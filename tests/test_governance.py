"""Tests for Governance module.

Tests cover:
- Rules engine (RC codes)
- PTS calculator
- Access control and rate limiting
- User role management
"""

import sys
import time
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))


class TestRulesEngine:
    """Tests for self-governance rules engine."""

    def test_rc_1_01_signature_required(self):
        """Test RC 1.01: Signature required rule."""
        from governance.rules_engine import RulesEngine, RuleCode

        engine = RulesEngine()

        # Test with valid signature
        result = engine.check_signature_required(
            has_signature=True,
            signature_valid=True,
            user_id="user123",
        )
        assert result.passed is True
        assert result.rule_code == RuleCode.RC_1_01

        # Test with missing signature
        result = engine.check_signature_required(
            has_signature=False,
            signature_valid=False,
            user_id="user123",
        )
        assert result.passed is False
        assert result.violation is not None
        assert result.action_required == "reject_request"

        # Test with invalid signature
        result = engine.check_signature_required(
            has_signature=True,
            signature_valid=False,
            user_id="user123",
        )
        assert result.passed is False

    def test_rc_1_02_heir_transfer(self):
        """Test RC 1.02: Heir transfer on unresponsive."""
        from governance.rules_engine import RulesEngine, UserState, RuleCode

        engine = RulesEngine()

        # Active user should pass
        active_user = UserState(
            user_id="active_user",
            last_activity=datetime.now(timezone.utc),
            heir_address="0xheir",
        )
        result = engine.check_heir_transfer(active_user)
        assert result.passed is True

        # Inactive user should trigger heir transfer
        inactive_user = UserState(
            user_id="inactive_user",
            last_activity=datetime.now(timezone.utc) - timedelta(days=100),
            heir_address="0xheir",
        )
        result = engine.check_heir_transfer(inactive_user)
        assert result.passed is False
        assert result.rule_code == RuleCode.RC_1_02
        assert result.action_required == "initiate_heir_transfer"

        # Inactive user without heir should pass (no transfer possible)
        no_heir_user = UserState(
            user_id="no_heir_user",
            last_activity=datetime.now(timezone.utc) - timedelta(days=100),
            heir_address=None,
        )
        result = engine.check_heir_transfer(no_heir_user)
        assert result.passed is True  # No heir to transfer to

    def test_rc_2_01_strike_policy(self):
        """Test RC 2.01: Three-strike rule."""
        from governance.rules_engine import RulesEngine, RuleCode

        engine = RulesEngine()
        user_id = "strike_test_user"

        # Initially should pass
        result = engine.check_strike_policy(user_id)
        assert result.passed is True

        # Issue strikes
        engine.issue_strike(user_id, "violation_1")
        engine.issue_strike(user_id, "violation_2")
        result = engine.check_strike_policy(user_id)
        assert result.passed is True  # Still under threshold

        # Third strike triggers ban
        engine.issue_strike(user_id, "violation_3")
        result = engine.check_strike_policy(user_id)
        assert result.passed is False
        assert result.rule_code == RuleCode.RC_2_01
        assert result.action_required == "issue_ban"

    def test_strike_reset(self):
        """Test strike reset functionality."""
        from governance.rules_engine import RulesEngine

        engine = RulesEngine()
        user_id = "reset_test_user"

        # Issue strikes
        for i in range(3):
            engine.issue_strike(user_id, f"violation_{i}")

        assert engine.get_strikes(user_id) == 3

        # Reset strikes
        engine.reset_strikes(user_id)
        assert engine.get_strikes(user_id) == 0

        # Should pass now
        result = engine.check_strike_policy(user_id)
        assert result.passed is True

    def test_rc_3_02_transaction_fallback(self):
        """Test RC 3.02: Transaction fallback rule."""
        from governance.rules_engine import RulesEngine, RuleCode

        engine = RulesEngine()

        # Successful transaction should pass
        result = engine.check_transaction_fallback(
            tx_success=True,
            user_id="user123",
            tx_type="transfer",
        )
        assert result.passed is True

        # Failed transaction triggers fallback
        result = engine.check_transaction_fallback(
            tx_success=False,
            user_id="user123",
            tx_type="transfer",
        )
        assert result.passed is False
        assert result.rule_code == RuleCode.RC_3_02
        assert result.action_required == "initiate_gryphon_fallback"

    def test_violation_recording(self):
        """Test violation recording."""
        from governance.rules_engine import RulesEngine

        engine = RulesEngine()

        # Trigger a violation
        engine.check_signature_required(
            has_signature=False,
            signature_valid=False,
            user_id="violation_user",
        )

        violations = engine.get_violations("violation_user")
        assert len(violations) == 1
        assert violations[0].rule_code.value == "RC_1.01"


