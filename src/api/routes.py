"""API Routes for PULSAR SENTINEL.

Provides REST API endpoints for:
- POST /encrypt: Encrypt data using PQC or legacy crypto
- POST /decrypt: Decrypt data
- GET /status: Get system and user status
- GET /asr/{user_id}: Get ASR records for a user
- POST /auth/nonce: Request authentication nonce
- POST /auth/verify: Verify signature and get token
"""

import base64
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field

from api.auth import MetaMaskAuth, extract_token_from_header, WalletSession
from core.pqc import HybridEncryptor, HybridCiphertext, get_pqc_engine, LIBOQS_AVAILABLE
from core.legacy import LegacyCrypto, AESCiphertext
from core.asr_engine import ASREngine, AgentStateRecord, PQCStatus, determine_pqc_status
from governance.access_control import (
    AccessController,
    UserRole,
    PERMISSION_ENCRYPT,
    PERMISSION_DECRYPT,
    PERMISSION_ASR_READ,
    RateLimitExceeded,
)
from governance.pts_calculator import PTSCalculator
from governance.rules_engine import RulesEngine, UserState
from config.constants import ThreatLevel, TierType
from config.logging import SecurityEventLogger

logger = SecurityEventLogger("api")

# Create router
router = APIRouter()

# Shared instances (initialized in server.py)
_auth: MetaMaskAuth | None = None
_access_controller: AccessController | None = None
_asr_engine: ASREngine | None = None
_pts_calculator: PTSCalculator | None = None
_rules_engine: RulesEngine | None = None


def init_routes(
    auth: MetaMaskAuth,
    access_controller: AccessController,
    asr_engine: ASREngine,
    pts_calculator: PTSCalculator,
    rules_engine: RulesEngine,
) -> None:
    """Initialize route dependencies.

    Args:
        auth: MetaMask auth handler
        access_controller: Access controller instance
        asr_engine: ASR engine instance
        pts_calculator: PTS calculator instance
        rules_engine: Rules engine instance
    """
    global _auth, _access_controller, _asr_engine, _pts_calculator, _rules_engine
    _auth = auth
    _access_controller = access_controller
    _asr_engine = asr_engine
    _pts_calculator = pts_calculator
    _rules_engine = rules_engine


# Request/Response Models

class NonceRequest(BaseModel):
    """Request for authentication nonce."""
    wallet_address: str = Field(..., description="Ethereum wallet address")


class NonceResponse(BaseModel):
    """Response containing authentication nonce."""
    nonce: str
    message: str
    expires_at: str


class AuthRequest(BaseModel):
    """Authentication request with signature."""
    wallet_address: str
    signature: str
    nonce: str


class AuthResponse(BaseModel):
    """Authentication response with token."""
    token: str
    wallet_address: str
    expires_at: str


class EncryptRequest(BaseModel):
    """Request to encrypt data."""
    data: str = Field(..., description="Base64-encoded data to encrypt")
    algorithm: str = Field(
        default="hybrid",
        description="Algorithm: 'hybrid' (PQC), 'aes' (legacy)"
    )
    public_key: str | None = Field(
        default=None,
        description="Base64-encoded public key (for hybrid)"
    )
    password: str | None = Field(
        default=None,
        description="Password for key derivation (for AES)"
    )


class EncryptResponse(BaseModel):
    """Response containing encrypted data."""
    ciphertext: str
    algorithm: str
    key_id: str | None = None


class DecryptRequest(BaseModel):
    """Request to decrypt data."""
    ciphertext: str = Field(..., description="Base64-encoded ciphertext")
    algorithm: str = Field(
        default="hybrid",
        description="Algorithm: 'hybrid' (PQC), 'aes' (legacy)"
    )
    secret_key: str | None = Field(
        default=None,
        description="Base64-encoded secret key (for hybrid)"
    )
    password: str | None = Field(
        default=None,
        description="Password for key derivation (for AES)"
    )


