"""Self-Governance Rules Engine for PULSAR SENTINEL.

Implements the core governance rules (RC codes) for the security framework:

RC 1.01: All public requests require encryption signature
RC 1.02: Unresponsive state triggers 90-day transfer to designated heir
RC 2.01: Minimum 3-strike rule enforcement
RC 3.02: Automated AI protocol execution on transaction failure

These rules are hardcoded and cannot be bypassed.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable

from config.constants import (
    RuleCode,
    ThreatLevel,
    DEFAULT_STRIKE_THRESHOLD,
    DEFAULT_HEIR_TRANSFER_DAYS,
)
from config.settings import get_settings
from config.logging import SecurityEventLogger

logger = SecurityEventLogger("governance")


class ViolationType(str, Enum):
    """Types of rule violations."""
    MISSING_SIGNATURE = "missing_signature"
    INVALID_SIGNATURE = "invalid_signature"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    POLICY_VIOLATION = "policy_violation"
    TRANSACTION_FAILURE = "transaction_failure"
    UNRESPONSIVE_STATE = "unresponsive_state"


@dataclass
class RuleViolation:
    """Record of a rule violation.

    Attributes:
        rule_code: The violated rule
        violation_type: Type of violation
        user_id: The user who violated the rule
        description: Human-readable description
        timestamp: When the violation occurred
        metadata: Additional violation data
    """
    rule_code: RuleCode
    violation_type: ViolationType
    user_id: str
    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_code": self.rule_code.value,
            "violation_type": self.violation_type.value,
            "user_id": self.user_id,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RuleResult:
    """Result of a rule check.

    Attributes:
        passed: Whether the rule check passed
        rule_code: The rule that was checked
        violation: Violation details if failed
        action_required: Action to take if failed
    """
    passed: bool
    rule_code: RuleCode
    violation: RuleViolation | None = None
    action_required: str | None = None


@dataclass
class UserState:
    """Current state of a user for rule evaluation.

    Attributes:
        user_id: User identifier (wallet address)
        strikes: Current strike count
        last_activity: Last activity timestamp
        heir_address: Designated heir address
        is_banned: Whether user is currently banned
        ban_expires: When current ban expires
        request_count_minute: Requests in current minute
    """
    user_id: str
    strikes: int = 0
    last_activity: datetime | None = None
    heir_address: str | None = None
    is_banned: bool = False
    ban_expires: datetime | None = None
    request_count_minute: int = 0


class RulesEngine:
    """Engine for enforcing self-governance rules.

    Evaluates requests against hardcoded rules and tracks violations.
    Rules cannot be bypassed or disabled.

    Example:
        >>> engine = RulesEngine()
        >>> result = engine.check_signature_required(request, user_state)
        >>> if not result.passed:
        ...     engine.record_violation(result.violation)
    """

    def __init__(self) -> None:
        """Initialize rules engine."""
        settings = get_settings()

        self._strike_threshold = settings.strike_threshold
        self._heir_transfer_days = settings.heir_transfer_days
        self._ban_duration_hours = settings.strike_ban_duration_hours

        # Violation history per user
        self._violations: dict[str, list[RuleViolation]] = {}

        # Strike counts per user
        self._strikes: dict[str, int] = {}

        # Ban status per user
        self._bans: dict[str, datetime] = {}

    # RC 1.01: Encryption Signature Required

    def check_signature_required(
        self,
        has_signature: bool,
        signature_valid: bool,
        user_id: str,
    ) -> RuleResult:
        """Check RC 1.01: All public requests require encryption signature.

        Args:
            has_signature: Whether request has a signature
            signature_valid: Whether signature is valid
            user_id: User making the request

        Returns:
            RuleResult indicating pass/fail
        """
        if not has_signature:
            violation = RuleViolation(
                rule_code=RuleCode.RC_1_01,
                violation_type=ViolationType.MISSING_SIGNATURE,
                user_id=user_id,
                description="Request missing required encryption signature",
            )
            return RuleResult(
                passed=False,
                rule_code=RuleCode.RC_1_01,
                violation=violation,
                action_required="reject_request",
            )

        if not signature_valid:
            violation = RuleViolation(
                rule_code=RuleCode.RC_1_01,
                violation_type=ViolationType.INVALID_SIGNATURE,
                user_id=user_id,
                description="Request has invalid encryption signature",
            )
            return RuleResult(
                passed=False,
                rule_code=RuleCode.RC_1_01,
                violation=violation,
                action_required="reject_request",
            )

        return RuleResult(passed=True, rule_code=RuleCode.RC_1_01)

    # RC 1.02: Heir Transfer on Unresponsive

    def check_heir_transfer(
        self,
        user_state: UserState,
    ) -> RuleResult:
        """Check RC 1.02: Unresponsive state triggers heir transfer.

        Args:
            user_state: Current user state

        Returns:
            RuleResult with heir transfer action if triggered
        """
        if user_state.last_activity is None:
            return RuleResult(passed=True, rule_code=RuleCode.RC_1_02)

        days_inactive = (
            datetime.now(timezone.utc) - user_state.last_activity
        ).days

        if days_inactive >= self._heir_transfer_days:
            if user_state.heir_address:
                violation = RuleViolation(
                    rule_code=RuleCode.RC_1_02,
                    violation_type=ViolationType.UNRESPONSIVE_STATE,
                    user_id=user_state.user_id,
                    description=f"User inactive for {days_inactive} days, "
                                f"initiating heir transfer to {user_state.heir_address}",
                    metadata={
                        "days_inactive": days_inactive,
                        "heir_address": user_state.heir_address,
                    },
                )
                return RuleResult(
                    passed=False,
                    rule_code=RuleCode.RC_1_02,
                    violation=violation,
                    action_required="initiate_heir_transfer",
                )

        return RuleResult(passed=True, rule_code=RuleCode.RC_1_02)

    # RC 2.01: Three-Strike Rule

    def check_strike_policy(
        self,
        user_id: str,
    ) -> RuleResult:
        """Check RC 2.01: Three-strike rule enforcement.

        Args:
            user_id: User to check

        Returns:
            RuleResult indicating ban status
        """
        # Check if currently banned
        if user_id in self._bans:
            ban_expires = self._bans[user_id]
            if datetime.now(timezone.utc) < ban_expires:
                remaining = (ban_expires - datetime.now(timezone.utc)).total_seconds()
                return RuleResult(
                    passed=False,
                    rule_code=RuleCode.RC_2_01,
                    violation=RuleViolation(
                        rule_code=RuleCode.RC_2_01,
                        violation_type=ViolationType.POLICY_VIOLATION,
                        user_id=user_id,
                        description=f"User is banned. Ban expires in {remaining:.0f} seconds",
                        metadata={"ban_expires": ban_expires.isoformat()},
                    ),
                    action_required="reject_banned_user",
                )
            else:
                # Ban expired, remove it
                del self._bans[user_id]

        # Check strike count
        strikes = self._strikes.get(user_id, 0)
        if strikes >= self._strike_threshold:
            # Issue ban
            ban_expires = datetime.now(timezone.utc) + timedelta(
                hours=self._ban_duration_hours
            )
            self._bans[user_id] = ban_expires

            return RuleResult(
                passed=False,
                rule_code=RuleCode.RC_2_01,
                violation=RuleViolation(
                    rule_code=RuleCode.RC_2_01,
                    violation_type=ViolationType.POLICY_VIOLATION,
                    user_id=user_id,
                    description=f"User has {strikes} strikes, temporary ban issued",
                    metadata={
                        "strikes": strikes,
                        "threshold": self._strike_threshold,
                        "ban_duration_hours": self._ban_duration_hours,
                    },
                ),
                action_required="issue_ban",
            )

        return RuleResult(passed=True, rule_code=RuleCode.RC_2_01)

    def issue_strike(self, user_id: str, reason: str) -> int:
        """Issue a strike to a user.

        Args:
            user_id: User to strike
            reason: Reason for the strike

        Returns:
            New strike count
        """
        self._strikes[user_id] = self._strikes.get(user_id, 0) + 1
        strikes = self._strikes[user_id]

        logger.log_event(
            event=f"strike_issued:{reason}",
            threat_level=ThreatLevel.WARNING,
            agent_id=user_id,
            metadata={"strikes": strikes, "threshold": self._strike_threshold},
        )

        return strikes

    def reset_strikes(self, user_id: str) -> None:
        """Reset strikes for a user (admin action).

        Args:
            user_id: User to reset
        """
        if user_id in self._strikes:
            del self._strikes[user_id]
        if user_id in self._bans:
            del self._bans[user_id]

    def get_strikes(self, user_id: str) -> int:
        """Get current strike count for a user.

        Args:
            user_id: User to check

        Returns:
            Current strike count
        """
        return self._strikes.get(user_id, 0)

    # RC 3.02: Fallback on Transaction Failure

    def check_transaction_fallback(
        self,
        tx_success: bool,
        user_id: str,
        tx_type: str,
    ) -> RuleResult:
        """Check RC 3.02: Automated fallback on transaction failure.

        Args:
            tx_success: Whether transaction succeeded
            user_id: User making the transaction
            tx_type: Type of transaction

        Returns:
            RuleResult with fallback action if needed
        """
        if tx_success:
            return RuleResult(passed=True, rule_code=RuleCode.RC_3_02)

        violation = RuleViolation(
            rule_code=RuleCode.RC_3_02,
            violation_type=ViolationType.TRANSACTION_FAILURE,
            user_id=user_id,
            description=f"Transaction {tx_type} failed, initiating Gryphon fallback",
            metadata={"tx_type": tx_type},
        )

        return RuleResult(
            passed=False,
            rule_code=RuleCode.RC_3_02,
            violation=violation,
            action_required="initiate_gryphon_fallback",
        )

    # Violation Management

    def record_violation(self, violation: RuleViolation) -> None:
        """Record a rule violation.

        Args:
            violation: The violation to record
        """
        user_id = violation.user_id

        if user_id not in self._violations:
            self._violations[user_id] = []

        self._violations[user_id].append(violation)

        # Determine threat level based on violation type
        threat_level = ThreatLevel.WARNING
        if violation.violation_type in (
            ViolationType.UNAUTHORIZED_ACCESS,
            ViolationType.INVALID_SIGNATURE,
        ):
            threat_level = ThreatLevel.ALERT

        logger.log_event(
            event=f"rule_violation:{violation.rule_code.value}",
            threat_level=threat_level,
            agent_id=user_id,
            metadata=violation.to_dict(),
        )

    def get_violations(
        self,
        user_id: str,
        rule_code: RuleCode | None = None,
    ) -> list[RuleViolation]:
        """Get violations for a user.

        Args:
            user_id: User to get violations for
            rule_code: Optional filter by rule code

        Returns:
            List of violations
        """
        violations = self._violations.get(user_id, [])

        if rule_code:
            violations = [v for v in violations if v.rule_code == rule_code]

        return violations

    def evaluate_all_rules(
        self,
        user_state: UserState,
        has_signature: bool = True,
        signature_valid: bool = True,
        tx_success: bool = True,
        tx_type: str = "",
    ) -> list[RuleResult]:
        """Evaluate all rules for a request.

        Args:
            user_state: Current user state
            has_signature: Whether request has signature
            signature_valid: Whether signature is valid
            tx_success: Whether related transaction succeeded
            tx_type: Type of transaction

        Returns:
            List of all rule results
        """
        results = []

        # RC 1.01: Signature required
        results.append(self.check_signature_required(
            has_signature, signature_valid, user_state.user_id
        ))

        # RC 1.02: Heir transfer check
        results.append(self.check_heir_transfer(user_state))

        # RC 2.01: Strike policy
        results.append(self.check_strike_policy(user_state.user_id))

        # RC 3.02: Transaction fallback
        if tx_type:
            results.append(self.check_transaction_fallback(
                tx_success, user_state.user_id, tx_type
            ))

        # Record any violations
        for result in results:
            if not result.passed and result.violation:
                self.record_violation(result.violation)

        return results


class GryphonFallback:
    """Fallback handler for Gryphon network (RC 3.02).

    Provides automated protocol execution when primary
    transaction processing fails.
    """

    def __init__(self) -> None:
        """Initialize Gryphon fallback handler."""
        self._fallback_queue: list[dict[str, Any]] = []

    def queue_fallback(
        self,
        user_id: str,
        operation: str,
        data: dict[str, Any],
    ) -> str:
        """Queue an operation for Gryphon fallback.

        Args:
            user_id: User requesting fallback
            operation: Operation type
            data: Operation data

        Returns:
            Fallback request ID
        """
        import secrets

        request_id = f"gryphon_{secrets.token_hex(16)}"

        self._fallback_queue.append({
            "request_id": request_id,
            "user_id": user_id,
            "operation": operation,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "queued",
        })

        logger.log_event(
            event="gryphon_fallback_queued",
            threat_level=ThreatLevel.CAUTION,
            agent_id=user_id,
            metadata={"request_id": request_id, "operation": operation},
        )

        return request_id

    def process_fallback(self, request_id: str) -> bool:
        """Process a queued fallback request.

        Args:
            request_id: The request to process

        Returns:
            True if processed successfully
        """
        for request in self._fallback_queue:
            if request["request_id"] == request_id:
                # Simulate Gryphon network processing
                request["status"] = "processed"
                request["processed_at"] = datetime.now(timezone.utc).isoformat()

                logger.log_event(
                    event="gryphon_fallback_processed",
                    threat_level=ThreatLevel.INFO,
                    agent_id=request["user_id"],
                    metadata={"request_id": request_id},
                )

                return True

        return False

    def get_queue_status(self) -> list[dict[str, Any]]:
        """Get current fallback queue status.

        Returns:
            List of queued requests
        """
        return self._fallback_queue.copy()
