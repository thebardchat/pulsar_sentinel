"""Polygon Blockchain Client for PULSAR SENTINEL.

Provides Web3.py integration for Polygon network interactions including:
- Connection management to Polygon mainnet/testnet
- Transaction submission and confirmation
- MetaMask wallet integration for signing
- Gas estimation and management

Network Support:
- Polygon Mainnet (Chain ID: 137)
- Polygon Amoy Testnet (Chain ID: 80002)
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Final

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import TxReceipt, TxParams, Wei
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress

from config.constants import POLYGON_CHAIN_ID_MAINNET, POLYGON_CHAIN_ID_TESTNET
from config.settings import get_settings
from config.logging import SecurityEventLogger

# Constants
DEFAULT_GAS_LIMIT: Final[int] = 100_000
MAX_GAS_PRICE_GWEI: Final[int] = 500
CONFIRMATION_BLOCKS: Final[int] = 2

logger = SecurityEventLogger("blockchain")


class NetworkType(str, Enum):
    """Polygon network types."""
    MAINNET = "mainnet"
    TESTNET = "testnet"


@dataclass
class TransactionResult:
    """Result of a blockchain transaction.

    Attributes:
        tx_hash: Transaction hash
        block_number: Block containing the transaction
        gas_used: Actual gas consumed
        status: Transaction status (1 = success, 0 = failure)
        timestamp: Transaction confirmation timestamp
    """
    tx_hash: str
    block_number: int
    gas_used: int
    status: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        """Check if transaction was successful."""
        return self.status == 1

    @classmethod
    def from_receipt(cls, receipt: TxReceipt) -> "TransactionResult":
        """Create from Web3 transaction receipt."""
        return cls(
            tx_hash=receipt["transactionHash"].hex(),
            block_number=receipt["blockNumber"],
            gas_used=receipt["gasUsed"],
            status=receipt.get("status", 0),
        )


@dataclass
class GasEstimate:
    """Gas estimation result.

    Attributes:
        gas_limit: Estimated gas limit
        gas_price: Current gas price in Wei
        max_fee: Maximum transaction fee in Wei
    """
    gas_limit: int
    gas_price: int
    max_fee: int

    @property
    def max_fee_matic(self) -> float:
        """Get maximum fee in MATIC."""
        return self.max_fee / 10**18


class PolygonClient:
    """Client for interacting with Polygon blockchain.

    Provides connection management, transaction handling, and wallet
    integration for Polygon mainnet and testnet.

    Example:
        >>> client = PolygonClient(network=NetworkType.TESTNET)
        >>> client.connect()
        >>> balance = client.get_balance("0x...")
        >>> result = client.send_transaction(tx_params)
    """

    def __init__(
        self,
        network: NetworkType | str = NetworkType.TESTNET,
        rpc_url: str | None = None,
    ) -> None:
        """Initialize Polygon client.

        Args:
            network: Network type (mainnet or testnet)
            rpc_url: Optional custom RPC URL
        """
        settings = get_settings()

        if isinstance(network, str):
            network = NetworkType(network)

        self._network = network
        self._chain_id = (
            POLYGON_CHAIN_ID_MAINNET
            if network == NetworkType.MAINNET
            else POLYGON_CHAIN_ID_TESTNET
        )

        if rpc_url:
            self._rpc_url = rpc_url
        else:
            self._rpc_url = (
                settings.polygon_mainnet_rpc
                if network == NetworkType.MAINNET
                else settings.polygon_testnet_rpc
            )

        self._web3: Web3 | None = None
        self._account: LocalAccount | None = None

    @property
    def network(self) -> NetworkType:
        """Get current network type."""
        return self._network

    @property
    def chain_id(self) -> int:
        """Get chain ID for current network."""
        return self._chain_id

    @property
    def web3(self) -> Web3:
        """Get Web3 instance (must be connected first)."""
        if self._web3 is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._web3

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to network."""
        return self._web3 is not None and self._web3.is_connected()

    def connect(self) -> bool:
        """Connect to Polygon network.

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))

            # Add POA middleware for Polygon
            self._web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not self._web3.is_connected():
                raise ConnectionError(f"Failed to connect to {self._rpc_url}")

            # Verify chain ID
            actual_chain_id = self._web3.eth.chain_id
            if actual_chain_id != self._chain_id:
                raise ConnectionError(
                    f"Chain ID mismatch: expected {self._chain_id}, "
                    f"got {actual_chain_id}"
                )

            logger.log_blockchain_event(
                event_type="connected",
                success=True,
            )

            return True

        except Exception as e:
            logger.log_blockchain_event(
                event_type="connection_failed",
                success=False,
                error=str(e),
            )
            raise ConnectionError(f"Connection failed: {e}") from e

    def disconnect(self) -> None:
        """Disconnect from network."""
        self._web3 = None
        self._account = None

    def set_account(self, private_key: str) -> ChecksumAddress:
        """Set account for signing transactions.

        Args:
            private_key: Private key (hex string with or without 0x prefix)

        Returns:
            The account address
        """
        if not private_key.startswith("0x"):
            private_key = f"0x{private_key}"

        self._account = Account.from_key(private_key)
        return self._account.address

    @property
    def account_address(self) -> ChecksumAddress | None:
        """Get the current account address."""
        return self._account.address if self._account else None

    def get_balance(self, address: str) -> int:
        """Get MATIC balance for an address.

        Args:
            address: Ethereum address

        Returns:
            Balance in Wei
        """
        checksum_address = Web3.to_checksum_address(address)
        return self.web3.eth.get_balance(checksum_address)

    def get_balance_matic(self, address: str) -> float:
        """Get MATIC balance in MATIC units.

        Args:
            address: Ethereum address

        Returns:
            Balance in MATIC
        """
        balance_wei = self.get_balance(address)
        return float(Web3.from_wei(balance_wei, "ether"))

    def get_nonce(self, address: str | None = None) -> int:
        """Get transaction nonce for an address.

        Args:
            address: Address to get nonce for (defaults to set account)

        Returns:
            Current nonce
        """
        if address is None:
            if self._account is None:
                raise ValueError("No address provided and no account set")
            address = self._account.address

        checksum_address = Web3.to_checksum_address(address)
        return self.web3.eth.get_transaction_count(checksum_address)

    def estimate_gas(
        self,
        to: str,
        data: bytes = b"",
        value: int = 0,
    ) -> GasEstimate:
        """Estimate gas for a transaction.

        Args:
            to: Destination address
            data: Transaction data
            value: Value to send (Wei)

        Returns:
            GasEstimate with limit, price, and max fee
        """
        if self._account is None:
            raise ValueError("No account set for gas estimation")

        tx: TxParams = {
            "from": self._account.address,
            "to": Web3.to_checksum_address(to),
            "data": data,
            "value": Wei(value),
        }

        gas_limit = self.web3.eth.estimate_gas(tx)
        gas_price = self.web3.eth.gas_price

        # Add 20% buffer to gas limit
        gas_limit = int(gas_limit * 1.2)

        return GasEstimate(
            gas_limit=gas_limit,
            gas_price=gas_price,
            max_fee=gas_limit * gas_price,
        )

    def send_transaction(
        self,
        to: str,
        data: bytes = b"",
        value: int = 0,
        gas_limit: int | None = None,
        gas_price: int | None = None,
        wait_for_receipt: bool = True,
    ) -> TransactionResult:
        """Send a signed transaction.

        Args:
            to: Destination address
            data: Transaction data
            value: Value to send (Wei)
            gas_limit: Gas limit (estimated if not provided)
            gas_price: Gas price (network price if not provided)
            wait_for_receipt: Wait for transaction confirmation

        Returns:
            TransactionResult with transaction details

        Raises:
            ValueError: If no account is set
            RuntimeError: If transaction fails
        """
        if self._account is None:
            raise ValueError("No account set. Call set_account() first.")

        # Get gas estimate if not provided
        if gas_limit is None or gas_price is None:
            estimate = self.estimate_gas(to, data, value)
            gas_limit = gas_limit or estimate.gas_limit
            gas_price = gas_price or estimate.gas_price

        # Build transaction
        tx: TxParams = {
            "chainId": self._chain_id,
            "from": self._account.address,
            "to": Web3.to_checksum_address(to),
            "data": data,
            "value": Wei(value),
            "gas": gas_limit,
            "gasPrice": Wei(gas_price),
            "nonce": self.get_nonce(),
        }

        # Sign transaction
        signed_tx = self._account.sign_transaction(tx)

        # Send transaction
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        logger.log_blockchain_event(
            event_type="tx_submitted",
            tx_hash=tx_hash.hex(),
            success=True,
        )

        if not wait_for_receipt:
            return TransactionResult(
                tx_hash=tx_hash.hex(),
                block_number=0,
                gas_used=0,
                status=1,
            )

        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=120,
        )

        result = TransactionResult.from_receipt(receipt)

        logger.log_blockchain_event(
            event_type="tx_confirmed",
            tx_hash=result.tx_hash,
            success=result.success,
        )

        return result

    def call_contract(
        self,
        contract_address: str,
        data: bytes,
    ) -> bytes:
        """Call a contract function (read-only).

        Args:
            contract_address: Contract address
            data: Encoded function call data

        Returns:
            Encoded return data
        """
        result = self.web3.eth.call({
            "to": Web3.to_checksum_address(contract_address),
            "data": data,
        })
        return bytes(result)

    def get_transaction_receipt(self, tx_hash: str) -> TransactionResult | None:
        """Get receipt for a transaction.

        Args:
            tx_hash: Transaction hash

        Returns:
            TransactionResult if found, None otherwise
        """
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            return TransactionResult.from_receipt(receipt)
        except Exception:
            return None

    def wait_for_confirmations(
        self,
        tx_hash: str,
        confirmations: int = CONFIRMATION_BLOCKS,
        timeout: int = 120,
    ) -> bool:
        """Wait for transaction confirmations.

        Args:
            tx_hash: Transaction hash
            confirmations: Number of confirmations to wait for
            timeout: Maximum wait time in seconds

        Returns:
            True if confirmations reached within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                current_block = self.web3.eth.block_number
                tx_block = receipt["blockNumber"]
                current_confirmations = current_block - tx_block

                if current_confirmations >= confirmations:
                    return True

            except Exception:
                pass

            time.sleep(2)

        return False


