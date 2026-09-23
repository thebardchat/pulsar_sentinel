"""ML-KEM key rotation policy and manager for PULSAR SENTINEL.

Enforces the documented 90-day (configurable) ML-KEM key rotation interval.
Docs and settings claimed automatic rotation; this module implements it.

Design:
- KeyRotationPolicy: rotation interval + grace period for retired keys
- KeyRotationManager: tracks current/retired keys, rotates via PQC helpers,
  rejects encapsulate against expired retired keys, emits ASR KEY_ROTATED
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from config.constants import (
    DEFAULT_KEY_ROTATION_DAYS,
    PQCSecurityLevel,
    PQCStatus,
    ThreatLevel,
)
from config.logging import SecurityEventLogger
from config.settings import Settings, get_settings
from core.asr_engine import AgentStateRecord, ASREngine, ASREventTypes
from core.pqc import (
    EncapsulationResult,
    MLKEMKeyPair,
    get_pqc_engine,
)

# Default grace period: retired keys remain usable for decapsulation only
DEFAULT_KEY_GRACE_PERIOD_DAYS: int = 7

logger = SecurityEventLogger("key_rotation")


class KeyRotationError(Exception):
    """Base error for key rotation failures."""


class KeyExpiredError(KeyRotationError):
    """Raised when encapsulate is attempted with an expired retired key."""


@dataclass(frozen=True)
class KeyRotationPolicy:
    """Policy controlling ML-KEM key lifetime and grace retention.

    Attributes:
        rotation_days: Maximum age in days before rotation is due
        grace_period_days: Days to retain retired keys for decapsulation
    """

    rotation_days: int = DEFAULT_KEY_ROTATION_DAYS
    grace_period_days: int = DEFAULT_KEY_GRACE_PERIOD_DAYS

    def __post_init__(self) -> None:
        if self.rotation_days < 1:
            raise ValueError("rotation_days must be >= 1")
        if self.grace_period_days < 0:
            raise ValueError("grace_period_days must be >= 0")

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        grace_period_days: int = DEFAULT_KEY_GRACE_PERIOD_DAYS,
    ) -> KeyRotationPolicy:
        """Build policy from application settings (key_rotation_days)."""
        if settings is None:
            settings = get_settings()
        return cls(
            rotation_days=int(settings.key_rotation_days),
            grace_period_days=grace_period_days,
        )


@dataclass
class ManagedKeyRecord:
    """Tracked key with optional retirement timestamp."""

    keypair: MLKEMKeyPair
    retired_at: datetime | None = None

    @property
    def key_id(self) -> str:
        return self.keypair.key_id

    @property
    def created_at(self) -> datetime:
        created = self.keypair.created_at
        if created.tzinfo is None:
            return created.replace(tzinfo=timezone.utc)
        return created

    def age_days(self, now: datetime | None = None) -> float:
        """Return key age in fractional days."""
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        delta = now - self.created_at
        return delta.total_seconds() / 86400.0

    def is_past_grace(self, grace_period_days: int, now: datetime | None = None) -> bool:
        """True if retired and past the grace retention window."""
        if self.retired_at is None:
            return False
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        retired = self.retired_at
        if retired.tzinfo is None:
            retired = retired.replace(tzinfo=timezone.utc)
        return now > retired + timedelta(days=grace_period_days)


@dataclass
class RotationResult:
    """Outcome of a successful key rotation."""

    new_keypair: MLKEMKeyPair
    old_key_id: str
    asr: AgentStateRecord | None = None
    rotated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class KeyRotationManager:
    """Manages ML-KEM key lifecycle: age tracking, rotation, grace, ASR.

    Example:
        >>> mgr = KeyRotationManager(policy=KeyRotationPolicy(rotation_days=90))
        >>> kp = mgr.initialize()
        >>> if mgr.needs_rotation():
        ...     result = mgr.rotate()
    """

    def __init__(
        self,
        policy: KeyRotationPolicy | None = None,
        security_level: int = PQCSecurityLevel.LEVEL_768,
        allow_simulated: bool = True,
        asr_engine: ASREngine | None = None,
        agent_id: str = "pulsar_sentinel",
        pqc_engine: Any | None = None,
    ) -> None:
        """Initialize the rotation manager.

        Args:
            policy: Rotation/grace policy (defaults from settings constants)
            security_level: ML-KEM level passed to PQC engine factory
            allow_simulated: Use simulated engine when liboqs unavailable
            asr_engine: Optional ASR engine for KEY_ROTATED events
            agent_id: Agent id recorded on ASR events
            pqc_engine: Optional pre-built PQC engine (for tests/injection)
        """
        self._policy = policy or KeyRotationPolicy()
        self._security_level = security_level
        self._allow_simulated = allow_simulated
        self._asr_engine = asr_engine
        self._agent_id = agent_id
        self._pqc_engine = pqc_engine
        self._lock = threading.RLock()
        self._current: ManagedKeyRecord | None = None
        self._retired: list[ManagedKeyRecord] = []
        self._last_rotation_asr: AgentStateRecord | None = None

    @property
    def policy(self) -> KeyRotationPolicy:
        """Active rotation policy."""
        return self._policy

    @property
    def current_keypair(self) -> MLKEMKeyPair | None:
        """Current active key pair, if initialized."""
        with self._lock:
            return self._current.keypair if self._current else None

    @property
    def current_key_id(self) -> str | None:
        """Current key id, if initialized."""
        with self._lock:
            return self._current.key_id if self._current else None

    @property
    def last_rotation_asr(self) -> AgentStateRecord | None:
        """Most recent KEY_ROTATED ASR, if any."""
        return self._last_rotation_asr

    def _engine(self) -> Any:
        if self._pqc_engine is not None:
            return self._pqc_engine
        self._pqc_engine = get_pqc_engine(
            security_level=self._security_level,
            allow_simulated=self._allow_simulated,
        )
        return self._pqc_engine

    def initialize(self, keypair: MLKEMKeyPair | None = None) -> MLKEMKeyPair:
        """Set the initial current key (generate if not provided)."""
        with self._lock:
            if keypair is None:
                keypair = self._engine().generate_keypair()
            self._current = ManagedKeyRecord(keypair=keypair)
            self._retired.clear()
            return keypair

    def key_age_days(self, now: datetime | None = None) -> float:
        """Age of the current key in days. Raises if not initialized."""
        with self._lock:
            if self._current is None:
                raise KeyRotationError("No current key; call initialize() first")
            return self._current.age_days(now)

    def needs_rotation(self, now: datetime | None = None) -> bool:
        """True if current key age exceeds policy.rotation_days."""
        with self._lock:
            if self._current is None:
                return True
            return self._current.age_days(now) >= float(self._policy.rotation_days)

    def get_retired_keys(self) -> list[MLKEMKeyPair]:
        """Return copies of retired key pairs still tracked (grace window)."""
        with self._lock:
            return [r.keypair for r in self._retired]

    def _find_record(self, key_id: str) -> ManagedKeyRecord | None:
        if self._current and self._current.key_id == key_id:
            return self._current
        for record in self._retired:
            if record.key_id == key_id:
                return record
        return None

    def is_valid_for_encapsulate(
        self,
        key_id: str,
        now: datetime | None = None,
    ) -> bool:
        """Only the current (non-retired) key may be used for new encapsulation."""
        with self._lock:
            if self._current is None:
                return False
            if self._current.key_id == key_id:
                return True
            # Retired keys — even within grace — are not valid for new encapsulate
            record = self._find_record(key_id)
            if record is None:
                return False
            # Explicitly expired (past grace) vs merely retired
            return False

    def encapsulate(
        self,
        public_key: bytes | None = None,
        *,
        key_id: str | None = None,
        now: datetime | None = None,
    ) -> EncapsulationResult:
        """Encapsulate using the current key (or explicit public_key).

        Rejects encapsulation when ``key_id`` refers to a retired key that
        has passed the grace period (expired). Retired-but-in-grace keys are
        also rejected for *new* encapsulate — grace is for decapsulation only.

        Args:
            public_key: Optional public key bytes; defaults to current key
            key_id: Optional key id to validate before encapsulating
            now: Optional clock override for expiry checks

        Returns:
            EncapsulationResult from the underlying PQC engine

        Raises:
            KeyExpiredError: If key_id is a retired key past grace
            KeyRotationError: If no current key or key_id is retired (in grace)
        """
        with self._lock:
            if self._current is None:
                raise KeyRotationError("No current key; call initialize() first")

            target_id = key_id
            if target_id is not None:
                record = self._find_record(target_id)
                if record is None:
                    raise KeyRotationError(f"Unknown key_id: {target_id}")
                if record.retired_at is not None:
                    if record.is_past_grace(self._policy.grace_period_days, now):
                        raise KeyExpiredError(
                            f"Key {target_id} expired past grace period; "
                            "cannot encapsulate"
                        )
                    raise KeyRotationError(
                        f"Key {target_id} is retired; use current key "
                        f"{self._current.key_id} for new encapsulation"
                    )
                if record.key_id != self._current.key_id:
                    raise KeyRotationError(
                        f"Key {target_id} is not the current encapsulation key"
                    )

            pk = public_key if public_key is not None else self._current.keypair.public_key
            return self._engine().encapsulate(pk)

    def get_keypair_for_decapsulate(
        self,
        key_id: str,
        now: datetime | None = None,
    ) -> MLKEMKeyPair:
        """Return a keypair for decapsulation (current or in-grace retired).

        Raises:
            KeyExpiredError: If the key is past grace or unknown
        """
        with self._lock:
            record = self._find_record(key_id)
            if record is None:
                raise KeyExpiredError(f"Unknown or purged key_id: {key_id}")
            if record.retired_at is not None and record.is_past_grace(
                self._policy.grace_period_days, now
            ):
                raise KeyExpiredError(
                    f"Key {key_id} expired past grace period; cannot decapsulate"
                )
            return record.keypair

    def purge_expired(self, now: datetime | None = None) -> int:
        """Drop retired keys past the grace window. Returns count removed."""
        with self._lock:
            remaining: list[ManagedKeyRecord] = []
            removed = 0
            for record in self._retired:
                if record.is_past_grace(self._policy.grace_period_days, now):
                    removed += 1
                else:
                    remaining.append(record)
            self._retired = remaining
            return removed

    def rotate(
        self,
        *,
        force: bool = False,
        now: datetime | None = None,
        store_asr: bool = True,
    ) -> RotationResult:
        """Generate a new ML-KEM key and retire the current one into grace.

        Thread-safe: concurrent callers serialize on an RLock; only one
        rotation proceeds (single-winner). Callers that lose the race after
        another rotation succeeded see needs_rotation False unless force=True.

        Args:
            force: Rotate even if not yet due
            now: Optional clock override
            store_asr: Persist ASR to engine storage when available

        Returns:
            RotationResult with new keypair and optional ASR

        Raises:
            KeyRotationError: If not initialized or rotation not due
        """
        with self._lock:
            if self._current is None:
                raise KeyRotationError("No current key; call initialize() first")

            if not force and not self.needs_rotation(now):
                raise KeyRotationError(
                    f"Rotation not due; key age "
                    f"{self._current.age_days(now):.2f}d < "
                    f"{self._policy.rotation_days}d"
                )

            now = now or datetime.now(timezone.utc)
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)

            old = self._current
            old_key_id = old.key_id
            old.retired_at = now

            new_keypair = self._engine().generate_keypair()
            # Ensure created_at reflects rotation time for deterministic tests
            if new_keypair.created_at != now:
                # MLKEMKeyPair is a dataclass; replace with same material + now
                new_keypair = MLKEMKeyPair(
                    public_key=new_keypair.public_key,
                    secret_key=new_keypair.secret_key,
                    algorithm=new_keypair.algorithm,
                    created_at=now,
                    key_id=new_keypair.key_id,
                )

            self._retired.append(old)
            self._current = ManagedKeyRecord(keypair=new_keypair)
            self.purge_expired(now)

            asr: AgentStateRecord | None = None
            if self._asr_engine is not None:
                asr = self._asr_engine.create_asr(
                    agent_id=self._agent_id,
                    action=ASREventTypes.KEY_ROTATED,
                    threat_level=ThreatLevel.INFO,
                    pqc_status=PQCStatus.SAFE,
                    metadata={
                        "old_key_id": old_key_id,
                        "new_key_id": new_keypair.key_id,
                        "algorithm": new_keypair.algorithm,
                        "rotation_days": self._policy.rotation_days,
                        "grace_period_days": self._policy.grace_period_days,
                        "rotated_at": now.isoformat(),
                    },
                )
                if store_asr:
                    self._asr_engine.store_asr(asr)
                self._last_rotation_asr = asr

            logger.log_crypto_operation(
                operation="key_rotate",
                algorithm=new_keypair.algorithm,
                success=True,
                duration_ms=0.0,
            )

            return RotationResult(
                new_keypair=new_keypair,
                old_key_id=old_key_id,
                asr=asr,
                rotated_at=now,
            )
