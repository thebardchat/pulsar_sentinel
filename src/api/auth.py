"""MetaMask Authentication Module for PULSAR SENTINEL.

Provides wallet-based authentication using MetaMask signatures
for secure, passwordless authentication.

Authentication Flow:
1. Client requests nonce for wallet address
2. Client signs nonce message with MetaMask
3. Server verifies signature and issues JWT token
4. Client uses JWT for subsequent requests
"""

import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

import jwt
from eth_account import Account
from eth_account.messages import encode_defunct

from config.settings import get_settings
from config.constants import ThreatLevel
from config.logging import SecurityEventLogger

logger = SecurityEventLogger("auth")

# Nonce expiration time (5 minutes)
NONCE_EXPIRATION_SECONDS = 300


@dataclass
class AuthNonce:
    """Authentication nonce for wallet signing.

    Attributes:
        nonce: Random nonce string
        wallet_address: Associated wallet address
        created_at: When nonce was created
        expires_at: When nonce expires
    """
    nonce: str
    wallet_address: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default=None)

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(seconds=NONCE_EXPIRATION_SECONDS)

    @property
    def is_expired(self) -> bool:
        """Check if nonce has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def get_message(self) -> str:
        """Get the message to be signed."""
        return (
            f"PULSAR SENTINEL Authentication\n\n"
            f"Please sign this message to authenticate.\n\n"
            f"Wallet: {self.wallet_address}\n"
            f"Nonce: {self.nonce}\n"
            f"Timestamp: {self.created_at.isoformat()}\n\n"
            f"This signature will not cost any gas fees."
        )


@dataclass
class WalletSession:
    """Authenticated wallet session.

    Attributes:
        wallet_address: The authenticated wallet address
        token: JWT token for the session
        created_at: Session creation time
        expires_at: Session expiration time
        metadata: Additional session data
    """
    wallet_address: str
    token: str
    created_at: datetime
    expires_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class TokenPayload:
    """JWT token payload.

    Attributes:
        sub: Subject (wallet address)
        iat: Issued at timestamp
        exp: Expiration timestamp
        nonce: Authentication nonce used
    """
    sub: str
    iat: int
    exp: int
    nonce: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JWT encoding."""
        return {
            "sub": self.sub,
            "iat": self.iat,
            "exp": self.exp,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenPayload":
        """Create from dictionary."""
        return cls(
            sub=data["sub"],
            iat=data["iat"],
            exp=data["exp"],
            nonce=data["nonce"],
        )


class MetaMaskAuth:
    """MetaMask wallet-based authentication handler.

    Manages the authentication flow for wallet-based auth:
    - Nonce generation and management
    - Signature verification
    - JWT token issuance and validation

    Example:
        >>> auth = MetaMaskAuth()
        >>> nonce = auth.create_nonce("0x123...")
        >>> message = nonce.get_message()
        >>> # Client signs message with MetaMask
        >>> session = auth.authenticate(nonce.wallet_address, signature, nonce.nonce)
        >>> # Use session.token for API requests
    """

    def __init__(self) -> None:
        """Initialize MetaMask auth handler."""
        settings = get_settings()

        self._secret_key = settings.jwt_secret_key or secrets.token_hex(32)
        self._algorithm = settings.jwt_algorithm
        self._token_expiration_hours = settings.jwt_expiration_hours

        # Active nonces: wallet_address -> AuthNonce
        self._nonces: dict[str, AuthNonce] = {}

        # Active sessions: token -> WalletSession
        self._sessions: dict[str, WalletSession] = {}

    def create_nonce(self, wallet_address: str) -> AuthNonce:
        """Create a new authentication nonce.

        Args:
            wallet_address: Wallet address requesting authentication

        Returns:
            AuthNonce to be signed by wallet
        """
        # Normalize address
        wallet_address = wallet_address.lower()

        # Generate random nonce
        nonce = secrets.token_hex(32)

        auth_nonce = AuthNonce(
            nonce=nonce,
            wallet_address=wallet_address,
        )

        # Store nonce
        self._nonces[wallet_address] = auth_nonce

        logger.log_event(
            event="nonce_created",
            threat_level=ThreatLevel.INFO,
            agent_id=wallet_address[:10] + "...",
        )

        return auth_nonce

    def get_nonce(self, wallet_address: str) -> AuthNonce | None:
        """Get existing nonce for a wallet.

        Args:
            wallet_address: Wallet address

        Returns:
            AuthNonce if exists and not expired, None otherwise
        """
        wallet_address = wallet_address.lower()
        nonce = self._nonces.get(wallet_address)

        if nonce and nonce.is_expired:
            del self._nonces[wallet_address]
            return None

        return nonce

    def verify_signature(
        self,
        wallet_address: str,
        signature: str,
        nonce: str,
    ) -> bool:
        """Verify a MetaMask signature.

        Args:
            wallet_address: Expected signer address
            signature: The signature (hex string)
            nonce: The nonce that was signed

        Returns:
            True if signature is valid
        """
        wallet_address = wallet_address.lower()

        # Get stored nonce
        stored_nonce = self._nonces.get(wallet_address)
        if stored_nonce is None:
            logger.log_auth_attempt(
                wallet_address=wallet_address,
                success=False,
                failure_reason="No nonce found",
            )
            return False

        if stored_nonce.is_expired:
            del self._nonces[wallet_address]
            logger.log_auth_attempt(
                wallet_address=wallet_address,
                success=False,
                failure_reason="Nonce expired",
            )
            return False

        if stored_nonce.nonce != nonce:
            logger.log_auth_attempt(
                wallet_address=wallet_address,
                success=False,
                failure_reason="Nonce mismatch",
            )
            return False

        try:
            # Get the message that was signed
            message = stored_nonce.get_message()

            # Encode message with Ethereum prefix
            message_encoded = encode_defunct(text=message)

            # Recover address from signature
            recovered_address = Account.recover_message(
                message_encoded,
                signature=signature,
            )

            # Compare addresses (case-insensitive)
            if recovered_address.lower() != wallet_address:
                logger.log_auth_attempt(
                    wallet_address=wallet_address,
                    success=False,
                    failure_reason="Signature verification failed",
                )
                return False

            return True

        except Exception as e:
            logger.log_auth_attempt(
                wallet_address=wallet_address,
                success=False,
                failure_reason=str(e),
            )
            return False

    def authenticate(
        self,
        wallet_address: str,
        signature: str,
        nonce: str,
    ) -> WalletSession | None:
        """Authenticate a wallet and create session.

        Args:
            wallet_address: Wallet address
            signature: MetaMask signature
            nonce: The signed nonce

        Returns:
            WalletSession if authentication succeeds, None otherwise
        """
        wallet_address = wallet_address.lower()

        # Verify signature
        if not self.verify_signature(wallet_address, signature, nonce):
            return None

        # Create JWT token
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self._token_expiration_hours)

        payload = TokenPayload(
            sub=wallet_address,
            iat=int(now.timestamp()),
            exp=int(expires_at.timestamp()),
            nonce=nonce,
        )

        token = jwt.encode(
            payload.to_dict(),
            self._secret_key,
            algorithm=self._algorithm,
        )

        # Create session
        session = WalletSession(
            wallet_address=wallet_address,
            token=token,
            created_at=now,
            expires_at=expires_at,
        )

        # Store session
        self._sessions[token] = session

        # Remove used nonce
        if wallet_address in self._nonces:
            del self._nonces[wallet_address]

        logger.log_auth_attempt(
            wallet_address=wallet_address,
            success=True,
        )

        return session

    def validate_token(self, token: str) -> TokenPayload | None:
        """Validate a JWT token.

        Args:
            token: JWT token to validate

        Returns:
            TokenPayload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return TokenPayload.from_dict(payload)

        except jwt.ExpiredSignatureError:
            logger.log_event(
                event="token_expired",
                threat_level=ThreatLevel.INFO,
                agent_id="unknown",
            )
            return None

        except jwt.InvalidTokenError as e:
            logger.log_event(
                event="token_invalid",
                threat_level=ThreatLevel.CAUTION,
                agent_id="unknown",
                metadata={"error": str(e)},
            )
            return None

    def get_session(self, token: str) -> WalletSession | None:
        """Get session for a token.

        Args:
            token: JWT token

        Returns:
            WalletSession if valid, None otherwise
        """
        # Validate token first
        payload = self.validate_token(token)
        if payload is None:
            return None

        # Check session store
        session = self._sessions.get(token)
        if session and session.is_expired:
            del self._sessions[token]
            return None

        # If not in store but token is valid, create session
        if session is None:
            session = WalletSession(
                wallet_address=payload.sub,
                token=token,
                created_at=datetime.fromtimestamp(payload.iat, tz=timezone.utc),
                expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
            )
            self._sessions[token] = session

        return session

    def revoke_session(self, token: str) -> bool:
        """Revoke a session.

        Args:
            token: Token to revoke

        Returns:
            True if session was revoked
        """
        if token in self._sessions:
            wallet = self._sessions[token].wallet_address
            del self._sessions[token]

            logger.log_event(
                event="session_revoked",
                threat_level=ThreatLevel.INFO,
                agent_id=wallet[:10] + "...",
            )
            return True

        return False

    def cleanup_expired(self) -> int:
        """Clean up expired nonces and sessions.

        Returns:
            Number of items cleaned up
        """
        count = 0

        # Clean expired nonces
        expired_nonces = [
            addr for addr, nonce in self._nonces.items()
            if nonce.is_expired
        ]
        for addr in expired_nonces:
            del self._nonces[addr]
            count += 1

        # Clean expired sessions
        expired_sessions = [
            token for token, session in self._sessions.items()
            if session.is_expired
        ]
        for token in expired_sessions:
            del self._sessions[token]
            count += 1

        return count


def extract_token_from_header(authorization: str | None) -> str | None:
    """Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Token string if found, None otherwise
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer":
        return None

    return token