class TestPTSCalculator:
    """Tests for Points Toward Threat Score calculator."""

    def test_pts_factors_creation(self):
        """Test PTSFactors creation."""
        from governance.pts_calculator import PTSFactors

        factors = PTSFactors(
            quantum_risk_count=2,
            access_violation_count=3,
            rate_limit_violations=5,
            signature_failures=1,
        )

        assert factors.quantum_risk_count == 2
        assert factors.access_violation_count == 3

    def test_pts_calculation_safe(self):
        """Test PTS calculation for safe tier."""
        from governance.pts_calculator import PTSCalculator, PTSTier

        calc = PTSCalculator()
        user_id = "safe_user"

        # No events = safe
        score = calc.calculate_pts(user_id)
        assert score.total_score == 0
        assert score.tier == PTSTier.SAFE
        assert score.is_safe is True

    def test_pts_calculation_caution(self):
        """Test PTS calculation for caution tier."""
        from governance.pts_calculator import PTSCalculator, PTSTier

        calc = PTSCalculator()
        user_id = "caution_user"

        # Add some violations to reach caution tier
        calc.record_quantum_risk(user_id, "weak_cipher")
        calc.record_access_violation(user_id, "unauthorized")
        calc.record_rate_limit_violation(user_id, "/api/test", 10, 5)

        score = calc.calculate_pts(user_id)
        assert score.tier == PTSTier.CAUTION
        assert score.is_caution is True
        assert 50 <= score.total_score < 150

    def test_pts_calculation_critical(self):
        """Test PTS calculation for critical tier."""
        from governance.pts_calculator import PTSCalculator, PTSTier

        calc = PTSCalculator()
        user_id = "critical_user"

        # Add many violations to reach critical tier
        for i in range(10):
            calc.record_quantum_risk(user_id, f"risk_{i}")
            calc.record_access_violation(user_id, f"violation_{i}")

        score = calc.calculate_pts(user_id)
        assert score.tier == PTSTier.CRITICAL
        assert score.is_critical is True
        assert score.total_score >= 150

    def test_pts_breakdown(self):
        """Test PTS score breakdown."""
        from governance.pts_calculator import PTSCalculator

        calc = PTSCalculator()
        user_id = "breakdown_user"

        calc.record_quantum_risk(user_id, "risk1")
        calc.record_signature_failure(user_id, "fail1")

        score = calc.calculate_pts(user_id)

        assert "quantum_risk" in score.breakdown
        assert "signature_failure" in score.breakdown
        assert score.breakdown["quantum_risk"] > 0
        assert score.breakdown["signature_failure"] > 0

    def test_pts_user_reset(self):
        """Test resetting a user's PTS events."""
        from governance.pts_calculator import PTSCalculator, PTSTier

        calc = PTSCalculator()
        user_id = "reset_user"

        # Add violations
        for i in range(5):
            calc.record_access_violation(user_id, f"v_{i}")

        assert calc.calculate_pts(user_id).tier != PTSTier.SAFE

        # Reset user
        calc.reset_user(user_id)

        assert calc.calculate_pts(user_id).tier == PTSTier.SAFE
        assert calc.calculate_pts(user_id).total_score == 0

    def test_pts_get_critical_users(self):
        """Test getting all critical users."""
        from governance.pts_calculator import PTSCalculator

        calc = PTSCalculator()

        # Make some users critical
        for i in range(3):
            user_id = f"critical_{i}"
            for j in range(15):
                calc.record_access_violation(user_id, f"v_{j}")

        # Make one safe user
        calc.record_quantum_risk("safe_user", "minor")

        critical = calc.get_all_critical_users()
        assert len(critical) == 3


