"""Smart Contract Interface for PULSAR SENTINEL.

Provides interaction with the Governance smart contract on Polygon
including deployment, function calls, and event monitoring.

Contract Features:
- Access control (Admin, Sentinel, User roles)
- Rate limiting (5-req/min default)
- Security event logging to blockchain
- Role-based permissions
"""

import json
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Final

from web3 import Web3
from web3.contract import Contract
from eth_typing import ChecksumAddress

from blockchain.polygon_client import PolygonClient, TransactionResult
from config.logging import SecurityEventLogger

logger = SecurityEventLogger("smart_contract")

# Governance Contract ABI (simplified for core functionality)
GOVERNANCE_ABI: Final[list[dict]] = [
    # Events
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "user", "type": "address"},
            {"indexed": False, "name": "eventType", "type": "string"},
            {"indexed": False, "name": "data", "type": "bytes32"},
            {"indexed": False, "name": "timestamp", "type": "uint256"},
        ],
        "name": "SecurityEvent",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "user", "type": "address"},
            {"indexed": False, "name": "role", "type": "uint8"},
        ],
        "name": "RoleGranted",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "user", "type": "address"},
            {"indexed": False, "name": "strikes", "type": "uint8"},
        ],
        "name": "StrikeIssued",
        "type": "event",
    },
    # Read Functions
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getRole",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getStrikes",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getRateLimit",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "isActive",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "isBanned",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getLastActivity",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    # Write Functions
    {
        "inputs": [
            {"name": "user", "type": "address"},
            {"name": "role", "type": "uint8"},
        ],
        "name": "grantRole",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "revokeRole",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "issueStrike",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "resetStrikes",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "eventType", "type": "string"},
            {"name": "data", "type": "bytes32"},
        ],
        "name": "logSecurityEvent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "user", "type": "address"},
            {"name": "limit", "type": "uint256"},
        ],
        "name": "setRateLimit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "recordActivity",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "heir", "type": "address"}],
        "name": "setHeir",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

# Contract bytecode (placeholder - would be actual compiled bytecode)
GOVERNANCE_BYTECODE: Final[str] = "0x608060405234801561001057600080fd5b50..."


class ContractRole(IntEnum):
    """Contract role levels."""
    NONE = 0
    USER = 1
    SENTINEL = 2
    ADMIN = 3


@dataclass
class ContractConfig:
    """Configuration for the governance contract.

    Attributes:
        address: Contract address on chain
        abi: Contract ABI
        default_rate_limit: Default rate limit per minute
        strike_threshold: Strikes before ban
        heir_transfer_days: Days until heir transfer
    """
    address: str
    abi: list[dict]
    default_rate_limit: int = 5
    strike_threshold: int = 3
    heir_transfer_days: int = 90


