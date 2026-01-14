"""Application settings using Pydantic Settings management."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.constants import (
    DEFAULT_KEY_ROTATION_DAYS,
    DEFAULT_RATE_LIMIT,
    DEFAULT_STRIKE_THRESHOLD,
    DEFAULT_BAN_DURATION_HOURS,
    DEFAULT_HEIR_TRANSFER_DAYS,
    PTSThreshold,
    PQCSecurityLevel,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Blockchain Configuration
    polygon_mainnet_rpc: str = Field(
        default="https://polygon-rpc.com",
        description="Polygon mainnet RPC endpoint",
    )
    polygon_testnet_rpc: str = Field(
        default="https://rpc-amoy.polygon.technology",
        description="Polygon testnet (Amoy) RPC endpoint",
    )
    polygon_network: Literal["mainnet", "testnet"] = Field(
        default="testnet",
        description="Active Polygon network",
    )
    governance_contract_address: str = Field(
        default="",
        description="Deployed governance contract address",
    )
    server_wallet_private_key: str = Field(
        default="",
        description="Server wallet private key (keep secret!)",
    )

    # Security Configuration
    pqc_security_level: int = Field(
        default=PQCSecurityLevel.LEVEL_768,
        description="ML-KEM security level (768 or 1024)",
    )
    key_rotation_days: int = Field(
        default=DEFAULT_KEY_ROTATION_DAYS,
        description="Key rotation interval in days",
    )
    aes_key_size: int = Field(
        default=256,
        description="AES key size in bits",
    )
    hmac_algorithm: str = Field(
        default="SHA256",
        description="HMAC algorithm",
    )

    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )
    api_port: int = Field(
        default=8000,
        description="API server port",
    )
    api_debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # Rate Limiting
    rate_limit_default: int = Field(
        default=DEFAULT_RATE_LIMIT,
        description="Default rate limit (requests/minute)",
    )
    rate_limit_sentinel: int = Field(
        default=10,
        description="Sentinel tier rate limit",
    )
    rate_limit_legacy: int = Field(
        default=5,
        description="Legacy tier rate limit",
    )
    rate_limit_guild: int = Field(
        default=100,
        description="Guild tier rate limit",
    )

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="",
        description="JWT signing secret key",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT algorithm",
    )
    jwt_expiration_hours: int = Field(
        default=24,
        description="JWT token expiration in hours",
    )

    # ASR Configuration
    asr_storage_path: str = Field(
        default="./data/asr",
        description="ASR local storage path",
    )
    asr_min_log_level: int = Field(
        default=1,
        description="Minimum threat level to log",
    )
    asr_blockchain_enabled: bool = Field(
        default=True,
        description="Enable blockchain logging for ASR",
    )

    # Governance Configuration
    strike_threshold: int = Field(
        default=DEFAULT_STRIKE_THRESHOLD,
        description="Number of strikes before ban",
    )
    strike_ban_duration_hours: int = Field(
        default=DEFAULT_BAN_DURATION_HOURS,
        description="Ban duration in hours after strikes",
    )
    heir_transfer_days: int = Field(
        default=DEFAULT_HEIR_TRANSFER_DAYS,
        description="Days until heir transfer on unresponsive",
    )

    # PTS Configuration
    pts_tier1_max: int = Field(
        default=PTSThreshold.TIER1_MAX,
        description="Max PTS for Tier 1 (Safe)",
    )
    pts_tier2_max: int = Field(
        default=PTSThreshold.TIER2_MAX,
        description="Max PTS for Tier 2 (Caution)",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format",
    )
    log_file_path: str = Field(
        default="./logs/pulsar_sentinel.log",
        description="Log file path",
    )

    @field_validator("pqc_security_level")
    @classmethod
    def validate_pqc_level(cls, v: int) -> int:
        """Validate PQC security level."""
        valid_levels = [768, 1024]
        if v not in valid_levels:
            raise ValueError(f"PQC security level must be one of {valid_levels}")
        return v

    @property
    def polygon_rpc_url(self) -> str:
        """Get the active Polygon RPC URL."""
        if self.polygon_network == "mainnet":
            return self.polygon_mainnet_rpc
        return self.polygon_testnet_rpc

    @property
    def asr_storage_dir(self) -> Path:
        """Get ASR storage directory as Path."""
        return Path(self.asr_storage_path)

    @property
    def log_file_dir(self) -> Path:
        """Get log file directory as Path."""
        return Path(self.log_file_path).parent


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