class DecryptResponse(BaseModel):
    """Response containing decrypted data."""
    data: str
    algorithm: str


class StatusResponse(BaseModel):
    """System and user status response."""
    status: str
    pqc_available: bool
    user: dict | None
    pts: dict | None
    timestamp: str


class ASRResponse(BaseModel):
    """ASR record response."""
    records: list[dict]
    total_count: int
    user_id: str


class KeyGenerateResponse(BaseModel):
    """Response containing generated key pair."""
    public_key: str
    key_id: str
    algorithm: str


# Dependency for authentication
async def get_current_session(
    authorization: str | None = Header(default=None),
) -> WalletSession:
    """Get current authenticated session.

    Args:
        authorization: Authorization header

    Returns:
        WalletSession for authenticated user

    Raises:
        HTTPException: If not authenticated
    """
    if _auth is None:
        raise HTTPException(status_code=500, detail="Auth not initialized")

    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    session = _auth.get_session(token)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return session


# Authentication Endpoints

@router.post("/auth/nonce", response_model=NonceResponse, tags=["Authentication"])
async def request_nonce(request: NonceRequest) -> NonceResponse:
    """Request an authentication nonce for wallet signing.

    The returned message should be signed using MetaMask or compatible wallet.
    """
    if _auth is None:
        raise HTTPException(status_code=500, detail="Auth not initialized")

    nonce = _auth.create_nonce(request.wallet_address)

    return NonceResponse(
        nonce=nonce.nonce,
        message=nonce.get_message(),
        expires_at=nonce.expires_at.isoformat(),
    )


