"""Integration Tests for PULSAR SENTINEL.

End-to-end tests covering:
- Full encryption/decryption workflows
- Authentication flows
- ASR to blockchain logging
- Governance rule enforcement
"""

import os
import sys
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))


class TestCryptoWorkflow:
    """Integration tests for cryptographic workflows."""

    def test_legacy_crypto_full_workflow(self, tmp_path):
        """Test complete legacy encryption workflow."""
        from core.legacy import LegacyCrypto
        from core.asr_engine import ASREngine, ThreatLevel, PQCStatus

        # Initialize components
        crypto = LegacyCrypto()
        asr_engine = ASREngine(storage_path=tmp_path)

        # User data
        user_id = "integration_user"
        password = b"secure_password_123"
        plaintext = b"Sensitive data to encrypt for testing purposes."

        # Encrypt
        key, salt = crypto.derive_key(password)
        ciphertext = crypto.encrypt(plaintext, key, salt)

        # Create ASR for encryption
        encrypt_asr = asr_engine.create_asr(
            agent_id=user_id,
            action="encrypt_aes",
            threat_level=ThreatLevel.INFO,
            pqc_status=PQCStatus.WARNING,  # AES is not quantum-safe
            metadata={"algorithm": "AES-256-CBC"},
        )
        asr_engine.store_asr(encrypt_asr)

        # Decrypt
        decrypted = crypto.decrypt(ciphertext, key)
        assert decrypted == plaintext

        # Create ASR for decryption
        decrypt_asr = asr_engine.create_asr(
            agent_id=user_id,
            action="decrypt_aes",
            threat_level=ThreatLevel.INFO,
            pqc_status=PQCStatus.WARNING,
        )
        asr_engine.store_asr(decrypt_asr)

        # Verify ASR records
        records = asr_engine.list_asr_by_agent(user_id)
        assert len(records) == 2

    def test_aes_ciphertext_roundtrip(self):
        """Test AES ciphertext serialization roundtrip."""
        from core.legacy import LegacyCrypto, AESCiphertext

        crypto = LegacyCrypto()
        plaintext = b"Test message for serialization"
        password = b"test_password"

        # Encrypt
        key, salt = crypto.derive_key(password)
        ciphertext = crypto.encrypt(plaintext, key, salt)

        # Serialize
        serialized = ciphertext.to_bytes()

        # Deserialize
        restored = AESCiphertext.from_bytes(serialized)

        # Decrypt restored ciphertext
        decrypted = crypto.decrypt(restored, key)
        assert decrypted == plaintext


class TestASRWorkflow:
    """Integration tests for ASR workflows."""

    def test_asr_batch_workflow(self, tmp_path):
        """Test complete ASR batching workflow."""
        from core.asr_engine import ASREngine, ThreatLevel, PQCStatus

        engine = ASREngine(storage_path=tmp_path)
        engine._max_batch_size = 5  # Small batch for testing

        # Create ASRs
        created_asrs = []
        for i in range(5):
            asr = engine.create_asr(
                agent_id=f"batch_user_{i % 2}",
                action=f"action_{i}",
                threat_level=ThreatLevel.INFO,
                pqc_status=PQCStatus.SAFE,
            )
            created_asrs.append(asr)
            engine.add_to_batch(asr)

        # Flush should create batch
        batch = engine.flush_batch()
        assert batch is not None
        assert len(batch.records) == 5

        # Verify Merkle root
        assert batch.merkle_root != ""
        assert len(batch.merkle_root) == 64  # SHA-256 hex

        # Verify proof for each ASR
        for asr in created_asrs:
            proof = engine.get_merkle_proof(asr, batch)
            assert len(proof) > 0

            # Verify proof
            is_valid = ASREngine.verify_merkle_proof(
                asr.signature,
                proof,
                batch.merkle_root,
            )
            assert is_valid

    def test_asr_threat_level_filtering(self, tmp_path):
        """Test ASR filtering by threat level."""
        from core.asr_engine import ASREngine, ThreatLevel

        engine = ASREngine(storage_path=tmp_path)

        # Create ASRs with different threat levels
        for level in ThreatLevel:
            asr = engine.create_asr(
                agent_id="filter_user",
                action=f"action_level_{level.value}",
                threat_level=level,
            )
            engine.store_asr(asr)

        # Filter by minimum threat level
        all_records = engine.list_asr_by_agent("filter_user", threat_level_min=1)
        assert len(all_records) == 5

        warning_plus = engine.list_asr_by_agent("filter_user", threat_level_min=3)
        assert len(warning_plus) == 3  # WARNING, ALERT, CRITICAL

        critical_only = engine.list_asr_by_agent("filter_user", threat_level_min=5)
        assert len(critical_only) == 1


