"""Points Toward Threat Score (PTS) Calculator for PULSAR SENTINEL.

Calculates real-time threat scores based on security metrics:

PTS = (quantum_risk_factor * 0.4) +
      (access_violation_count * 0.3) +
      (rate_limit_violations * 0.2) +
      (signature_failures * 0.1)

Tiers:
- Tier 1 (Safe/Green): PTS < 50
- Tier 2 (Caution/Yellow): 50 <= PTS < 150
- Tier 3 (Critical/Red): PTS >= 150
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Final

from config.constants import (
    PTSThreshold,
    PTSTier,
    PTS_WEIGHTS,
    ThreatLevel,
)
from config.settings import get_settings
from config.logging import SecurityEventLogger

logger = SecurityEventLogger("pts")

# PTS Weights
WEIGHT_QUANTUM_RISK: Final[float] = PTS_WEIGHTS["quantum_risk_factor"]
WEIGHT_ACCESS_VIOLATION: Final[float] = PTS_WEIGHTS["access_violation_count"]
WEIGHT_RATE_LIMIT: Final[float] = PTS_WEIGHTS["rate_limit_violations"]
WEIGHT_SIGNATURE_FAILURE: Final[float] = PTS_WEIGHTS["signature_failures"]

# Risk multipliers
QUANTUM_RISK_MULTIPLIER: Final[float] = 50.0  # Per quantum-adjacent cipher
ACCESS_VIOLATION_MULTIPLIER: Final[float] = 25.0  # Per violation
RATE_LIMIT_MULTIPLIER: Final[float] = 10.0  # Per rate limit hit
SIGNATURE_FAILURE_MULTIPLIER: Final[float] = 30.0  # Per signature failure


@dataclass
class PTSFactors:
    """Factors contributing to PTS calculation.

    Attributes:
        quantum_risk_count: Number of quantum-risky operations
        access_violation_count: Number of access violations
        rate_limit_violations: Number of rate limit hits
        signature_failures: Number of signature verification failures
        time_window_hours: Time window for calculation
    """
    quantum_risk_count: int = 0
    access_violation_count: int = 0
    rate_limit_violations: int = 0
    signature_failures: int = 0
    time_window_hours: int = 24

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "quantum_risk_count": self.quantum_risk_count,
            "access_violation_count": self.access_violation_count,
            "rate_limit_violations": self.rate_limit_violations,
            "signature_failures": self.signature_failures,
            "time_window_hours": self.time_window_hours,
        }


@dataclass
class PTSScore:
    """Calculated PTS score with breakdown.

    Attributes:
        total_score: Total PTS value
        tier: Current tier classification
        factors: Contributing factors
        breakdown: Score breakdown by factor
        calculated_at: Calculation timestamp
        user_id: User this score belongs to
    """
    total_score: float
    tier: PTSTier
    factors: PTSFactors
    breakdown: dict[str, float]
    calculated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    user_id: str = ""

    @property
    def is_safe(self) -> bool:
        """Check if score is in safe tier."""
        return self.tier == PTSTier.SAFE

    @property
    def is_caution(self) -> bool:
        """Check if score is in caution tier."""
        return self.tier == PTSTier.CAUTION

    @property
    def is_critical(self) -> bool:
        """Check if score is in critical tier."""
        return self.tier == PTSTier.CRITICAL

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_score": round(self.total_score, 2),
            "tier": self.tier.value,
            "factors": self.factors.to_dict(),
            "breakdown": {k: round(v, 2) for k, v in self.breakdown.items()},
            "calculated_at": self.calculated_at.isoformat(),
            "user_id": self.user_id,
        }


@dataclass
class SecurityEvent:
    """Security event for PTS tracking.

    Attributes:
        event_type: Type of security event
        user_id: User associated with event
        timestamp: When event occurred
        metadata: Additional event data
    """
    event_type: str
    user_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


class PTSCalculator:
    """Calculator for Points Toward Threat Score.

    Tracks security events and calculates real-time threat scores
    for users based on their security-relevant activities.

    Example:
        >>> calc = PTSCalculator()
        >>> calc.record_quantum_risk("user123", "weak_cipher_detected")
        >>> calc.record_access_violation("user123", "unauthorized_endpoint")
        >>> score = calc.calculate_pts("user123")
        >>> print(f"Score: {score.total_score}, Tier: {score.tier}")
    """

    def __init__(self, time_window_hours: int = 24) -> None:
        """Initialize PTS calculator.

        Args:
            time_window_hours: Time window for event consideration
        """
        settings = get_settings()

        self._time_window = timedelta(hours=time_window_hours)
        self._tier1_max = settings.pts_tier1_max
        self._tier2_max = settings.pts_tier2_max

        # Event storage per user
        self._events: dict[str, list[SecurityEvent]] = {}

    def _cleanup_old_events(self, user_id: str) -> None:
        """Remove events outside the time window.

        Args:
            user_id: User to cleanup events for
        """
        if user_id not in self._events:
            return

        cutoff = datetime.now(timezone.utc) - self._time_window
        self._events[user_id] = [
            e for e in self._events[user_id]
            if e.timestamp >= cutoff
        ]

    def _add_event(self, event: SecurityEvent) -> None:
        """Add a security event.

        Args:
            event: Event to add
        """
        if event.user_id not in self._events:
            self._events[event.user_id] = []

        self._events[event.user_id].append(event)
        self._cleanup_old_events(event.user_id)

    def record_quantum_risk(
        self,
        user_id: str,
        risk_type: str,
        metadata: dict | None = None,
    ) -> None:
        """Record a quantum risk event.

        Args:
            user_id: User associated with the risk
            risk_type: Type of quantum risk detected
            metadata: Additional risk data
        """
        event = SecurityEvent(
            event_type="quantum_risk",
            user_id=user_id,
            metadata={"risk_type": risk_type, **(metadata or {})},
        )
        self._add_event(event)

        logger.log_event(
            event=f"quantum_risk:{risk_type}",
            threat_level=ThreatLevel.WARNING,
            agent_id=user_id,
        )

    def record_access_violation(
        self,
        user_id: str,
        violation_type: str,
        metadata: dict | None = None,
    ) -> None:
        """Record an access violation event.

        Args:
            user_id: User who violated access rules
            violation_type: Type of violation
            metadata: Additional violation data
        """
        event = SecurityEvent(
            event_type="access_violation",
            user_id=user_id,
            metadata={"violation_type": violation_type, **(metadata or {})},
        )
        self._add_event(event)

        logger.log_event(
            event=f"access_violation:{violation_type}",
            threat_level=ThreatLevel.ALERT,
            agent_id=user_id,
        )

    def record_rate_limit_violation(
        self,
        user_id: str,
        endpoint: str,
        count: int,
        limit: int,
    ) -> None:
        """Record a rate limit violation.

        Args:
            user_id: User who exceeded rate limit
            endpoint: API endpoint that was rate limited
            count: Request count
            limit: Rate limit threshold
        """
        event = SecurityEvent(
            event_type="rate_limit_violation",
            user_id=user_id,
            metadata={"endpoint": endpoint, "count": count, "limit": limit},
        )
        self._add_event(event)

        logger.log_event(
            event="rate_limit_violation",
            threat_level=ThreatLevel.CAUTION,
            agent_id=user_id,
            metadata={"endpoint": endpoint},
        )

    def record_signature_failure(
        self,
        user_id: str,
        failure_type: str,
        metadata: dict | None = None,
    ) -> None:
        """Record a signature verification failure.

        Args:
            user_id: User with signature failure
            failure_type: Type of signature failure
            metadata: Additional failure data
        """
        event = SecurityEvent(
            event_type="signature_failure",
            user_id=user_id,
            metadata={"failure_type": failure_type, **(metadata or {})},
        )
        self._add_event(event)

        logger.log_event(
            event=f"signature_failure:{failure_type}",
            threat_level=ThreatLevel.ALERT,
            agent_id=user_id,
        )

    def get_factors(self, user_id: str) -> PTSFactors:
        """Get PTS factors for a user.

        Args:
            user_id: User to get factors for

        Returns:
            PTSFactors with event counts
        """
        self._cleanup_old_events(user_id)

        events = self._events.get(user_id, [])

        quantum_risk = sum(1 for e in events if e.event_type == "quantum_risk")
        access_violations = sum(1 for e in events if e.event_type == "access_violation")
        rate_limits = sum(1 for e in events if e.event_type == "rate_limit_violation")
        sig_failures = sum(1 for e in events if e.event_type == "signature_failure")

        return PTSFactors(
            quantum_risk_count=quantum_risk,
            access_violation_count=access_violations,
            rate_limit_violations=rate_limits,
            signature_failures=sig_failures,
            time_window_hours=int(self._time_window.total_seconds() / 3600),
        )

    def calculate_pts(self, user_id: str) -> PTSScore:
        """Calculate PTS score for a user.

        Args:
            user_id: User to calculate score for

        Returns:
            PTSScore with total and breakdown
        """
        factors = self.get_factors(user_id)

        # Calculate component scores
        quantum_score = (
            factors.quantum_risk_count *
            QUANTUM_RISK_MULTIPLIER *
            WEIGHT_QUANTUM_RISK
        )

        access_score = (
            factors.access_violation_count *
            ACCESS_VIOLATION_MULTIPLIER *
            WEIGHT_ACCESS_VIOLATION
        )

        rate_score = (
            factors.rate_limit_violations *
            RATE_LIMIT_MULTIPLIER *
            WEIGHT_RATE_LIMIT
        )

        sig_score = (
            factors.signature_failures *
            SIGNATURE_FAILURE_MULTIPLIER *
            WEIGHT_SIGNATURE_FAILURE
        )

        # Calculate total
        total = quantum_score + access_score + rate_score + sig_score

        # Determine tier
        if total < self._tier1_max:
            tier = PTSTier.SAFE
        elif total < self._tier2_max:
            tier = PTSTier.CAUTION
        else:
            tier = PTSTier.CRITICAL

        breakdown = {
            "quantum_risk": quantum_score,
            "access_violation": access_score,
            "rate_limit": rate_score,
            "signature_failure": sig_score,
        }

        score = PTSScore(
            total_score=total,
            tier=tier,
            factors=factors,
            breakdown=breakdown,
            user_id=user_id,
        )

        # Log if crossing tier thresholds
        if tier == PTSTier.CAUTION:
            logger.log_event(
                event="pts_caution_tier",
                threat_level=ThreatLevel.CAUTION,
                agent_id=user_id,
                metadata={"pts": total},
            )
        elif tier == PTSTier.CRITICAL:
            logger.log_event(
                event="pts_critical_tier",
                threat_level=ThreatLevel.ALERT,
                agent_id=user_id,
                metadata={"pts": total},
            )

        return score

    def get_tier(self, user_id: str) -> PTSTier:
        """Get current tier for a user.

        Args:
            user_id: User to get tier for

        Returns:
            Current PTSTier
        """
        return self.calculate_pts(user_id).tier

    def is_critical(self, user_id: str) -> bool:
        """Check if user is in critical tier.

        Args:
            user_id: User to check

        Returns:
            True if user is in critical tier
        """
        return self.get_tier(user_id) == PTSTier.CRITICAL

    def reset_user(self, user_id: str) -> None:
        """Reset all events for a user (admin action).

        Args:
            user_id: User to reset
        """
        if user_id in self._events:
            del self._events[user_id]

    def get_all_critical_users(self) -> list[str]:
        """Get all users in critical tier.

        Returns:
            List of user IDs in critical tier
        """
        critical_users = []

        for user_id in self._events.keys():
            if self.is_critical(user_id):
                critical_users.append(user_id)

        return critical_users


class PTSMonitor:
    """Real-time PTS monitoring service.

    Provides continuous monitoring of PTS scores and
    alerts when users cross tier thresholds.
    """

    def __init__(
        self,
        calculator: PTSCalculator | None = None,
        alert_callback: callable | None = None,
    ) -> None:
        """Initialize PTS monitor.

        Args:
            calculator: PTSCalculator instance
            alert_callback: Callback for alerts
        """
        self._calculator = calculator or PTSCalculator()
        self._alert_callback = alert_callback
        self._last_tiers: dict[str, PTSTier] = {}

    def check_user(self, user_id: str) -> PTSScore:
        """Check a user's PTS and alert on tier change.

        Args:
            user_id: User to check

        Returns:
            Current PTSScore
        """
        score = self._calculator.calculate_pts(user_id)

        # Check for tier change
        last_tier = self._last_tiers.get(user_id)
        if last_tier and last_tier != score.tier:
            self._on_tier_change(user_id, last_tier, score.tier, score)

        self._last_tiers[user_id] = score.tier
        return score

    def _on_tier_change(
        self,
        user_id: str,
        old_tier: PTSTier,
        new_tier: PTSTier,
        score: PTSScore,
    ) -> None:
        """Handle tier change event.

        Args:
            user_id: User who changed tiers
            old_tier: Previous tier
            new_tier: New tier
            score: Current score
        """
        # Determine if escalation or de-escalation
        tier_order = [PTSTier.SAFE, PTSTier.CAUTION, PTSTier.CRITICAL]
        is_escalation = tier_order.index(new_tier) > tier_order.index(old_tier)

        threat_level = ThreatLevel.WARNING if is_escalation else ThreatLevel.INFO

        logger.log_event(
            event="pts_tier_change",
            threat_level=threat_level,
            agent_id=user_id,
            metadata={
                "old_tier": old_tier.value,
                "new_tier": new_tier.value,
                "pts": score.total_score,
                "escalation": is_escalation,
            },
        )

        if self._alert_callback:
            self._alert_callback(user_id, old_tier, new_tier, score)
