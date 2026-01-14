"""Structured logging configuration for PULSAR SENTINEL."""

import sys
import logging
from pathlib import Path
from typing import Any

import structlog
from structlog.typing import Processor

from config.settings import get_settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()

    # Ensure log directory exists
    log_dir = settings.log_file_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a bound logger with the given name."""
    return structlog.get_logger(name)


class SecurityEventLogger:
    """Logger specifically for security events.

    This logger ensures all security-relevant events are captured
    with consistent structure for ASR integration.
    """

    def __init__(self, component: str) -> None:
        """Initialize security event logger.

        Args:
            component: The component name (e.g., 'pqc', 'blockchain', 'auth')
        """
        self._logger = get_logger(f"security.{component}")
        self._component = component

    def log_event(
        self,
        event: str,
        threat_level: int,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a security event.

        Args:
            event: Description of the security event
            threat_level: Severity level (1-5)
            agent_id: Optional agent/user identifier
            metadata: Additional event metadata
        """
        self._logger.info(
            event,
            component=self._component,
            threat_level=threat_level,
            agent_id=agent_id,
            metadata=metadata or {},
        )

    def log_crypto_operation(
        self,
        operation: str,
        algorithm: str,
        success: bool,
        duration_ms: float | None = None,
    ) -> None:
        """Log a cryptographic operation.

        Args:
            operation: Type of operation (encrypt, decrypt, keygen)
            algorithm: Algorithm used (ML-KEM-768, AES-256-GCM, etc.)
            success: Whether operation succeeded
            duration_ms: Operation duration in milliseconds
        """
        self._logger.info(
            f"crypto_{operation}",
            operation=operation,
            algorithm=algorithm,
            success=success,
            duration_ms=duration_ms,
        )

    def log_auth_attempt(
        self,
        wallet_address: str,
        success: bool,
        failure_reason: str | None = None,
    ) -> None:
        """Log an authentication attempt.

        Args:
            wallet_address: The wallet address attempting auth
            success: Whether authentication succeeded
            failure_reason: Reason for failure if applicable
        """
        level = "info" if success else "warning"
        getattr(self._logger, level)(
            "auth_attempt",
            wallet_address=wallet_address[:10] + "...",  # Truncate for privacy
            success=success,
            failure_reason=failure_reason,
        )

    def log_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        current_count: int,
        limit: int,
    ) -> None:
        """Log a rate limit event.

        Args:
            user_id: User identifier
            endpoint: API endpoint being accessed
            current_count: Current request count
            limit: Rate limit threshold
        """
        exceeded = current_count >= limit
        self._logger.warning(
            "rate_limit_event",
            user_id=user_id,
            endpoint=endpoint,
            current_count=current_count,
            limit=limit,
            exceeded=exceeded,
        )

    def log_blockchain_event(
        self,
        event_type: str,
        tx_hash: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Log a blockchain-related event.

        Args:
            event_type: Type of blockchain event
            tx_hash: Transaction hash if applicable
            success: Whether operation succeeded
            error: Error message if failed
        """
        if success:
            self._logger.info(
                "blockchain_event",
                event_type=event_type,
                tx_hash=tx_hash,
            )
        else:
            self._logger.error(
                "blockchain_error",
                event_type=event_type,
                tx_hash=tx_hash,
                error=error,
            )