class TestGovernanceWorkflow:
    """Integration tests for governance workflows."""

    def test_user_lifecycle(self):
        """Test complete user lifecycle with governance."""
        from governance.access_control import AccessController, UserRole, TierType
        from governance.rules_engine import RulesEngine
        from governance.pts_calculator import PTSCalculator, PTSTier

        # Initialize components
        access_ctrl = AccessController()
        rules_engine = RulesEngine()
        pts_calc = PTSCalculator()

        user_id = "lifecycle_user"

        # 1. Register user
        profile = access_ctrl.register_user(
            user_id=user_id,
            role=UserRole.USER,
            tier=TierType.LEGACY_BUILDER,
        )
        assert profile.role == UserRole.USER

        # 2. User makes requests - check rate limit
        for i in range(3):
            result = access_ctrl.check_rate_limit(user_id)
            assert result.allowed

        # 3. Check PTS - should be safe
        pts = pts_calc.calculate_pts(user_id)
        assert pts.tier == PTSTier.SAFE

        # 4. User commits violation
        pts_calc.record_access_violation(user_id, "unauthorized_access")

        # 5. Issue strike
        strikes = rules_engine.issue_strike(user_id, "policy_violation")
        assert strikes == 1

        # 6. Upgrade tier
        access_ctrl.update_tier(user_id, TierType.SENTINEL_CORE)
        profile = access_ctrl.get_user(user_id)
        assert profile.tier == TierType.SENTINEL_CORE

        # 7. Multiple violations escalate PTS
        for i in range(5):
            pts_calc.record_quantum_risk(user_id, "weak_cipher")

        pts = pts_calc.calculate_pts(user_id)
        assert pts.tier in (PTSTier.CAUTION, PTSTier.CRITICAL)

    def test_strike_to_ban_workflow(self):
        """Test workflow from strikes to ban."""
        from governance.rules_engine import RulesEngine

        engine = RulesEngine()
        user_id = "ban_test_user"

        # Issue strikes until banned
        for i in range(3):
            engine.issue_strike(user_id, f"violation_{i}")

        # Check that user is banned
        result = engine.check_strike_policy(user_id)
        assert result.passed is False
        assert "banned" in result.violation.description.lower()

        # Subsequent requests should fail
        result = engine.check_strike_policy(user_id)
        assert result.passed is False

    def test_pts_monitoring_workflow(self):
        """Test PTS monitoring with tier transitions."""
        from governance.pts_calculator import PTSCalculator, PTSMonitor, PTSTier

        calc = PTSCalculator()
        tier_changes = []

        def on_change(user_id, old_tier, new_tier, score):
            tier_changes.append((user_id, old_tier, new_tier))

        monitor = PTSMonitor(calculator=calc, alert_callback=on_change)
        user_id = "monitor_user"

        # Initial check - safe
        score = monitor.check_user(user_id)
        assert score.tier == PTSTier.SAFE

        # Add violations
        for i in range(5):
            calc.record_access_violation(user_id, f"v_{i}")

        # Check again - should trigger tier change
        score = monitor.check_user(user_id)

        # Verify tier change was recorded
        assert len(tier_changes) >= 1
        assert tier_changes[-1][0] == user_id


