"""Constants and enumerations for PULSAR SENTINEL."""

from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Final


class ThreatLevel(IntEnum):
    """Threat level classification for ASR records.

    1: Info - Routine operations (key rotation, normal activity)
    2: Caution - Minor issues (failed auth attempt)
    3: Warning - Moderate concern (quantum-adjacent cipher detected)
    4: Alert - Significant concern (potential breach pattern)
    5: Critical - Immediate action required (active exploitation)
    """
    INFO = 1
    CAUTION = 2
    WARNING = 3
    ALERT = 4
    CRITICAL = 5


class TierType(str, Enum):
    """Subscription tier types."""
    SENTINEL_CORE = "sentinel_core"
    LEGACY_BUILDER = "legacy_builder"
    AUTONOMOUS_GUILD = "autonomous_guild"


class PQCStatus(str, Enum):
    """Post-quantum cryptography status indicators."""
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"


class PQCSecurityLevel(IntEnum):
    """ML-KEM security levels (NIST standards)."""
    LEVEL_768 = 768   # ML-KEM-768: ~NIST Level 3
    LEVEL_1024 = 1024  # ML-KEM-1024: ~NIST Level 5


class PTSThreshold(IntEnum):
    """Points Toward Threat Score thresholds."""
    TIER1_MAX = 50    # Safe (Green)
    TIER2_MAX = 150   # Caution (Yellow)
    # Anything >= TIER2_MAX is Critical (Red)


class PTSTier(str, Enum):
    """PTS tier classifications."""
    SAFE = "safe"          # PTS < 50 (Green)
    CAUTION = "caution"    # 50 <= PTS < 150 (Yellow)
    CRITICAL = "critical"  # PTS >= 150 (Red)


class RoleType(str, Enum):
    """User role types for access control."""
    ADMIN = "admin"
    SENTINEL = "sentinel"
    USER = "user"


class RuleCode(str, Enum):
    """Self-governance rule codes.

    RC 1.01: All public requests require encryption signature
    RC 1.02: Unresponsive state triggers 90-day transfer to designated heir
    RC 2.01: Minimum 3-strike rule enforcement
    RC 3.02: Automated AI protocol execution on transaction failure
    """
    RC_1_01 = "RC_1.01"  # Encryption signature required
    RC_1_02 = "RC_1.02"  # Heir transfer on unresponsive
    RC_2_01 = "RC_2.01"  # Three-strike policy
    RC_3_02 = "RC_3.02"  # Fallback to Gryphon network


@dataclass(frozen=True)
class TierConfig:
    """Configuration for subscription tiers."""
    name: str
    price_usd: float
    operations_per_month: int  # -1 for unlimited
    pqc_enabled: bool
    smart_contract_enabled: bool
    asr_frequency: str  # daily, weekly, realtime


# Tier configurations
TIER_CONFIGS: dict[TierType, TierConfig] = {
    TierType.SENTINEL_CORE: TierConfig(
        name="Sentinel Core",
        price_usd=16.99,
        operations_per_month=10_000_000,
        pqc_enabled=True,
        smart_contract_enabled=False,
        asr_frequency="daily",
    ),
    TierType.LEGACY_BUILDER: TierConfig(
        name="Legacy Builder",
        price_usd=10.99,
        operations_per_month=5_000_000,
        pqc_enabled=False,
        smart_contract_enabled=False,
        asr_frequency="weekly",
    ),
    TierType.AUTONOMOUS_GUILD: TierConfig(
        name="Autonomous Guild",
        price_usd=29.99,
        operations_per_month=-1,  # Unlimited
        pqc_enabled=True,
        smart_contract_enabled=True,
        asr_frequency="realtime",
    ),
}

# Rate limits (requests per minute)
RATE_LIMITS: dict[TierType, int] = {
    TierType.SENTINEL_CORE: 10,
    TierType.LEGACY_BUILDER: 5,
    TierType.AUTONOMOUS_GUILD: 100,
}

# PTS calculation weights
PTS_WEIGHTS: Final[dict[str, float]] = {
    "quantum_risk_factor": 0.4,
    "access_violation_count": 0.3,
    "rate_limit_violations": 0.2,
    "signature_failures": 0.1,
}

# Cryptographic constants
AES_KEY_SIZE: Final[int] = 256
AES_BLOCK_SIZE: Final[int] = 128
GCM_NONCE_SIZE: Final[int] = 12
GCM_TAG_SIZE: Final[int] = 16
HMAC_DIGEST_SIZE: Final[int] = 32

# Key rotation
DEFAULT_KEY_ROTATION_DAYS: Final[int] = 90

# Strike policy
DEFAULT_STRIKE_THRESHOLD: Final[int] = 3
DEFAULT_BAN_DURATION_HOURS: Final[int] = 24

# Heir transfer
DEFAULT_HEIR_TRANSFER_DAYS: Final[int] = 90

# API defaults
DEFAULT_RATE_LIMIT: Final[int] = 5
MAX_REQUEST_SIZE: Final[int] = 10 * 1024 * 1024  # 10 MB

# Blockchain constants
POLYGON_CHAIN_ID_MAINNET: Final[int] = 137
POLYGON_CHAIN_ID_TESTNET: Final[int] = 80002  # Amoy testnet

# Algorithm identifiers
ML_KEM_768_OID: Final[str] = "1.3.6.1.4.1.2.267.12.4.4"
ML_KEM_1024_OID: Final[str] = "1.3.6.1.4.1.2.267.12.6.6"
AES_256_GCM_OID: Final[str] = "2.16.840.1.101.3.4.1.46"
ECDSA_SECP256K1_OID: Final[str] = "1.3.132.0.10"
