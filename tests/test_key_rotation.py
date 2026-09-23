"""Tests for ML-KEM 90-day key rotation enforcement.

Covers policy, age tracking, rotation + grace, encapsulate rejection,
ASR KEY_ROTATED emission/verification, settings override, and concurrent rotate.
Follows test_pqc.py patterns (simulated engine when liboqs unavailable).
"""

from __future__ import annotations

import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Add src and config to path (same as test_pqc.py)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_manager(
    rotation_days: int = 90,
    grace_period_days: int = 7,
    asr_engine=None,
    tmp_path=None,
):
    from core.key_rotation import KeyRotationManager, KeyRotationPolicy
    from core.asr_engine import ASREngine

    if asr_engine is None and tmp_path is not None:
        asr_engine = ASREngine(storage_path=tmp_path)

    policy = KeyRotationPolicy(
        rotation_days=rotation_days,
        grace_period_days=grace_period_days,
    )
    return KeyRotationManager(
        policy=policy,
        allow_simulated=True,
        asr_engine=asr_engine,
        agent_id="test_agent",
    )


def _backdate_current(manager, days: float) -> None:
    """Mutate current key created_at into the past for age tests."""
    from core.pqc import MLKEMKeyPair

    assert manager._current is not None
    old = manager._current.keypair
    created = datetime.now(timezone.utc) - timedelta(days=days)
    manager._current.keypair = MLKEMKeyPair(
        public_key=old.public_key,
        secret_key=old.secret_key,
        algorithm=old.algorithm,
        created_at=created,
        key_id=old.key_id,
    )


class TestFreshKeyNotDue:
    """(1) Fresh key is not due for rotation."""

    def test_fresh_key_not_due(self):
        mgr = _make_manager(rotation_days=90)
        kp = mgr.initialize()
        assert kp.key_id is not None
        assert mgr.needs_rotation() is False
        assert mgr.key_age_days() < 1.0


class TestNeedsRotationByAge:
    """(2) Key older than N days → needs_rotation."""

    def test_key_older_than_n_days_needs_rotation(self):
        mgr = _make_manager(rotation_days=30)
        mgr.initialize()
        _backdate_current(mgr, days=31)
        assert mgr.needs_rotation() is True

    def test_key_just_under_threshold_not_due(self):
        mgr = _make_manager(rotation_days=30)
        mgr.initialize()
        _backdate_current(mgr, days=29.5)
        assert mgr.needs_rotation() is False


class TestRotateRetainsOldForGrace:
    """(3) rotate → new key_id, old retained for grace."""

    def test_rotate_new_key_id_old_retained(self, tmp_path):
        mgr = _make_manager(rotation_days=10, grace_period_days=7, tmp_path=tmp_path)
        old = mgr.initialize()
        old_id = old.key_id
        _backdate_current(mgr, days=11)

        result = mgr.rotate()

        assert result.new_keypair.key_id != old_id
        assert result.old_key_id == old_id
        assert mgr.current_key_id == result.new_keypair.key_id
        retired = mgr.get_retired_keys()
        assert len(retired) == 1
        assert retired[0].key_id == old_id
        # Decapsulate path still resolves in-grace old key
        recovered = mgr.get_keypair_for_decapsulate(old_id)
        assert recovered.key_id == old_id


class TestExpiredOldKeyRejected:
    """(4) Expired old key rejected for new encapsulate."""

    def test_expired_old_key_rejected_for_encapsulate(self, tmp_path):
        from core.key_rotation import KeyExpiredError, KeyRotationError

        mgr = _make_manager(rotation_days=10, grace_period_days=3, tmp_path=tmp_path)
        old = mgr.initialize()
        old_id = old.key_id
        _backdate_current(mgr, days=11)
        mgr.rotate()

        # Advance past grace
        past_grace = datetime.now(timezone.utc) + timedelta(days=4)

        with pytest.raises(KeyExpiredError, match="expired past grace"):
            mgr.encapsulate(key_id=old_id, now=past_grace)

        # Current key still works
        result = mgr.encapsulate(key_id=mgr.current_key_id)
        assert len(result.shared_secret) == 32

    def test_retired_in_grace_also_rejected_for_new_encapsulate(self, tmp_path):
        from core.key_rotation import KeyRotationError

        mgr = _make_manager(rotation_days=10, grace_period_days=7, tmp_path=tmp_path)
        old = mgr.initialize()
        old_id = old.key_id
        _backdate_current(mgr, days=11)
        mgr.rotate()

        with pytest.raises(KeyRotationError, match="retired"):
            mgr.encapsulate(key_id=old_id)