class TestMultiComponentIntegration:
    """Tests for multi-component integration."""

    def test_crypto_with_governance(self, tmp_path):
        """Test cryptographic operations with governance checks."""
        from core.legacy import LegacyCrypto
        from core.asr_engine import ASREngine, ThreatLevel
        from governance.access_control import (
            AccessController,
            UserRole,
            PERMISSION_ENCRYPT,
        )
        from governance.pts_calculator import PTSCalculator

        # Initialize all components
        crypto = LegacyCrypto()
        asr_engine = ASREngine(storage_path=tmp_path)
        access_ctrl = AccessController()
        pts_calc = PTSCalculator()

        user_id = "multi_component_user"

        # Register user
        access_ctrl.register_user(user_id, role=UserRole.USER)

        # Check permission
        has_perm = access_ctrl.has_permission(user_id, PERMISSION_ENCRYPT)
        assert has_perm

        # Check rate limit
        rate_result = access_ctrl.check_rate_limit(user_id)
        assert rate_result.allowed

        # Perform encryption
        password = b"test_password"
        key, salt = crypto.derive_key(password)
        plaintext = b"Secret data"
        ciphertext = crypto.encrypt(plaintext, key, salt)

        # Log ASR
        asr = asr_engine.create_asr(
            agent_id=user_id,
            action="encrypt",
            threat_level=ThreatLevel.INFO,
        )
        asr_engine.store_asr(asr)

        # Verify PTS is still safe
        pts = pts_calc.calculate_pts(user_id)
        assert pts.is_safe

    def test_failed_operation_pts_impact(self, tmp_path):
        """Test that failed operations impact PTS."""
        from core.asr_engine import ASREngine, ThreatLevel, PQCStatus
        from governance.pts_calculator import PTSCalculator
        from governance.rules_engine import RulesEngine

        asr_engine = ASREngine(storage_path=tmp_path)
        pts_calc = PTSCalculator()
        rules_engine = RulesEngine()

        user_id = "failure_impact_user"

        # Simulate multiple signature failures
        for i in range(3):
            pts_calc.record_signature_failure(user_id, "decrypt_failure")

            # Log ASR for failure
            asr = asr_engine.create_asr(
                agent_id=user_id,
                action="decrypt_failed",
                threat_level=ThreatLevel.CAUTION,
                pqc_status=PQCStatus.WARNING,
            )
            asr_engine.store_asr(asr)

            # Issue strike
            rules_engine.issue_strike(user_id, "signature_failure")

        # Verify PTS has increased
        pts = pts_calc.calculate_pts(user_id)
        assert pts.total_score > 0
        assert pts.factors.signature_failures == 3

        # Verify strikes
        assert rules_engine.get_strikes(user_id) == 3


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_empty_asr_batch(self, tmp_path):
        """Test flushing empty batch."""
        from core.asr_engine import ASREngine

        engine = ASREngine(storage_path=tmp_path)
        batch = engine.flush_batch()
        assert batch is None

    def test_single_asr_merkle(self, tmp_path):
        """Test Merkle tree with single ASR."""
        from core.asr_engine import ASREngine, ThreatLevel

        engine = ASREngine(storage_path=tmp_path)

        asr = engine.create_asr(
            agent_id="single_user",
            action="single_action",
            threat_level=ThreatLevel.INFO,
        )
        engine.add_to_batch(asr)
        batch = engine.flush_batch()

        assert batch is not None
        assert len(batch.records) == 1
        assert batch.merkle_root == asr.signature

    def test_rate_limit_boundary(self):
        """Test exact rate limit boundary."""
        from governance.access_control import AccessController, UserRole, TierType

        controller = AccessController()
        controller.register_user(
            "boundary_user",
            role=UserRole.USER,
            tier=TierType.LEGACY_BUILDER,  # 5 req/min
        )

        # Make exactly 5 requests
        results = []
        for i in range(6):
            result = controller.check_rate_limit("boundary_user")
            results.append(result.allowed)

        # First 5 should be allowed, 6th should be denied
        assert results[:5] == [True, True, True, True, True]
        assert results[5] is False

    def test_pts_zero_score(self):
        """Test PTS with no events."""
        from governance.pts_calculator import PTSCalculator, PTSTier

        calc = PTSCalculator()
        score = calc.calculate_pts("nonexistent_user")

        assert score.total_score == 0
        assert score.tier == PTSTier.SAFE
        assert all(v == 0 for v in score.breakdown.values())

    def test_concurrent_asr_creation(self, tmp_path):
        """Test creating multiple ASRs rapidly."""
        from core.asr_engine import ASREngine, ThreatLevel

        engine = ASREngine(storage_path=tmp_path)

        # Create many ASRs quickly
        asrs = []
        for i in range(100):
            asr = engine.create_asr(
                agent_id=f"concurrent_user_{i % 10}",
                action=f"action_{i}",
                threat_level=ThreatLevel.INFO,
            )
            asrs.append(asr)

        # Verify all have unique IDs
        asr_ids = [a.asr_id for a in asrs]
        assert len(set(asr_ids)) == 100

        # Verify all signatures are valid
        for asr in asrs:
            assert asr.verify_signature()