class MetaMaskWalletVerifier:
    """Verifier for MetaMask wallet signatures.

    Provides signature verification for MetaMask-signed messages
    used in wallet-based authentication.
    """

    @staticmethod
    def create_sign_message(
        address: str,
        nonce: str,
        timestamp: str | None = None,
    ) -> str:
        """Create the message to be signed by MetaMask.

        Args:
            address: Wallet address
            nonce: Unique nonce for this auth attempt
            timestamp: Optional timestamp

        Returns:
            Message string for signing
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        return (
            f"PULSAR SENTINEL Authentication\n\n"
            f"Address: {address}\n"
            f"Nonce: {nonce}\n"
            f"Timestamp: {timestamp}\n\n"
            f"Sign this message to authenticate."
        )

    @staticmethod
    def verify_signature(
        message: str,
        signature: str,
        expected_address: str,
    ) -> bool:
        """Verify a MetaMask signature.

        Args:
            message: The signed message
            signature: The signature (hex string)
            expected_address: Expected signer address

        Returns:
            True if signature is valid and from expected address
        """
        try:
            # Encode message with Ethereum prefix
            message_hash = Account.defunct_hash_message(text=message)

            # Recover address from signature
            recovered_address = Account.recover_message(
                defunct_hash=message_hash,
                signature=signature,
            )

            # Compare addresses (case-insensitive)
            return recovered_address.lower() == expected_address.lower()

        except Exception as e:
            logger.log_auth_attempt(
                wallet_address=expected_address,
                success=False,
                failure_reason=str(e),
            )
            return False

    @staticmethod
    def recover_address(message: str, signature: str) -> str | None:
        """Recover address from signature.

        Args:
            message: The signed message
            signature: The signature (hex string)

        Returns:
            Recovered address or None if invalid
        """
        try:
            message_hash = Account.defunct_hash_message(text=message)
            return Account.recover_message(
                defunct_hash=message_hash,
                signature=signature,
            )
        except Exception:
            return None