class TestAccessController:
    """Tests for access control and rate limiting."""

    def test_user_registration(self):
        """Test user registration."""
        from governance.access_control import AccessController, UserRole, TierType

        controller = AccessController()

        profile = controller.register_user(
            user_id="0x123",
            role=UserRole.SENTINEL,
            tier=TierType.SENTINEL_CORE,
        )

        assert profile.user_id == "0x123"
        assert profile.role == UserRole.SENTINEL
        assert profile.tier == TierType.SENTINEL_CORE

    def test_permission_check(self):
        """Test permission checking."""
        from governance.access_control import (
            AccessController,
            UserRole,
            PERMISSION_ENCRYPT,
            PERMISSION_USER_MANAGE,
        )

        controller = AccessController()
        controller.register_user("user1", role=UserRole.USER)
        controller.register_user("admin1", role=UserRole.ADMIN)

        # User should have encrypt permission
        result = controller.check_permission("user1", PERMISSION_ENCRYPT)
        assert result.allowed is True

        # User should not have admin permission
        result = controller.check_permission("user1", PERMISSION_USER_MANAGE)
        assert result.allowed is False

        # Admin should have admin permission
        result = controller.check_permission("admin1", PERMISSION_USER_MANAGE)
        assert result.allowed is True

    def test_has_permission_helper(self):
        """Test has_permission helper method."""
        from governance.access_control import (
            AccessController,
            UserRole,
            PERMISSION_DECRYPT,
        )

        controller = AccessController()
        controller.register_user("test_user", role=UserRole.USER)

        assert controller.has_permission("test_user", PERMISSION_DECRYPT) is True
        assert controller.has_permission("nonexistent", PERMISSION_DECRYPT) is False

    def test_rate_limiting(self):
        """Test rate limiting."""
        from governance.access_control import AccessController, UserRole, TierType

        controller = AccessController()
        controller.register_user(
            "rate_test_user",
            role=UserRole.USER,
            tier=TierType.LEGACY_BUILDER,  # 5 req/min
        )

        # First 5 requests should be allowed
        for i in range(5):
            result = controller.check_rate_limit("rate_test_user")
            assert result.allowed is True

        # 6th request should be denied
        result = controller.check_rate_limit("rate_test_user")
        assert result.allowed is False
        assert result.reset_in_seconds > 0

    def test_rate_limit_by_endpoint(self):
        """Test per-endpoint rate limiting."""
        from governance.access_control import AccessController, UserRole

        controller = AccessController()
        controller.register_user("endpoint_user", role=UserRole.USER)

        # Different endpoints have separate limits
        for i in range(5):
            result = controller.check_rate_limit("endpoint_user", "/api/encrypt")
            assert result.allowed is True

        for i in range(5):
            result = controller.check_rate_limit("endpoint_user", "/api/decrypt")
            assert result.allowed is True

        # Encrypt endpoint should be rate limited
        result = controller.check_rate_limit("endpoint_user", "/api/encrypt")
        assert result.allowed is False

        # Decrypt endpoint should be rate limited
        result = controller.check_rate_limit("endpoint_user", "/api/decrypt")
        assert result.allowed is False

    def test_role_update(self):
        """Test role update."""
        from governance.access_control import AccessController, UserRole

        controller = AccessController()
        controller.register_user("upgrade_user", role=UserRole.USER)

        success = controller.update_role("upgrade_user", UserRole.SENTINEL)
        assert success is True

        user = controller.get_user("upgrade_user")
        assert user.role == UserRole.SENTINEL

    def test_tier_update(self):
        """Test tier update."""
        from governance.access_control import AccessController, TierType

        controller = AccessController()
        controller.register_user("tier_user")

        success = controller.update_tier("tier_user", TierType.AUTONOMOUS_GUILD)
        assert success is True

        user = controller.get_user("tier_user")
        assert user.tier == TierType.AUTONOMOUS_GUILD

    def test_user_removal(self):
        """Test user removal."""
        from governance.access_control import AccessController

        controller = AccessController()
        controller.register_user("remove_user")

        assert controller.get_user("remove_user") is not None

        success = controller.remove_user("remove_user")
        assert success is True
        assert controller.get_user("remove_user") is None

    def test_get_all_users(self):
        """Test getting all users."""
        from governance.access_control import AccessController, UserRole

        controller = AccessController()
        controller.register_user("user1", role=UserRole.USER)
        controller.register_user("user2", role=UserRole.USER)
        controller.register_user("admin1", role=UserRole.ADMIN)

        all_users = controller.get_all_users()
        assert len(all_users) == 3

        admins = controller.get_all_users(role=UserRole.ADMIN)
        assert len(admins) == 1


