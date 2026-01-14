"""Tests for Blockchain Integration module.

Tests cover:
- Polygon client connection
- Transaction result handling
- MetaMask signature verification
- Smart contract interfaces
- Event logger and Merkle proofs
"""

import os
import sys
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))


class TestTransactionResult:
    """Tests for TransactionResult dataclass."""

    def test_transaction_result_creation(self):
        """Test creating a transaction result."""
        from blockchain.polygon_client import TransactionResult

        result = TransactionResult(
            tx_hash="0x" + "a" * 64,
            block_number=12345,
            gas_used=21000,
            status=1,
        )

        assert result.tx_hash == "0x" + "a" * 64
        assert result.block_number == 12345
        assert result.gas_used == 21000
        assert result.success is True

    def test_transaction_result_failure(self):
        """Test transaction result with failure status."""
        from blockchain.polygon_client import TransactionResult

        result = TransactionResult(
            tx_hash="0x" + "b" * 64,
            block_number=12345,
            gas_used=21000,
            status=0,
        )

        assert result.success is False


class TestGasEstimate:
    """Tests for GasEstimate dataclass."""

    def test_gas_estimate_matic_conversion(self):
        """Test MATIC conversion from Wei."""
        from blockchain.polygon_client import GasEstimate

        estimate = GasEstimate(
            gas_limit=100000,
            gas_price=30_000_000_000,  # 30 Gwei
            max_fee=3_000_000_000_000_000,  # 0.003 MATIC
        )

        assert estimate.max_fee_matic == 0.003


class TestMetaMaskWalletVerifier:
    """Tests for MetaMask signature verification."""

    def test_create_sign_message(self):
        """Test sign message creation."""
        from blockchain.polygon_client import MetaMaskWalletVerifier

        address = "0x" + "1" * 40
        nonce = "test_nonce_123"

        message = MetaMaskWalletVerifier.create_sign_message(address, nonce)

        assert "PULSAR SENTINEL" in message
        assert address in message
        assert nonce in message

    def test_verify_signature_invalid_format(self):
        """Test signature verification with invalid format."""
        from blockchain.polygon_client import MetaMaskWalletVerifier

        result = MetaMaskWalletVerifier.verify_signature(
            message="test",
            signature="invalid_signature",
            expected_address="0x" + "1" * 40,
        )

        assert result is False

    def test_recover_address_invalid_signature(self):
        """Test address recovery with invalid signature."""
        from blockchain.polygon_client import MetaMaskWalletVerifier

        result = MetaMaskWalletVerifier.recover_address(
            message="test",
            signature="not_a_valid_signature",
        )

        assert result is None


class TestContractRole:
    """Tests for ContractRole enum."""

    def test_contract_roles(self):
        """Test contract role values."""
        from blockchain.smart_contract import ContractRole

        assert ContractRole.NONE == 0
        assert ContractRole.USER == 1
        assert ContractRole.SENTINEL == 2
        assert ContractRole.ADMIN == 3


class TestMerkleProof:
    """Tests for Merkle proof functionality."""

    def test_merkle_proof_creation(self):
        """Test Merkle proof creation."""
        from blockchain.event_logger import MerkleProof

        proof = MerkleProof(
            asr_id="asr_test123",
            asr_signature="a" * 64,
            proof_path=[("b" * 64, "right"), ("c" * 64, "left")],
            merkle_root="d" * 64,
            batch_id="batch_test456",
            tx_hash="0x" + "e" * 64,
        )

        assert proof.asr_id == "asr_test123"
        assert len(proof.proof_path) == 2

    def test_merkle_proof_serialization(self):
        """Test Merkle proof JSON serialization."""
        from blockchain.event_logger import MerkleProof

        proof = MerkleProof(
            asr_id="asr_test",
            asr_signature="sig123",
            proof_path=[("hash1", "right")],
            merkle_root="root123",
            batch_id="batch123",
            tx_hash="0xtx123",
        )

        json_str = proof.to_json()
        assert "asr_test" in json_str

        restored = MerkleProof.from_dict(eval(json_str))
        assert restored.asr_id == proof.asr_id

    def test_merkle_proof_verification(self):
        """Test Merkle proof verification."""
        from core.asr_engine import ASREngine

        # Create a simple proof
        asr_signature = "a" * 64
        sibling = "b" * 64

        # Manual Merkle calculation
        import hashlib
        left = bytes.fromhex(asr_signature)
        right = bytes.fromhex(sibling)
        root = hashlib.sha256(left + right).hexdigest()

        proof_path = [(sibling, "right")]

        result = ASREngine.verify_merkle_proof(
            asr_signature,
            proof_path,
            root,
        )

        assert result is True

    def test_merkle_proof_verification_failure(self):
        """Test Merkle proof verification with wrong root."""
        from core.asr_engine import ASREngine

        asr_signature = "a" * 64
        sibling = "b" * 64
        wrong_root = "c" * 64

        proof_path = [(sibling, "right")]

        result = ASREngine.verify_merkle_proof(
            asr_signature,
            proof_path,
            wrong_root,
        )

        assert result is False


