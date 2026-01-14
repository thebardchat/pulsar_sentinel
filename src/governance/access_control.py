"""Access Control Module for PULSAR SENTINEL.

Provides role-based access control (RBAC) and rate limiting
for API endpoints and operations.

Roles:
- Admin: Full access, can manage other users
- Sentinel: Enhanced access, PQC operations
- User: Basic access, limited operations

Rate Limits (per minute):
- Default: 5
- Sentinel: 10
- Guild: 100
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Callable, Final

from config.constants import TierType, RATE_LIMITS, ThreatLevel
from config.settings import get_settings
from config.logging import SecurityEventLogger

logger = SecurityEventLogger("access_control")

# Permission definitions
PERMISSION_ENCRYPT: Final[str] = "encrypt"
PERMISSION_DECRYPT: Final[str] = "decrypt"
PERMISSION_KEY_GENERATE: Final[str] = "key_generate"
PERMISSION_KEY_ROTATE: Final[str] = "key_rotate"
PERMISSION_ASR_READ: Final[str] = "asr_read"
PERMISSION_ASR_WRITE: Final[str] = "asr_write"
PERMISSION_USER_MANAGE: Final[str] = "user_manage"
PERMISSION_ADMIN: Final[str] = "admin"
PERMISSION_BLOCKCHAIN_WRITE: Final[str] = "blockchain_write"
PERMISSION_GOVERNANCE: Final[str] = "governance"


class UserRole(IntEnum):
    """User role levels (must match smart contract)."""
    NONE = 0
    USER = 1
    SENTINEL = 2
    ADMIN = 3


@dataclass
class Permission:
    """Permission definition.

    Attributes:
        name: Permission name
        description: Human-readable description
        min_role: Minimum role required
    """
    name: str
    description: str
    min_role: UserRole


# Permission registry
PERMISSIONS: dict[str, Permission] = {
    PERMISSION_ENCRYPT: Permission(
        name=PERMISSION_ENCRYPT,
        description="Encrypt data using PQC or legacy crypto",
        min_role=UserRole.USER,
    ),
    PERMISSION_DECRYPT: Permission(
        name=PERMISSION_DECRYPT,
        description="Decrypt data using PQC or legacy crypto",
        min_role=UserRole.USER,
    ),
    PERMISSION_KEY_GENERATE: Permission(
        name=PERMISSION_KEY_GENERATE,
        description="Generate new cryptographic keys",
        min_role=UserRole.USER,
    ),
    PERMISSION_KEY_ROTATE: Permission(
        name=PERMISSION_KEY_ROTATE,
        description="Rotate existing keys",
        min_role=UserRole.SENTINEL,
    ),
    PERMISSION_ASR_READ: Permission(
        name=PERMISSION_ASR_READ,
        description="Read ASR records",
        min_role=UserRole.USER,
    ),
    PERMISSION_ASR_WRITE: Permission(
        name=PERMISSION_ASR_WRITE,
        description="Write ASR records",
        min_role=UserRole.SENTINEL,
    ),
    PERMISSION_USER_MANAGE: Permission(
        name=PERMISSION_USER_MANAGE,
        description="Manage user roles and permissions",
        min_role=UserRole.ADMIN,
    ),
    PERMISSION_ADMIN: Permission(
        name=PERMISSION_ADMIN,
        description="Full administrative access",
        min_role=UserRole.ADMIN,
    ),
    PERMISSION_BLOCKCHAIN_WRITE: Permission(
        name=PERMISSION_BLOCKCHAIN_WRITE,
        description="Write to blockchain",
        min_role=UserRole.SENTINEL,
    ),
    PERMISSION_GOVERNANCE: Permission(
        name=PERMISSION_GOVERNANCE,
        description="Access governance features",
        min_role=UserRole.ADMIN,
    ),
}


@dataclass
class UserProfile:
    """User profile with role and tier information.

    Attributes:
        user_id: Unique user identifier (wallet address)
        role: User's role level
        tier: Subscription tier
        created_at: Account creation time
        last_active: Last activity timestamp
        rate_limit: Custom rate limit (0 = use default)
        metadata: Additional user data
    """
    user_id: str
    role: UserRole = UserRole.USER
    tier: TierType = TierType.LEGACY_BUILDER
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rate_limit: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_rate_limit(self) -> int:
        """Get effective rate limit for this user."""
        if self.rate_limit > 0:
            return self.rate_limit
        return RATE_LIMITS.get(self.tier, 5)


@dataclass
class AccessResult:
    """Result of an access check.

    Attributes:
        allowed: Whether access is allowed
        reason: Reason for denial if not allowed
        permission: The permission that was checked
        user_role: The user's role
    """
    allowed: bool
    reason: str | None = None
    permission: str | None = None
    user_role: UserRole | None = None


@dataclass
class RateLimitResult:
    """Result of a rate limit check.

    Attributes:
        allowed: Whether request is within rate limit
        current_count: Current request count in window
        limit: Rate limit threshold
        reset_in_seconds: Seconds until rate limit resets
    """
    allowed: bool
    current_count: int
    limit: int
    reset_in_seconds: float


class AccessController:
    """Controller for role-based access control and rate limiting.

    Manages user profiles, permission checks, and rate limiting
    for the PULSAR SENTINEL API.

    Example:
        >>> controller = AccessController()
        >>> controller.register_user("0x123...", UserRole.SENTINEL)
        >>> result = controller.check_permission("0x123...", "encrypt")
        >>> if result.allowed:
        ...     # Perform operation
    """

    def __init__(self) -> None:
        """Initialize access controller."""
        settings = get_settings()

        self._users: dict[str, UserProfile] = {}
        self._rate_limit_default = settings.rate_limit_default

        # Rate limiting state: user_id -> list of request timestamps
        self._request_times: dict[str, list[float]] = defaultdict(list)
        self._rate_limit_window = 60.0  # 1 minute window

    def register_user(
        self,
        user_id: str,
        role: UserRole = UserRole.USER,
        tier: TierType = TierType.LEGACY_BUILDER,
    ) -> UserProfile:
        """Register a new user.

        Args:
            user_id: User identifier (wallet address)
            role: Initial role
            tier: Subscription tier

        Returns:
            Created UserProfile
        """
        profile = UserProfile(
            user_id=user_id,
            role=role,
            tier=tier,
        )
        self._users[user_id] = profile

        logger.log_event(
            event="user_registered",
            threat_level=ThreatLevel.INFO,
            agent_id=user_id,
            metadata={"role": role.name, "tier": tier.value},
        )

        return profile

    def get_user(self, user_id: str) -> UserProfile | None:
        """Get user profile.

        Args:
            user_id: User identifier

        Returns:
            UserProfile if found, None otherwise
        """
        return self._users.get(user_id)

    def update_role(self, user_id: str, role: UserRole) -> bool:
        """Update a user's role.

        Args:
            user_id: User to update
            role: New role

        Returns:
            True if updated successfully
        """
        if user_id not in self._users:
            return False

        old_role = self._users[user_id].role
        self._users[user_id].role = role

        logger.log_event(
            event="role_updated",
            threat_level=ThreatLevel.INFO,
            agent_id=user_id,
            metadata={"old_role": old_role.name, "new_role": role.name},
        )

        return True

    def update_tier(self, user_id: str, tier: TierType) -> bool:
        """Update a user's subscription tier.

        Args:
            user_id: User to update
            tier: New tier

        Returns:
            True if updated successfully
        """
        if user_id not in self._users:
            return False

        old_tier = self._users[user_id].tier
        self._users[user_id].tier = tier

        logger.log_event(
            event="tier_updated",
            threat_level=ThreatLevel.INFO,
            agent_id=user_id,
            metadata={"old_tier": old_tier.value, "new_tier": tier.value},
        )

        return True

    def check_permission(
        self,
        user_id: str,
        permission: str,
    ) -> AccessResult:
        """Check if a user has a specific permission.

        Args:
            user_id: User to check
            permission: Permission name

        Returns:
            AccessResult with allowed status
        """
        # Get user profile
        user = self._users.get(user_id)
        if user is None:
            return AccessResult(
                allowed=False,
                reason="User not found",
                permission=permission,
            )

        # Get permission definition
        perm = PERMISSIONS.get(permission)
        if perm is None:
            return AccessResult(
                allowed=False,
                reason=f"Unknown permission: {permission}",
                permission=permission,
                user_role=user.role,
            )

        # Check role level
        if user.role >= perm.min_role:
            return AccessResult(
                allowed=True,
                permission=permission,
                user_role=user.role,
            )

        return AccessResult(
            allowed=False,
            reason=f"Insufficient role: requires {perm.min_role.name}, "
                   f"user has {user.role.name}",
            permission=permission,
            user_role=user.role,
        )

    def has_permission(self, user_id: str, permission: str) -> bool:
        """Quick check if user has permission.

        Args:
            user_id: User to check
            permission: Permission name

        Returns:
            True if user has permission
        """
        return self.check_permission(user_id, permission).allowed

    def check_rate_limit(
        self,
        user_id: str,
        endpoint: str | None = None,
    ) -> RateLimitResult:
        """Check if a request is within rate limits.

        Args:
            user_id: User making the request
            endpoint: Optional endpoint for per-endpoint limits

        Returns:
            RateLimitResult with limit status
        """
        now = time.time()
        window_start = now - self._rate_limit_window

        # Get user's rate limit
        user = self._users.get(user_id)
        if user:
            limit = user.get_rate_limit()
        else:
            limit = self._rate_limit_default

        # Clean old requests
        key = f"{user_id}:{endpoint}" if endpoint else user_id
        self._request_times[key] = [
            t for t in self._request_times[key]
            if t > window_start
        ]

        current_count = len(self._request_times[key])

        if current_count >= limit:
            # Find when oldest request will expire
            oldest = min(self._request_times[key]) if self._request_times[key] else now
            reset_in = oldest + self._rate_limit_window - now

            logger.log_rate_limit(
                user_id=user_id,
                endpoint=endpoint or "global",
                current_count=current_count,
                limit=limit,
            )

            return RateLimitResult(
                allowed=False,
                current_count=current_count,
                limit=limit,
                reset_in_seconds=max(0, reset_in),
            )

        # Record this request
        self._request_times[key].append(now)

        return RateLimitResult(
            allowed=True,
            current_count=current_count + 1,
            limit=limit,
            reset_in_seconds=self._rate_limit_window,
        )

    def record_activity(self, user_id: str) -> None:
        """Record user activity.

        Args:
            user_id: User who performed activity
        """
        if user_id in self._users:
            self._users[user_id].last_active = datetime.now(timezone.utc)

    def get_all_users(self, role: UserRole | None = None) -> list[UserProfile]:
        """Get all users, optionally filtered by role.

        Args:
            role: Optional role filter

        Returns:
            List of matching user profiles
        """
        users = list(self._users.values())

        if role is not None:
            users = [u for u in users if u.role == role]

        return users

    def remove_user(self, user_id: str) -> bool:
        """Remove a user.

        Args:
            user_id: User to remove

        Returns:
            True if removed successfully
        """
        if user_id not in self._users:
            return False

        del self._users[user_id]

        # Clean up rate limit data
        keys_to_remove = [k for k in self._request_times if k.startswith(user_id)]
        for key in keys_to_remove:
            del self._request_times[key]

        return True


def require_permission(permission: str) -> Callable:
    """Decorator to require a permission for a function.

    Args:
        permission: Required permission name

    Returns:
        Decorator function

    Example:
        >>> @require_permission("encrypt")
        ... def encrypt_data(controller, user_id, data):
        ...     # Only runs if user has encrypt permission
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(
            controller: AccessController,
            user_id: str,
            *args,
            **kwargs,
        ) -> Any:
            result = controller.check_permission(user_id, permission)
            if not result.allowed:
                raise PermissionError(
                    f"Access denied: {result.reason}"
                )
            return func(controller, user_id, *args, **kwargs)
        return wrapper
    return decorator