class GovernanceContract:
    """Interface for the PULSAR SENTINEL Governance Contract.

    Provides methods to interact with the on-chain governance
    contract for access control, rate limiting, and event logging.

    Example:
        >>> client = PolygonClient()
        >>> client.connect()
        >>> client.set_account(private_key)
        >>> contract = GovernanceContract(client, contract_address)
        >>> role = contract.get_role(user_address)
    """

    def __init__(
        self,
        client: PolygonClient,
        address: str | None = None,
        abi: list[dict] | None = None,
    ) -> None:
        """Initialize governance contract interface.

        Args:
            client: Connected PolygonClient instance
            address: Contract address (uses config if not provided)
            abi: Contract ABI (uses default if not provided)
        """
        from config.settings import get_settings

        settings = get_settings()

        self._client = client
        self._address = address or settings.governance_contract_address
        self._abi = abi or GOVERNANCE_ABI

        self._contract: Contract | None = None

    @property
    def address(self) -> str:
        """Get contract address."""
        return self._address

    @property
    def contract(self) -> Contract:
        """Get Web3 contract instance."""
        if self._contract is None:
            if not self._address:
                raise ValueError("Contract address not set")

            self._contract = self._client.web3.eth.contract(
                address=Web3.to_checksum_address(self._address),
                abi=self._abi,
            )
        return self._contract

    # Read Functions

    def get_role(self, user: str) -> ContractRole:
        """Get user's role.

        Args:
            user: User address

        Returns:
            ContractRole enum value
        """
        role_value = self.contract.functions.getRole(
            Web3.to_checksum_address(user)
        ).call()
        return ContractRole(role_value)

    def get_strikes(self, user: str) -> int:
        """Get user's strike count.

        Args:
            user: User address

        Returns:
            Number of strikes
        """
        return self.contract.functions.getStrikes(
            Web3.to_checksum_address(user)
        ).call()

    def get_rate_limit(self, user: str) -> int:
        """Get user's rate limit.

        Args:
            user: User address

        Returns:
            Rate limit per minute
        """
        return self.contract.functions.getRateLimit(
            Web3.to_checksum_address(user)
        ).call()

    def is_active(self, user: str) -> bool:
        """Check if user is active.

        Args:
            user: User address

        Returns:
            True if user is active
        """
        return self.contract.functions.isActive(
            Web3.to_checksum_address(user)
        ).call()

    def is_banned(self, user: str) -> bool:
        """Check if user is banned.

        Args:
            user: User address

        Returns:
            True if user is banned
        """
        return self.contract.functions.isBanned(
            Web3.to_checksum_address(user)
        ).call()

    def get_last_activity(self, user: str) -> int:
        """Get user's last activity timestamp.

        Args:
            user: User address

        Returns:
            Unix timestamp of last activity
        """
        return self.contract.functions.getLastActivity(
            Web3.to_checksum_address(user)
        ).call()

    # Write Functions

    def grant_role(
        self,
        user: str,
        role: ContractRole,
    ) -> TransactionResult:
        """Grant a role to a user.

        Args:
            user: User address
            role: Role to grant

        Returns:
            Transaction result
        """
        tx_data = self.contract.functions.grantRole(
            Web3.to_checksum_address(user),
            role.value,
        ).build_transaction({
            "from": self._client.account_address,
        })["data"]

        result = self._client.send_transaction(
            to=self._address,
            data=bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data),
        )

        logger.log_blockchain_event(
            event_type="role_granted",
            tx_hash=result.tx_hash,
            success=result.success,
        )

        return result

    def revoke_role(self, user: str) -> TransactionResult:
        """Revoke a user's role.

        Args:
            user: User address

        Returns:
            Transaction result
        """
        tx_data = self.contract.functions.revokeRole(
            Web3.to_checksum_address(user),
        ).build_transaction({
            "from": self._client.account_address,
        })["data"]

        result = self._client.send_transaction(
            to=self._address,
            data=bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data),
        )

        return result

    def issue_strike(self, user: str) -> TransactionResult:
        """Issue a strike to a user.

        Args:
            user: User address

        Returns:
            Transaction result
        """
        tx_data = self.contract.functions.issueStrike(
            Web3.to_checksum_address(user),
        ).build_transaction({
            "from": self._client.account_address,
        })["data"]

        result = self._client.send_transaction(
            to=self._address,
            data=bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data),
        )

        logger.log_blockchain_event(
            event_type="strike_issued",
            tx_hash=result.tx_hash,
            success=result.success,
        )

        return result

    def reset_strikes(self, user: str) -> TransactionResult:
        """Reset a user's strikes.

        Args:
            user: User address

        Returns:
            Transaction result
        """
        tx_data = self.contract.functions.resetStrikes(
            Web3.to_checksum_address(user),
        ).build_transaction({
            "from": self._client.account_address,
        })["data"]

        result = self._client.send_transaction(
            to=self._address,
            data=bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data),
        )

        return result

    def log_security_event(
        self,
        event_type: str,
        data: bytes,
    ) -> TransactionResult:
        """Log a security event to the blockchain.

        Args:
            event_type: Type of security event
            data: 32-byte event data

        Returns:
            Transaction result
        """
        # Ensure data is exactly 32 bytes
        if len(data) < 32:
            data = data.ljust(32, b"\x00")
        elif len(data) > 32:
            data = data[:32]

        tx_data = self.contract.functions.logSecurityEvent(
            event_type,
            data,
        ).build_transaction({
            "from": self._client.account_address,
        })["data"]

        result = self._client.send_transaction(
            to=self._address,
            data=bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data),
        )

        logger.log_blockchain_event(
            event_type="security_event_logged",
            tx_hash=result.tx_hash,
            success=result.success,
        )

        return result

    def set_rate_limit(
        self,
        user: str,
        limit: int,
    ) -> TransactionResult:
        """Set rate limit for a user.

        Args:
            user: User address
            limit: Rate limit per minute

        Returns:
            Transaction result
        """
        tx_data = self.contract.functions.setRateLimit(
            Web3.to_checksum_address(user),
            limit,
        ).build_transaction({
            "from": self._client.account_address,
        })["data"]

        result = self._client.send_transaction(
            to=self._address,
            data=bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data),
        )

        return result

    def record_activity(self) -> TransactionResult:
        """Record activity for the caller.

        Returns:
            Transaction result
        """
        tx_data = self.contract.functions.recordActivity().build_transaction({
            "from": self._client.account_address,
        })["data"]

        result = self._client.send_transaction(
            to=self._address,
            data=bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data),
        )

        return result

    def set_heir(self, heir: str) -> TransactionResult:
        """Set heir address for account recovery.

        Args:
            heir: Heir's address

        Returns:
            Transaction result
        """
        tx_data = self.contract.functions.setHeir(
            Web3.to_checksum_address(heir),
        ).build_transaction({
            "from": self._client.account_address,
        })["data"]

        result = self._client.send_transaction(
            to=self._address,
            data=bytes.fromhex(tx_data[2:]) if tx_data.startswith("0x") else bytes.fromhex(tx_data),
        )

        return result

    # Event Retrieval

    def get_security_events(
        self,
        user: str | None = None,
        from_block: int = 0,
        to_block: str | int = "latest",
    ) -> list[dict[str, Any]]:
        """Get security events from the contract.

        Args:
            user: Optional user address to filter by
            from_block: Start block number
            to_block: End block number or 'latest'

        Returns:
            List of security event dictionaries
        """
        event_filter = self.contract.events.SecurityEvent.create_filter(
            from_block=from_block,
            to_block=to_block,
            argument_filters={"user": Web3.to_checksum_address(user)} if user else None,
        )

        events = []
        for event in event_filter.get_all_entries():
            events.append({
                "user": event.args.user,
                "event_type": event.args.eventType,
                "data": event.args.data.hex(),
                "timestamp": event.args.timestamp,
                "block_number": event.blockNumber,
                "tx_hash": event.transactionHash.hex(),
            })

        return events