@router.post("/auth/verify", response_model=AuthResponse, tags=["Authentication"])
async def verify_signature(request: AuthRequest) -> AuthResponse:
    """Verify wallet signature and issue JWT token."""
    if _auth is None:
        raise HTTPException(status_code=500, detail="Auth not initialized")

    session = _auth.authenticate(
        request.wallet_address,
        request.signature,
        request.nonce,
    )

    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Signature verification failed",
        )

    # Register user if not exists
    if _access_controller:
        user = _access_controller.get_user(session.wallet_address)
        if user is None:
            _access_controller.register_user(
                session.wallet_address,
                role=UserRole.USER,
                tier=TierType.LEGACY_BUILDER,
            )

    return AuthResponse(
        token=session.token,
        wallet_address=session.wallet_address,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/auth/logout", tags=["Authentication"])
async def logout(session: WalletSession = Depends(get_current_session)) -> dict:
    """Logout and revoke current session."""
    if _auth:
        _auth.revoke_session(session.token)

    return {"message": "Logged out successfully"}


# Cryptographic Endpoints

@router.post("/keys/generate", response_model=KeyGenerateResponse, tags=["Cryptography"])
async def generate_keys(
    algorithm: str = Query(default="hybrid", description="Algorithm: 'hybrid' or 'aes'"),
    session: WalletSession = Depends(get_current_session),
) -> KeyGenerateResponse:
    """Generate a new key pair for encryption."""
    if _access_controller is None:
        raise HTTPException(status_code=500, detail="Access control not initialized")

    # Check permission
    if not _access_controller.has_permission(session.wallet_address, PERMISSION_ENCRYPT):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Check rate limit
    result = _access_controller.check_rate_limit(session.wallet_address, "keys/generate")
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Reset in {result.reset_in_seconds:.0f}s",
        )

    if algorithm == "hybrid":
        if not LIBOQS_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="PQC not available. Use algorithm='aes' for legacy crypto.",
            )

        encryptor = HybridEncryptor()
        keypair = encryptor.generate_keypair()

        return KeyGenerateResponse(
            public_key=base64.b64encode(keypair.public_key).decode(),
            key_id=keypair.key_id,
            algorithm=keypair.algorithm,
        )

    elif algorithm == "aes":
        # For AES, we generate a random key
        import os
        key = os.urandom(64)  # 32 for AES + 32 for HMAC

        return KeyGenerateResponse(
            public_key=base64.b64encode(key).decode(),
            key_id=base64.b64encode(os.urandom(8)).decode(),
            algorithm="AES-256-CBC-HMAC-SHA256",
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown algorithm: {algorithm}")


@router.post("/encrypt", response_model=EncryptResponse, tags=["Cryptography"])
async def encrypt_data(
    request: EncryptRequest,
    session: WalletSession = Depends(get_current_session),
) -> EncryptResponse:
    """Encrypt data using PQC hybrid or legacy AES."""
    if _access_controller is None:
        raise HTTPException(status_code=500, detail="Access control not initialized")

    # Check permission
    if not _access_controller.has_permission(session.wallet_address, PERMISSION_ENCRYPT):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Check rate limit
    result = _access_controller.check_rate_limit(session.wallet_address, "encrypt")
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Reset in {result.reset_in_seconds:.0f}s",
        )

    try:
        plaintext = base64.b64decode(request.data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data")

    if request.algorithm == "hybrid":
        if not LIBOQS_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="PQC not available. Use algorithm='aes' for legacy crypto.",
            )

        if not request.public_key:
            raise HTTPException(status_code=400, detail="public_key required for hybrid")

        try:
            public_key = base64.b64decode(request.public_key)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 public_key")

        encryptor = HybridEncryptor()
        ciphertext = encryptor.encrypt(plaintext, public_key)

        # Create ASR
        if _asr_engine:
            _asr_engine.create_asr(
                agent_id=session.wallet_address,
                action="encrypt_hybrid",
                threat_level=ThreatLevel.INFO,
                pqc_status=PQCStatus.SAFE,
            )

        return EncryptResponse(
            ciphertext=base64.b64encode(ciphertext.to_bytes()).decode(),
            algorithm=ciphertext.algorithm,
        )

    elif request.algorithm == "aes":
        if not request.password:
            raise HTTPException(status_code=400, detail="password required for AES")

        crypto = LegacyCrypto()
        key, salt = crypto.derive_key(request.password.encode())
        ciphertext = crypto.encrypt(plaintext, key, salt)

        # Create ASR
        if _asr_engine:
            _asr_engine.create_asr(
                agent_id=session.wallet_address,
                action="encrypt_aes",
                threat_level=ThreatLevel.INFO,
                pqc_status=PQCStatus.WARNING,  # AES is not quantum-safe
            )

        return EncryptResponse(
            ciphertext=base64.b64encode(ciphertext.to_bytes()).decode(),
            algorithm="AES-256-CBC-HMAC-SHA256",
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown algorithm: {request.algorithm}")


@router.post("/decrypt", response_model=DecryptResponse, tags=["Cryptography"])
async def decrypt_data(
    request: DecryptRequest,
    session: WalletSession = Depends(get_current_session),
) -> DecryptResponse:
    """Decrypt data using PQC hybrid or legacy AES."""
    if _access_controller is None:
        raise HTTPException(status_code=500, detail="Access control not initialized")

    # Check permission
    if not _access_controller.has_permission(session.wallet_address, PERMISSION_DECRYPT):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Check rate limit
    result = _access_controller.check_rate_limit(session.wallet_address, "decrypt")
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Reset in {result.reset_in_seconds:.0f}s",
        )

    try:
        ciphertext_bytes = base64.b64decode(request.ciphertext)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 ciphertext")

    if request.algorithm == "hybrid":
        if not LIBOQS_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="PQC not available",
            )

        if not request.secret_key:
            raise HTTPException(status_code=400, detail="secret_key required for hybrid")

        try:
            secret_key = base64.b64decode(request.secret_key)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 secret_key")

        try:
            ciphertext = HybridCiphertext.from_bytes(ciphertext_bytes, "HYBRID")
            encryptor = HybridEncryptor()
            plaintext = encryptor.decrypt(ciphertext, secret_key)

            return DecryptResponse(
                data=base64.b64encode(plaintext).decode(),
                algorithm="HYBRID",
            )

        except Exception as e:
            # Record signature failure
            if _pts_calculator:
                _pts_calculator.record_signature_failure(
                    session.wallet_address,
                    "decrypt_failure",
                )

            raise HTTPException(status_code=400, detail=f"Decryption failed: {e}")

    elif request.algorithm == "aes":
        if not request.password:
            raise HTTPException(status_code=400, detail="password required for AES")

        try:
            ciphertext = AESCiphertext.from_bytes(ciphertext_bytes)
            crypto = LegacyCrypto()
            key, _ = crypto.derive_key(request.password.encode(), ciphertext.salt)
            plaintext = crypto.decrypt(ciphertext, key)

            return DecryptResponse(
                data=base64.b64encode(plaintext).decode(),
                algorithm="AES-256-CBC-HMAC-SHA256",
            )

        except Exception as e:
            # Record signature failure
            if _pts_calculator:
                _pts_calculator.record_signature_failure(
                    session.wallet_address,
                    "decrypt_failure",
                )

            raise HTTPException(status_code=400, detail=f"Decryption failed: {e}")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown algorithm: {request.algorithm}")


