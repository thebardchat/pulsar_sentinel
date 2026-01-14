"""Agent State Record (ASR) Engine for PULSAR SENTINEL.

Generates immutable security event records for blockchain logging.
Every security event creates an ASR with cryptographic signature
for tamper-evident audit trails.

ASR Structure:
{
    timestamp: ISO8601,
    agent_id: str,
    action: str,
    threat_level: int (1-5),
    pqc_status: str ("safe" | "warning" | "critical"),
    signature: blockchain_hash,
    metadata: dict
}
"""

import json
import hashlib
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final
import secrets

from config.constants import (
    ThreatLevel,
    PQCStatus,
    PTSTier,
)
from config.settings import get_settings
from config.logging import SecurityEventLogger

# Constants
ASR_VERSION: Final[str] = "1.0"
HASH_ALGORITHM: Final[str] = "sha256"

logger = SecurityEventLogger("asr")


@dataclass
class AgentStateRecord:
    """Immutable Agent State Record for security event logging.

    Attributes:
        asr_id: Unique identifier for this record
        timestamp: ISO8601 timestamp of the event
        agent_id: Identifier of the agent/user triggering the event
        action: Description of the security action/event
        threat_level: Severity level (1-5)
        pqc_status: Post-quantum security status
        signature: Cryptographic hash/signature of the record
        metadata: Additional event-specific data
        version: ASR schema version
    """
    asr_id: str
    timestamp: str
    agent_id: str
    action: str
    threat_level: int
    pqc_status: str
    signature: str
    metadata: dict[str, Any] = field(default_factory=dict)
    version: str = ASR_VERSION

    def __post_init__(self) -> None:
        """Validate ASR fields after initialization."""
        if not 1 <= self.threat_level <= 5:
            raise ValueError(f"Threat level must be 1-5, got {self.threat_level}")

        valid_status = {s.value for s in PQCStatus}
        if self.pqc_status not in valid_status:
            raise ValueError(f"Invalid PQC status: {self.pqc_status}")

    def to_dict(self) -> dict[str, Any]:
        """Convert ASR to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize ASR to JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentStateRecord":
        """Create ASR from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentStateRecord":
        """Deserialize ASR from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def verify_signature(self) -> bool:
        """Verify the ASR signature is valid.

        Returns:
            True if signature matches computed hash
        """
        expected = self._compute_signature()
        return secrets.compare_digest(self.signature, expected)

    def _compute_signature(self) -> str:
        """Compute the signature for this ASR (excluding signature field)."""
        data = {
            "asr_id": self.asr_id,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "action": self.action,
            "threat_level": self.threat_level,
            "pqc_status": self.pqc_status,
            "metadata": self.metadata,
            "version": self.version,
        }
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class ASRBatch:
    """Batch of ASR records for efficient blockchain submission.

    Attributes:
        batch_id: Unique batch identifier
        records: List of ASR records in this batch
        merkle_root: Merkle tree root of all records
        created_at: Batch creation timestamp
    """
    batch_id: str
    records: list[AgentStateRecord]
    merkle_root: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def count(self) -> int:
        """Get number of records in batch."""
        return len(self.records)


class ASREngine:
    """Engine for generating and managing Agent State Records.

    Provides creation, validation, storage, and batching of ASR records
    for security event logging and blockchain submission.

    Example:
        >>> engine = ASREngine()
        >>> asr = engine.create_asr(
        ...     agent_id="user123",
        ...     action="key_rotation",
        ...     threat_level=ThreatLevel.INFO,
        ...     pqc_status=PQCStatus.SAFE,
        ... )
        >>> engine.store_asr(asr)
    """

    def __init__(self, storage_path: Path | str | None = None) -> None:
        """Initialize ASR engine.

        Args:
            storage_path: Optional custom storage path for ASR records
        """
        settings = get_settings()

        if storage_path is None:
            self._storage_path = settings.asr_storage_dir
        else:
            self._storage_path = Path(storage_path)

        self._min_log_level = settings.asr_min_log_level
        self._pending_batch: list[AgentStateRecord] = []
        self._max_batch_size = 100

        # Ensure storage directory exists
        self._storage_path.mkdir(parents=True, exist_ok=True)

    @property
    def storage_path(self) -> Path:
        """Get the ASR storage path."""
        return self._storage_path

    def create_asr(
        self,
        agent_id: str,
        action: str,
        threat_level: int | ThreatLevel,
        pqc_status: str | PQCStatus = PQCStatus.SAFE,
        metadata: dict[str, Any] | None = None,
    ) -> AgentStateRecord:
        """Create a new Agent State Record.

        Args:
            agent_id: Identifier of the agent/user
            action: Description of the security event
            threat_level: Severity level (1-5 or ThreatLevel enum)
            pqc_status: Post-quantum security status
            metadata: Additional event data

        Returns:
            New AgentStateRecord instance
        """
        # Normalize enums to values
        if isinstance(threat_level, ThreatLevel):
            threat_level = threat_level.value
        if isinstance(pqc_status, PQCStatus):
            pqc_status = pqc_status.value

        # Generate unique ID
        asr_id = f"asr_{secrets.token_hex(16)}"

        # Create timestamp
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build record (without signature first)
        asr = AgentStateRecord(
            asr_id=asr_id,
            timestamp=timestamp,
            agent_id=agent_id,
            action=action,
            threat_level=threat_level,
            pqc_status=pqc_status,
            signature="",  # Placeholder
            metadata=metadata or {},
        )

        # Compute and set signature
        asr.signature = asr._compute_signature()

        # Log the event
        if threat_level >= self._min_log_level:
            logger.log_event(
                event=f"asr_created:{action}",
                threat_level=threat_level,
                agent_id=agent_id,
                metadata={"asr_id": asr_id},
            )

        return asr

    def store_asr(self, asr: AgentStateRecord) -> Path:
        """Store ASR record to local storage.

        Args:
            asr: The ASR record to store

        Returns:
            Path to the stored file
        """
        # Verify signature before storing
        if not asr.verify_signature():
            raise ValueError("ASR signature verification failed")

        # Create date-based subdirectory
        date_str = asr.timestamp[:10]  # YYYY-MM-DD
        date_dir = self._storage_path / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        # Write to file
        file_path = date_dir / f"{asr.asr_id}.json"
        file_path.write_text(asr.to_json())

        return file_path

    def load_asr(self, asr_id: str, date: str | None = None) -> AgentStateRecord | None:
        """Load ASR record from storage.

        Args:
            asr_id: The ASR ID to load
            date: Optional date (YYYY-MM-DD) to narrow search

        Returns:
            AgentStateRecord if found, None otherwise
        """
        if date:
            # Search specific date directory
            file_path = self._storage_path / date / f"{asr_id}.json"
            if file_path.exists():
                return AgentStateRecord.from_json(file_path.read_text())
            return None

        # Search all date directories
        for date_dir in self._storage_path.iterdir():
            if date_dir.is_dir():
                file_path = date_dir / f"{asr_id}.json"
                if file_path.exists():
                    return AgentStateRecord.from_json(file_path.read_text())

        return None

    def list_asr_by_agent(
        self,
        agent_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        threat_level_min: int = 1,
    ) -> list[AgentStateRecord]:
        """List ASR records for a specific agent.

        Args:
            agent_id: Agent ID to filter by
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            threat_level_min: Minimum threat level to include

        Returns:
            List of matching ASR records
        """
        results: list[AgentStateRecord] = []

        for date_dir in sorted(self._storage_path.iterdir()):
            if not date_dir.is_dir():
                continue

            date_str = date_dir.name

            # Apply date filters
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue

            # Load matching records
            for file_path in date_dir.glob("*.json"):
                try:
                    asr = AgentStateRecord.from_json(file_path.read_text())
                    if (
                        asr.agent_id == agent_id
                        and asr.threat_level >= threat_level_min
                    ):
                        results.append(asr)
                except (json.JSONDecodeError, ValueError):
                    continue

        return results

    def add_to_batch(self, asr: AgentStateRecord) -> ASRBatch | None:
        """Add ASR to pending batch.

        Args:
            asr: The ASR record to add

        Returns:
            ASRBatch if batch is full and ready, None otherwise
        """
        self._pending_batch.append(asr)

        if len(self._pending_batch) >= self._max_batch_size:
            return self.flush_batch()

        return None

    def flush_batch(self) -> ASRBatch | None:
        """Flush pending batch and create ASRBatch.

        Returns:
            ASRBatch of pending records, None if no records
        """
        if not self._pending_batch:
            return None

        # Create batch
        batch_id = f"batch_{secrets.token_hex(16)}"
        merkle_root = self._compute_merkle_root(self._pending_batch)

        batch = ASRBatch(
            batch_id=batch_id,
            records=self._pending_batch.copy(),
            merkle_root=merkle_root,
        )

        # Clear pending
        self._pending_batch = []

        return batch

    def _compute_merkle_root(self, records: list[AgentStateRecord]) -> str:
        """Compute Merkle tree root of ASR records.

        Args:
            records: List of ASR records

        Returns:
            Hexadecimal Merkle root hash
        """
        if not records:
            return hashlib.sha256(b"").hexdigest()

        # Get leaf hashes
        hashes = [bytes.fromhex(r.signature) for r in records]

        # Build tree
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])  # Duplicate last if odd

            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                next_level.append(hashlib.sha256(combined).digest())
            hashes = next_level

        return hashes[0].hex()

    def get_merkle_proof(
        self,
        asr: AgentStateRecord,
        batch: ASRBatch,
    ) -> list[tuple[str, str]]:
        """Get Merkle proof for an ASR in a batch.

        Args:
            asr: The ASR record to prove
            batch: The batch containing the ASR

        Returns:
            List of (hash, position) tuples forming the proof
        """
        # Find index of ASR in batch
        try:
            index = next(
                i for i, r in enumerate(batch.records)
                if r.asr_id == asr.asr_id
            )
        except StopIteration:
            raise ValueError("ASR not found in batch")

        # Build proof
        hashes = [bytes.fromhex(r.signature) for r in batch.records]
        proof: list[tuple[str, str]] = []

        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])

            sibling_index = index ^ 1  # XOR with 1 to get sibling
            position = "right" if index % 2 == 0 else "left"
            proof.append((hashes[sibling_index].hex(), position))

            # Move to parent level
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                next_level.append(hashlib.sha256(combined).digest())

            hashes = next_level
            index = index // 2

        return proof

    @staticmethod
    def verify_merkle_proof(
        asr_signature: str,
        proof: list[tuple[str, str]],
        merkle_root: str,
    ) -> bool:
        """Verify a Merkle proof for an ASR.

        Args:
            asr_signature: The ASR's signature hash
            proof: List of (hash, position) tuples
            merkle_root: Expected Merkle root

        Returns:
            True if proof is valid
        """
        current = bytes.fromhex(asr_signature)

        for sibling_hash, position in proof:
            sibling = bytes.fromhex(sibling_hash)
            if position == "right":
                combined = current + sibling
            else:
                combined = sibling + current
            current = hashlib.sha256(combined).digest()

        return current.hex() == merkle_root


class ASREventTypes:
    """Predefined ASR event types for consistency."""

    # Authentication events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_RATE_LIMITED = "auth_rate_limited"

    # Cryptographic events
    KEY_GENERATED = "key_generated"
    KEY_ROTATED = "key_rotated"
    KEY_REVOKED = "key_revoked"
    ENCRYPT_SUCCESS = "encrypt_success"
    DECRYPT_SUCCESS = "decrypt_success"
    DECRYPT_FAILURE = "decrypt_failure"

    # PQC-specific events
    PQC_CIPHER_DETECTED = "pqc_cipher_detected"
    QUANTUM_RISK_DETECTED = "quantum_risk_detected"

    # Governance events
    RULE_VIOLATION = "rule_violation"
    STRIKE_ISSUED = "strike_issued"
    BAN_TRIGGERED = "ban_triggered"
    HEIR_TRANSFER_INITIATED = "heir_transfer_initiated"

    # Access events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGED = "permission_changed"

    # Blockchain events
    TX_SUBMITTED = "tx_submitted"
    TX_CONFIRMED = "tx_confirmed"
    TX_FAILED = "tx_failed"


def determine_pqc_status(
    algorithm: str,
    key_age_days: int = 0,
) -> PQCStatus:
    """Determine PQC status based on algorithm and key age.

    Args:
        algorithm: The cryptographic algorithm in use
        key_age_days: Age of the key in days

    Returns:
        PQCStatus indicating quantum safety
    """
    # ML-KEM algorithms are quantum-safe
    quantum_safe = {"ML-KEM-768", "ML-KEM-1024", "HYBRID"}

    # Check if algorithm is quantum-safe
    is_safe = any(safe in algorithm.upper() for safe in quantum_safe)

    if is_safe:
        # Check key age
        if key_age_days > 365:
            return PQCStatus.WARNING
        return PQCStatus.SAFE

    # Classical algorithms
    classical = {"AES", "ECDSA", "RSA"}
    is_classical = any(c in algorithm.upper() for c in classical)

    if is_classical:
        return PQCStatus.WARNING

    # Unknown algorithm
    return PQCStatus.CRITICAL