class TestBatchSubmission:
    """Tests for batch submission tracking."""

    def test_batch_submission_creation(self):
        """Test batch submission creation."""
        from blockchain.event_logger import BatchSubmission

        submission = BatchSubmission(
            batch_id="batch_123",
            merkle_root="root_abc",
            tx_hash="0xtx_xyz",
            block_number=100,
            timestamp=datetime.now(timezone.utc),
            asr_count=10,
        )

        assert submission.batch_id == "batch_123"
        assert submission.asr_count == 10


class TestBlockchainEventLogger:
    """Tests for blockchain event logger."""

    def test_event_logger_initialization(self, tmp_path):
        """Test event logger initialization."""
        from blockchain.event_logger import BlockchainEventLogger

        # Create with blockchain disabled
        logger = BlockchainEventLogger()

        assert logger.pending_count == 0

    def test_event_logger_batch_accumulation(self, tmp_path):
        """Test ASR accumulation in batches."""
        from blockchain.event_logger import BlockchainEventLogger
        from core.asr_engine import ASREngine, ThreatLevel

        # Create logger without blockchain
        logger = BlockchainEventLogger()

        # Create ASRs
        asr_engine = ASREngine(storage_path=tmp_path)

        for i in range(5):
            asr = asr_engine.create_asr(
                agent_id=f"user_{i}",
                action=f"action_{i}",
                threat_level=ThreatLevel.INFO,
            )
            logger.log_asr(asr)

        assert logger.pending_count == 5

    def test_event_logger_disabled(self, tmp_path):
        """Test event logger when disabled."""
        from blockchain.event_logger import BlockchainEventLogger
        from core.asr_engine import ASREngine, ThreatLevel

        logger = BlockchainEventLogger()
        # Disable by setting enabled to False
        logger._enabled = False

        asr_engine = ASREngine(storage_path=tmp_path)
        asr = asr_engine.create_asr(
            agent_id="test",
            action="test",
            threat_level=ThreatLevel.INFO,
        )

        result = logger.log_asr(asr)
        assert result is None


class TestPolygonClientOffline:
    """Tests for Polygon client (offline/unit tests)."""

    def test_client_initialization(self):
        """Test client initialization."""
        from blockchain.polygon_client import PolygonClient, NetworkType

        client = PolygonClient(network=NetworkType.TESTNET)

        assert client.network == NetworkType.TESTNET
        assert client.chain_id == 80002  # Amoy testnet

    def test_client_mainnet(self):
        """Test mainnet configuration."""
        from blockchain.polygon_client import PolygonClient, NetworkType

        client = PolygonClient(network=NetworkType.MAINNET)

        assert client.network == NetworkType.MAINNET
        assert client.chain_id == 137

    def test_client_not_connected(self):
        """Test accessing web3 without connection raises error."""
        from blockchain.polygon_client import PolygonClient

        client = PolygonClient()

        with pytest.raises(RuntimeError, match="Not connected"):
            _ = client.web3

    def test_client_is_connected_false(self):
        """Test is_connected returns False when not connected."""
        from blockchain.polygon_client import PolygonClient

        client = PolygonClient()

        assert client.is_connected is False