# Status Endpoints

@router.get("/status", response_model=StatusResponse, tags=["Status"])
async def get_status(
    session: WalletSession | None = Depends(get_current_session),
) -> StatusResponse:
    """Get system status and user information."""
    user_info = None
    pts_info = None

    if session and _access_controller:
        user = _access_controller.get_user(session.wallet_address)
        if user:
            user_info = {
                "wallet_address": user.user_id,
                "role": user.role.name,
                "tier": user.tier.value,
                "rate_limit": user.get_rate_limit(),
            }

    if session and _pts_calculator:
        score = _pts_calculator.calculate_pts(session.wallet_address)
        pts_info = score.to_dict()

    return StatusResponse(
        status="operational",
        pqc_available=LIBOQS_AVAILABLE,
        user=user_info,
        pts=pts_info,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health", tags=["Status"])
async def health_check() -> dict:
    """Health check endpoint (no auth required)."""
    return {
        "status": "healthy",
        "pqc_available": LIBOQS_AVAILABLE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ASR Endpoints

@router.get("/asr/{user_id}", response_model=ASRResponse, tags=["ASR"])
async def get_asr_records(
    user_id: str,
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    threat_level_min: int = Query(default=1, ge=1, le=5),
    session: WalletSession = Depends(get_current_session),
) -> ASRResponse:
    """Get ASR records for a user."""
    if _access_controller is None or _asr_engine is None:
        raise HTTPException(status_code=500, detail="Services not initialized")

    # Check permission
    if not _access_controller.has_permission(session.wallet_address, PERMISSION_ASR_READ):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Users can only read their own ASRs unless admin
    user = _access_controller.get_user(session.wallet_address)
    if user and user.role < UserRole.ADMIN and user_id != session.wallet_address:
        raise HTTPException(status_code=403, detail="Can only read own ASR records")

    records = _asr_engine.list_asr_by_agent(
        agent_id=user_id,
        start_date=start_date,
        end_date=end_date,
        threat_level_min=threat_level_min,
    )

    return ASRResponse(
        records=[r.to_dict() for r in records],
        total_count=len(records),
        user_id=user_id,
    )


# PTS Endpoint

@router.get("/pts/{user_id}", tags=["Governance"])
async def get_pts_score(
    user_id: str,
    session: WalletSession = Depends(get_current_session),
) -> dict:
    """Get PTS (Points Toward Threat Score) for a user."""
    if _pts_calculator is None or _access_controller is None:
        raise HTTPException(status_code=500, detail="Services not initialized")

    # Users can only check their own PTS unless admin
    user = _access_controller.get_user(session.wallet_address)
    if user and user.role < UserRole.ADMIN and user_id != session.wallet_address:
        raise HTTPException(status_code=403, detail="Can only check own PTS")

    score = _pts_calculator.calculate_pts(user_id)
    return score.to_dict()