class TestASRKeyRotated:
    """(5) ASR KEY_ROTATED written and signature verifies."""

    def test_asr_key_rotated_written_and_verifies(self, tmp_path):
        from core.asr_engine import ASREventTypes

        mgr = _make_manager(rotation_days=5, grace_period_days=2, tmp_path=tmp_path)
        mgr.initialize()
        _backdate_current(mgr, days=6)

        result = mgr.rotate(store_asr=True)

        assert result.asr is not None
        assert result.asr.action == ASREventTypes.KEY_ROTATED
        assert result.asr.verify_signature() is True
        assert result.asr.metadata["old_key_id"] == result.old_key_id
        assert result.asr.metadata["new_key_id"] == result.new_keypair.key_id

        # Persisted to storage
        loaded = mgr._asr_engine.load_asr(result.asr.asr_id)
        assert loaded is not None
        assert loaded.verify_signature() is True
        assert loaded.action == ASREventTypes.KEY_ROTATED


class TestSettingsOverride:
    """(6) settings override key_rotation_days."""

    def test_settings_override_key_rotation_days(self):
        from config.settings import Settings
        from core.key_rotation import KeyRotationPolicy, KeyRotationManager

        settings = Settings(key_rotation_days=14)
        policy = KeyRotationPolicy.from_settings(settings)
        assert policy.rotation_days == 14

        mgr = KeyRotationManager(policy=policy, allow_simulated=True)
        mgr.initialize()
        _backdate_current(mgr, days=15)
        assert mgr.needs_rotation() is True

        mgr2 = KeyRotationManager(
            policy=KeyRotationPolicy.from_settings(Settings(key_rotation_days=90)),
            allow_simulated=True,
        )
        mgr2.initialize()
        _backdate_current(mgr2, days=15)
        assert mgr2.needs_rotation() is False


class TestConcurrentRotate:
    """(7) concurrent rotate safe / single-winner."""

    def test_concurrent_rotate_single_winner(self, tmp_path):
        mgr = _make_manager(rotation_days=1, grace_period_days=7, tmp_path=tmp_path)
        mgr.initialize()
        _backdate_current(mgr, days=2)

        winners: list[str] = []
        errors: list[BaseException] = []
        barrier = threading.Barrier(8)

        def worker() -> None:
            try:
                barrier.wait(timeout=5)
                result = mgr.rotate(force=True)
                winners.append(result.new_keypair.key_id)
            except BaseException as exc:  # noqa: BLE001 — collect for assert
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # All threads completed; every rotate with force=True succeeds serially,
        # but key_ids must be unique (no shared corrupt state) and final current
        # matches the last successful rotation.
        assert len(errors) == 0, f"unexpected errors: {errors}"
        assert len(winners) == 8
        assert len(set(winners)) == 8
        assert mgr.current_key_id == winners[-1] or mgr.current_key_id in winners
        # Exactly 8 retired predecessors retained (or purged only if grace hit —
        # grace is 7d so all retained)
        assert len(mgr.get_retired_keys()) == 8

    def test_concurrent_needs_rotation_single_effective_rotate(self, tmp_path):
        """Without force, only first due rotation should win; others raise."""
        from core.key_rotation import KeyRotationError

        mgr = _make_manager(rotation_days=1, grace_period_days=7, tmp_path=tmp_path)
        mgr.initialize()
        _backdate_current(mgr, days=2)

        success = []
        failures = []
        lock = threading.Lock()
        barrier = threading.Barrier(6)

        def worker() -> None:
            barrier.wait(timeout=5)
            try:
                result = mgr.rotate(force=False)
                with lock:
                    success.append(result.new_keypair.key_id)
            except KeyRotationError as exc:
                with lock:
                    failures.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Single-winner: exactly one success; rest report not due / error
        assert len(success) == 1
        assert len(failures) == 5
        assert mgr.current_key_id == success[0]


class TestPolicyValidation:
    """Policy edge cases."""

    def test_invalid_rotation_days(self):
        from core.key_rotation import KeyRotationPolicy

        with pytest.raises(ValueError):
            KeyRotationPolicy(rotation_days=0)

    def test_default_matches_constant(self):
        from config.constants import DEFAULT_KEY_ROTATION_DAYS
        from core.key_rotation import KeyRotationPolicy

        assert KeyRotationPolicy().rotation_days == DEFAULT_KEY_ROTATION_DAYS
        assert DEFAULT_KEY_ROTATION_DAYS == 90