# Solidity source code for reference/deployment
GOVERNANCE_CONTRACT_SOLIDITY: Final[str] = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PulsarSentinelGovernance
 * @dev Self-governance contract for PULSAR SENTINEL security framework
 */
contract PulsarSentinelGovernance {
    enum Role { NONE, USER, SENTINEL, ADMIN }

    struct UserInfo {
        Role role;
        uint8 strikes;
        uint256 rateLimit;
        uint256 lastActivity;
        address heir;
        bool banned;
    }

    mapping(address => UserInfo) public users;
    address public owner;

    uint8 public constant STRIKE_THRESHOLD = 3;
    uint256 public constant DEFAULT_RATE_LIMIT = 5;
    uint256 public constant HEIR_TRANSFER_DAYS = 90;

    event SecurityEvent(address indexed user, string eventType, bytes32 data, uint256 timestamp);
    event RoleGranted(address indexed user, uint8 role);
    event StrikeIssued(address indexed user, uint8 strikes);
    event HeirTransfer(address indexed from, address indexed to);

    modifier onlyAdmin() {
        require(users[msg.sender].role == Role.ADMIN || msg.sender == owner, "Not admin");
        _;
    }

    modifier notBanned() {
        require(!users[msg.sender].banned, "User is banned");
        _;
    }

    constructor() {
        owner = msg.sender;
        users[msg.sender].role = Role.ADMIN;
        users[msg.sender].rateLimit = 100;
    }

    function getRole(address user) external view returns (uint8) {
        return uint8(users[user].role);
    }

    function getStrikes(address user) external view returns (uint8) {
        return users[user].strikes;
    }

    function getRateLimit(address user) external view returns (uint256) {
        uint256 limit = users[user].rateLimit;
        return limit == 0 ? DEFAULT_RATE_LIMIT : limit;
    }

    function isActive(address user) external view returns (bool) {
        return users[user].role != Role.NONE && !users[user].banned;
    }

    function isBanned(address user) external view returns (bool) {
        return users[user].banned;
    }

    function getLastActivity(address user) external view returns (uint256) {
        return users[user].lastActivity;
    }

    function grantRole(address user, uint8 role) external onlyAdmin {
        users[user].role = Role(role);
        if (users[user].rateLimit == 0) {
            users[user].rateLimit = DEFAULT_RATE_LIMIT;
        }
        emit RoleGranted(user, role);
    }

    function revokeRole(address user) external onlyAdmin {
        users[user].role = Role.NONE;
    }

    function issueStrike(address user) external onlyAdmin {
        users[user].strikes++;
        emit StrikeIssued(user, users[user].strikes);

        if (users[user].strikes >= STRIKE_THRESHOLD) {
            users[user].banned = true;
        }
    }

    function resetStrikes(address user) external onlyAdmin {
        users[user].strikes = 0;
        users[user].banned = false;
    }

    function logSecurityEvent(string memory eventType, bytes32 data) external notBanned {
        emit SecurityEvent(msg.sender, eventType, data, block.timestamp);
        users[msg.sender].lastActivity = block.timestamp;
    }

    function setRateLimit(address user, uint256 limit) external onlyAdmin {
        users[user].rateLimit = limit;
    }

    function recordActivity() external notBanned {
        users[msg.sender].lastActivity = block.timestamp;
    }

    function setHeir(address heir) external notBanned {
        users[msg.sender].heir = heir;
    }

    function claimAsHeir(address from) external {
        require(users[from].heir == msg.sender, "Not designated heir");
        require(
            block.timestamp > users[from].lastActivity + (HEIR_TRANSFER_DAYS * 1 days),
            "Transfer period not elapsed"
        );

        // Transfer role and settings
        users[msg.sender].role = users[from].role;
        users[msg.sender].rateLimit = users[from].rateLimit;

        // Revoke original user
        users[from].role = Role.NONE;
        users[from].heir = address(0);

        emit HeirTransfer(from, msg.sender);
    }
}
'''
