"""Blockchain Event Logger for PULSAR SENTINEL.

Provides immutable ASR (Agent State Record) logging to the Polygon blockchain
with Merkle tree proofs for efficient verification.

Features:
- Batch ASR submissions to minimize gas costs
- Merkle tree proofs for individual record verification
- Automatic retry with exponential backoff
- Local caching with blockchain sync
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from core.asr_engine import AgentStateRecord, ASRBatch, ASREngine
from blockchain.polygon_client import PolygonClient, TransactionResult
from blockchain.smart_contract import GovernanceContract
from config.settings import get_settings
from config.logging import SecurityEventLogger

# Constants
MAX_BATCH_SIZE: Final[int] = 50
BATCH_TIMEOUT_SECONDS: Final[int] = 300  # 5 minutes
MAX_RETRY_ATTEMPTS: Final[int] = 3
RETRY_BASE_DELAY: Final[float] = 2.0

logger = SecurityEventLogger("event_logger")


@dataclass
class MerkleProof:
    """Merkle proof for verifying an ASR in a batch.

    Attributes:
        asr_id: The ASR being proven
        asr_signature: The ASR's signature hash
        proof_path: List of (hash, position) tuples
        merkle_root: The batch's Merkle root
        batch_id: The batch ID containing this ASR
        tx_hash: Blockchain transaction hash
    """
    asr_id: str
    asr_signature: str
    proof_path: list[tuple[str, str]]
    merkle_root: str
    batch_id: str
    tx_hash: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "asr_id": self.asr_id,
            "asr_signature": self.asr_signature,
            "proof_path": self.proof_path,
            "merkle_root": self.merkle_root,
            "batch_id": self.batch_id,
            "tx_hash": self.tx_hash,
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "MerkleProof":
        """Create from dictionary."""
        return cls(**data)

    def verify(self) -> bool:
        """Verify the Merkle proof.

        Returns:
            True if proof is valid
        """
        return ASREngine.verify_merkle_proof(
            self.asr_signature,
            self.proof_path,
            self.merkle_root,
        )


@dataclass
class BatchSubmission:
    """Record of a batch submission to blockchain.

    Attributes:
        batch_id: The batch ID
        merkle_root: Merkle root of the batch
        tx_hash: Blockchain transaction hash
        block_number: Block containing the transaction
        timestamp: Submission timestamp
        asr_count: Number of ASRs in the batch
    """
    batch_id: str
    merkle_root: str
    tx_hash: str
    block_number: int
    timestamp: datetime
    asr_count: int


class BlockchainEventLogger:
    """Logger for submitting ASR records to blockchain.

    Handles batching, Merkle tree construction, and blockchain
    submission of Agent State Records.

    Example:
        >>> client = PolygonClient()
        >>> client.connect()
        >>> contract = GovernanceContract(client, address)
        >>> event_logger = BlockchainEventLogger(contract)
        >>> event_logger.log_asr(asr_record)
        >>> event_logger.flush()  # Force submit pending batch
    """

    def __init__(
        self,
        contract: GovernanceContract | None = None,
        client: PolygonClient | None = None,
        max_batch_size: int = MAX_BATCH_SIZE,
        batch_timeout: int = BATCH_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize blockchain event logger.

        Args:
            contract: GovernanceContract instance
            client: PolygonClient instance (creates contract if not provided)
            max_batch_size: Maximum ASRs per batch
            batch_timeout: Seconds before auto-flush
        """
        settings = get_settings()

        self._client = client
        self._contract = contract
        self._max_batch_size = max_batch_size
        self._batch_timeout = batch_timeout

        self._pending_asrs: list[AgentStateRecord] = []
        self._batch_start_time: float | None = None
        self._submissions: list[BatchSubmission] = []

        # Local cache directory
        self._cache_dir = Path(settings.asr_storage_path) / "blockchain_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # ASR engine for Merkle operations
        self._asr_engine = ASREngine()

        # Blockchain logging enabled?
        self._enabled = settings.asr_blockchain_enabled

    @property
    def is_enabled(self) -> bool:
        """Check if blockchain logging is enabled."""
        return self._enabled

    @property
    def pending_count(self) -> int:
        """Get number of pending ASRs."""
        return len(self._pending_asrs)

    def log_asr(self, asr: AgentStateRecord) -> MerkleProof | None:
        """Log an ASR record (adds to pending batch).

        Args:
            asr: The ASR record to log

        Returns:
            MerkleProof if batch was submitted, None otherwise
        """
        if not self._enabled:
            return None

        # Verify ASR signature
        if not asr.verify_signature():
            raise ValueError("Invalid ASR signature")

        # Add to pending batch
        self._pending_asrs.append(asr)

        # Start batch timer if first in batch
        if self._batch_start_time is None:
            self._batch_start_time = time.time()

        # Check if batch is full or timed out
        if self._should_flush():
            result = self.flush()
            if result:
                # Return proof for the just-added ASR
                return self._get_proof_from_submission(asr, result)

        return None

    def _should_flush(self) -> bool:
        """Check if batch should be flushed."""
        if len(self._pending_asrs) >= self._max_batch_size:
            return True

        if self._batch_start_time is not None:
            elapsed = time.time() - self._batch_start_time
            if elapsed >= self._batch_timeout:
                return True

        return False

    def flush(self) -> BatchSubmission | None:
        """Flush pending batch to blockchain.

        Returns:
            BatchSubmission if successful, None if no pending ASRs
        """
        if not self._pending_asrs:
            return None

        if not self._enabled:
            # Clear pending but don't submit
            self._pending_asrs = []
            self._batch_start_time = None
            return None

        if self._contract is None:
            raise RuntimeError("No contract configured for blockchain logging")

        # Create batch
        batch = self._asr_engine.flush_batch()
        if batch is None:
            # Use pending ASRs directly
            batch = self._create_batch()

        # Submit to blockchain with retry
        result = self._submit_batch_with_retry(batch)

        if result:
            # Cache the submission
            self._cache_submission(batch, result)
            self._submissions.append(result)

            # Clear pending
            self._pending_asrs = []
            self._batch_start_time = None

            logger.log_blockchain_event(
                event_type="batch_submitted",
                tx_hash=result.tx_hash,
                success=True,
            )

        return result

    def _create_batch(self) -> ASRBatch:
        """Create batch from pending ASRs."""
        import secrets

        batch_id = f"batch_{secrets.token_hex(16)}"
        merkle_root = self._asr_engine._compute_merkle_root(self._pending_asrs)

        return ASRBatch(
            batch_id=batch_id,
            records=self._pending_asrs.copy(),
            merkle_root=merkle_root,
        )

    def _submit_batch_with_retry(
        self,
        batch: ASRBatch,
    ) -> BatchSubmission | None:
        """Submit batch with exponential backoff retry.

        Args:
            batch: The batch to submit

        Returns:
            BatchSubmission if successful, None on failure
        """
        delay = RETRY_BASE_DELAY

        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # Create event data (Merkle root as bytes32)
                event_data = bytes.fromhex(batch.merkle_root)

                # Submit to contract
                tx_result = self._contract.log_security_event(
                    event_type=f"ASR_BATCH:{batch.batch_id[:16]}",
                    data=event_data,
                )

                if tx_result.success:
                    return BatchSubmission(
                        batch_id=batch.batch_id,
                        merkle_root=batch.merkle_root,
                        tx_hash=tx_result.tx_hash,
                        block_number=tx_result.block_number,
                        timestamp=datetime.now(timezone.utc),
                        asr_count=len(batch.records),
                    )

            except Exception as e:
                logger.log_blockchain_event(
                    event_type="batch_submit_failed",
                    success=False,
                    error=f"Attempt {attempt + 1}: {e}",
                )

                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

        return None

    def _cache_submission(
        self,
        batch: ASRBatch,
        submission: BatchSubmission,
    ) -> None:
        """Cache batch submission locally.

        Args:
            batch: The submitted batch
            submission: The submission record
        """
        cache_data = {
            "submission": {
                "batch_id": submission.batch_id,
                "merkle_root": submission.merkle_root,
                "tx_hash": submission.tx_hash,
                "block_number": submission.block_number,
                "timestamp": submission.timestamp.isoformat(),
                "asr_count": submission.asr_count,
            },
            "records": [r.to_dict() for r in batch.records],
        }

        cache_file = self._cache_dir / f"{submission.batch_id}.json"
        cache_file.write_text(json.dumps(cache_data, indent=2, default=str))

    def _get_proof_from_submission(
        self,
        asr: AgentStateRecord,
        submission: BatchSubmission,
    ) -> MerkleProof:
        """Generate Merkle proof for an ASR from submission.

        Args:
            asr: The ASR to prove
            submission: The batch submission

        Returns:
            MerkleProof for the ASR
        """
        # Load batch from cache
        cache_file = self._cache_dir / f"{submission.batch_id}.json"
        cache_data = json.loads(cache_file.read_text())

        # Reconstruct batch
        records = [AgentStateRecord.from_dict(r) for r in cache_data["records"]]
        batch = ASRBatch(
            batch_id=submission.batch_id,
            records=records,
            merkle_root=submission.merkle_root,
        )

        # Get proof
        proof_path = self._asr_engine.get_merkle_proof(asr, batch)

        return MerkleProof(
            asr_id=asr.asr_id,
            asr_signature=asr.signature,
            proof_path=proof_path,
            merkle_root=submission.merkle_root,
            batch_id=submission.batch_id,
            tx_hash=submission.tx_hash,
        )

    def get_proof(self, asr_id: str) -> MerkleProof | None:
        """Get Merkle proof for an ASR by ID.

        Args:
            asr_id: The ASR ID

        Returns:
            MerkleProof if found, None otherwise
        """
        # Search cache for ASR
        for cache_file in self._cache_dir.glob("batch_*.json"):
            try:
                cache_data = json.loads(cache_file.read_text())

                for record_data in cache_data["records"]:
                    if record_data["asr_id"] == asr_id:
                        # Found it - generate proof
                        asr = AgentStateRecord.from_dict(record_data)
                        records = [
                            AgentStateRecord.from_dict(r)
                            for r in cache_data["records"]
                        ]

                        batch = ASRBatch(
                            batch_id=cache_data["submission"]["batch_id"],
                            records=records,
                            merkle_root=cache_data["submission"]["merkle_root"],
                        )

                        proof_path = self._asr_engine.get_merkle_proof(asr, batch)

                        return MerkleProof(
                            asr_id=asr.asr_id,
                            asr_signature=asr.signature,
                            proof_path=proof_path,
                            merkle_root=batch.merkle_root,
                            batch_id=batch.batch_id,
                            tx_hash=cache_data["submission"]["tx_hash"],
                        )

            except (json.JSONDecodeError, KeyError):
                continue

        return None

    def verify_asr_on_chain(self, proof: MerkleProof) -> bool:
        """Verify an ASR exists on chain.

        Args:
            proof: The Merkle proof to verify

        Returns:
            True if ASR is verified on chain
        """
        if not proof.verify():
            return False

        # Verify transaction exists
        if self._client is None:
            return False

        receipt = self._client.get_transaction_receipt(proof.tx_hash)
        return receipt is not None and receipt.success

    def get_submissions(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[BatchSubmission]:
        """Get batch submissions within time range.

        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of matching submissions
        """
        results = []

        for cache_file in sorted(self._cache_dir.glob("batch_*.json")):
            try:
                cache_data = json.loads(cache_file.read_text())
                sub_data = cache_data["submission"]

                timestamp = datetime.fromisoformat(sub_data["timestamp"])

                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue

                results.append(BatchSubmission(
                    batch_id=sub_data["batch_id"],
                    merkle_root=sub_data["merkle_root"],
                    tx_hash=sub_data["tx_hash"],
                    block_number=sub_data["block_number"],
                    timestamp=timestamp,
                    asr_count=sub_data["asr_count"],
                ))

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return results


class EventLoggerFactory:
    """Factory for creating configured event loggers."""

    @staticmethod
    def create(
        client: PolygonClient | None = None,
        contract_address: str | None = None,
    ) -> BlockchainEventLogger:
        """Create a configured event logger.

        Args:
            client: Optional PolygonClient (creates new if not provided)
            contract_address: Optional contract address

        Returns:
            Configured BlockchainEventLogger
        """
        settings = get_settings()

        if client is None:
            client = PolygonClient(network=settings.polygon_network)
            try:
                client.connect()
            except ConnectionError:
                # Return logger with blockchain disabled
                return BlockchainEventLogger()

        address = contract_address or settings.governance_contract_address
        if not address:
            # Return logger with blockchain disabled
            return BlockchainEventLogger()

        contract = GovernanceContract(client, address)
        return BlockchainEventLogger(contract=contract, client=client)