def require_rate_limit() -> Callable:
    """Decorator to enforce rate limiting on a function.

    Returns:
        Decorator function

    Example:
        >>> @require_rate_limit()
        ... def api_endpoint(controller, user_id, data):
        ...     # Only runs if within rate limit
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(
            controller: AccessController,
            user_id: str,
            *args,
            **kwargs,
        ) -> Any:
            result = controller.check_rate_limit(user_id)
            if not result.allowed:
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {result.current_count}/{result.limit}. "
                    f"Reset in {result.reset_in_seconds:.0f}s"
                )
            return func(controller, user_id, *args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


class TierManager:
    """Manager for subscription tier operations."""

    @staticmethod
    def get_tier_features(tier: TierType) -> dict[str, Any]:
        """Get features available for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Dictionary of tier features
        """
        from config.constants import TIER_CONFIGS

        config = TIER_CONFIGS[tier]

        return {
            "name": config.name,
            "price_usd": config.price_usd,
            "operations_per_month": config.operations_per_month,
            "pqc_enabled": config.pqc_enabled,
            "smart_contract_enabled": config.smart_contract_enabled,
            "asr_frequency": config.asr_frequency,
            "rate_limit": RATE_LIMITS[tier],
        }

    @staticmethod
    def can_use_pqc(tier: TierType) -> bool:
        """Check if tier can use PQC features.

        Args:
            tier: Subscription tier

        Returns:
            True if PQC is enabled for tier
        """
        from config.constants import TIER_CONFIGS
        return TIER_CONFIGS[tier].pqc_enabled

    @staticmethod
    def can_use_smart_contracts(tier: TierType) -> bool:
        """Check if tier can use smart contract features.

        Args:
            tier: Subscription tier

        Returns:
            True if smart contracts enabled for tier
        """
        from config.constants import TIER_CONFIGS
        return TIER_CONFIGS[tier].smart_contract_enabled