class TestTierManager:
    """Tests for tier management."""

    def test_tier_features(self):
        """Test getting tier features."""
        from governance.access_control import TierManager
        from config.constants import TierType

        sentinel_features = TierManager.get_tier_features(TierType.SENTINEL_CORE)
        assert sentinel_features["pqc_enabled"] is True
        assert sentinel_features["price_usd"] == 16.99

        legacy_features = TierManager.get_tier_features(TierType.LEGACY_BUILDER)
        assert legacy_features["pqc_enabled"] is False
        assert legacy_features["price_usd"] == 10.99

        guild_features = TierManager.get_tier_features(TierType.AUTONOMOUS_GUILD)
        assert guild_features["smart_contract_enabled"] is True
        assert guild_features["operations_per_month"] == -1  # Unlimited

    def test_can_use_pqc(self):
        """Test PQC availability check."""
        from governance.access_control import TierManager
        from config.constants import TierType

        assert TierManager.can_use_pqc(TierType.SENTINEL_CORE) is True
        assert TierManager.can_use_pqc(TierType.LEGACY_BUILDER) is False
        assert TierManager.can_use_pqc(TierType.AUTONOMOUS_GUILD) is True

    def test_can_use_smart_contracts(self):
        """Test smart contract availability check."""
        from governance.access_control import TierManager
        from config.constants import TierType

        assert TierManager.can_use_smart_contracts(TierType.SENTINEL_CORE) is False
        assert TierManager.can_use_smart_contracts(TierType.LEGACY_BUILDER) is False
        assert TierManager.can_use_smart_contracts(TierType.AUTONOMOUS_GUILD) is True


class TestGryphonFallback:
    """Tests for Gryphon network fallback."""

    def test_fallback_queue(self):
        """Test fallback request queuing."""
        from governance.rules_engine import GryphonFallback

        fallback = GryphonFallback()

        request_id = fallback.queue_fallback(
            user_id="user123",
            operation="transfer",
            data={"amount": 100},
        )

        assert request_id.startswith("gryphon_")
        queue = fallback.get_queue_status()
        assert len(queue) == 1
        assert queue[0]["status"] == "queued"

    def test_fallback_processing(self):
        """Test fallback request processing."""
        from governance.rules_engine import GryphonFallback

        fallback = GryphonFallback()

        request_id = fallback.queue_fallback(
            user_id="user123",
            operation="transfer",
            data={},
        )

        success = fallback.process_fallback(request_id)
        assert success is True

        queue = fallback.get_queue_status()
        assert queue[0]["status"] == "processed"

    def test_fallback_not_found(self):
        """Test processing nonexistent fallback."""
        from governance.rules_engine import GryphonFallback

        fallback = GryphonFallback()

        success = fallback.process_fallback("nonexistent_id")
        assert success is False
