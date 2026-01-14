"""Post-Quantum Cryptography Engine for PULSAR SENTINEL.

Implements ML-KEM (CRYSTALS-Kyber) key encapsulation with hybrid encryption
combining quantum-resistant and classical cryptographic primitives.

Security Model:
- ML-KEM-768: NIST Level 3 security (~AES-192 equivalent)
- ML-KEM-1024: NIST Level 5 security (~AES-256 equivalent)
- Hybrid: ML-KEM + AES-256-GCM for defense in depth

Performance Targets:
- Key generation: < 500ms
- Encryption: < 100ms
- Memory efficient for 7.4GB RAM systems
"""

import os
import time
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

# Attempt to import liboqs - gracefully handle if not available
try:
    import oqs
    LIBOQS_AVAILABLE = True
except ImportError:
    LIBOQS_AVAILABLE = False
    oqs = None

from config.constants import (
    PQCSecurityLevel,
    GCM_NONCE_SIZE,
    GCM_TAG_SIZE,
    AES_KEY_SIZE,
)
from config.logging import SecurityEventLogger

# Constants
ML_KEM_768_NAME: Final[str] = "ML-KEM-768"
ML_KEM_1024_NAME: Final[str] = "ML-KEM-1024"
SHARED_SECRET_SIZE: Final[int] = 32  # 256 bits
INFO_LABEL: Final[bytes] = b"PULSAR-SENTINEL-HYBRID-v1"

logger = SecurityEventLogger("pqc")


@dataclass
class MLKEMKeyPair:
    """ML-KEM key pair container.

    Attributes:
        public_key: The public encapsulation key
        secret_key: The private decapsulation key
        algorithm: The ML-KEM variant used
        created_at: Key pair creation timestamp
        key_id: Unique identifier for this key pair
    """
    public_key: bytes
    secret_key: bytes
    algorithm: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    key_id: str = field(default_factory=lambda: secrets.token_hex(16))

    def __post_init__(self) -> None:
        """Validate key pair after initialization."""
        if not self.public_key or not self.secret_key:
            raise ValueError("Both public and secret keys are required")

    @property
    def public_key_hash(self) -> str:
        """Get SHA-256 hash of the public key for identification."""
        return hashlib.sha256(self.public_key).hexdigest()[:16]


@dataclass
class EncapsulationResult:
    """Result of ML-KEM encapsulation operation.

    Attributes:
        ciphertext: The encapsulated ciphertext
        shared_secret: The derived shared secret
    """
    ciphertext: bytes
    shared_secret: bytes


@dataclass
class HybridCiphertext:
    """Hybrid encryption ciphertext container.

    Combines ML-KEM encapsulation with AES-GCM symmetric encryption.

    Attributes:
        kem_ciphertext: ML-KEM encapsulated key
        aes_nonce: AES-GCM nonce
        aes_ciphertext: AES-GCM encrypted data (includes auth tag)
        algorithm: Algorithm identifier string
    """
    kem_ciphertext: bytes
    aes_nonce: bytes
    aes_ciphertext: bytes
    algorithm: str

    def to_bytes(self) -> bytes:
        """Serialize to bytes format."""
        # Format: [4-byte kem_len][kem_ciphertext][12-byte nonce][aes_ciphertext]
        kem_len = len(self.kem_ciphertext).to_bytes(4, "big")
        return kem_len + self.kem_ciphertext + self.aes_nonce + self.aes_ciphertext

    @classmethod
    def from_bytes(cls, data: bytes, algorithm: str) -> "HybridCiphertext":
        """Deserialize from bytes format."""
        kem_len = int.from_bytes(data[:4], "big")
        kem_ciphertext = data[4:4 + kem_len]
        aes_nonce = data[4 + kem_len:4 + kem_len + GCM_NONCE_SIZE]
        aes_ciphertext = data[4 + kem_len + GCM_NONCE_SIZE:]
        return cls(
            kem_ciphertext=kem_ciphertext,
            aes_nonce=aes_nonce,
            aes_ciphertext=aes_ciphertext,
            algorithm=algorithm,
        )


class PQCEngine:
    """Post-Quantum Cryptography engine using ML-KEM.

    Provides key generation, encapsulation, and decapsulation using
    liboqs implementation of ML-KEM (CRYSTALS-Kyber).

    Example:
        >>> engine = PQCEngine(security_level=768)
        >>> keypair = engine.generate_keypair()
        >>> result = engine.encapsulate(keypair.public_key)
        >>> shared_secret = engine.decapsulate(result.ciphertext, keypair.secret_key)
    """

    def __init__(self, security_level: int = PQCSecurityLevel.LEVEL_768) -> None:
        """Initialize PQC engine.

        Args:
            security_level: ML-KEM security level (768 or 1024)

        Raises:
            RuntimeError: If liboqs is not available
            ValueError: If security level is invalid
        """
        if not LIBOQS_AVAILABLE:
            raise RuntimeError(
                "liboqs-python is required for PQC operations. "
                "Install with: pip install liboqs-python"
            )

        if security_level not in (768, 1024):
            raise ValueError(f"Invalid security level: {security_level}. Must be 768 or 1024")

        self._security_level = security_level
        self._algorithm = ML_KEM_768_NAME if security_level == 768 else ML_KEM_1024_NAME
        self._kem: oqs.KeyEncapsulation | None = None

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        return self._algorithm

    @property
    def security_level(self) -> int:
        """Get the security level."""
        return self._security_level

    def _get_kem(self) -> "oqs.KeyEncapsulation":
        """Get or create the KEM instance (lazy initialization)."""
        if self._kem is None:
            # Map our names to liboqs algorithm names
            liboqs_name = "Kyber768" if self._security_level == 768 else "Kyber1024"
            self._kem = oqs.KeyEncapsulation(liboqs_name)
        return self._kem

    def generate_keypair(self) -> MLKEMKeyPair:
        """Generate a new ML-KEM key pair.

        Returns:
            MLKEMKeyPair containing public and secret keys

        Performance:
            Target: < 500ms
        """
        start_time = time.perf_counter()

        kem = self._get_kem()
        public_key = kem.generate_keypair()
        secret_key = kem.export_secret_key()

        duration_ms = (time.perf_counter() - start_time) * 1000

        keypair = MLKEMKeyPair(
            public_key=public_key,
            secret_key=secret_key,
            algorithm=self._algorithm,
        )

        logger.log_crypto_operation(
            operation="keygen",
            algorithm=self._algorithm,
            success=True,
            duration_ms=duration_ms,
        )

        return keypair

    def encapsulate(self, public_key: bytes) -> EncapsulationResult:
        """Encapsulate a shared secret using a public key.

        Args:
            public_key: The recipient's public encapsulation key

        Returns:
            EncapsulationResult containing ciphertext and shared secret
        """
        start_time = time.perf_counter()

        kem = self._get_kem()
        ciphertext, shared_secret = kem.encap_secret(public_key)

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.log_crypto_operation(
            operation="encapsulate",
            algorithm=self._algorithm,
            success=True,
            duration_ms=duration_ms,
        )

        return EncapsulationResult(
            ciphertext=ciphertext,
            shared_secret=shared_secret,
        )

    def decapsulate(self, ciphertext: bytes, secret_key: bytes) -> bytes:
        """Decapsulate a shared secret using a secret key.

        Args:
            ciphertext: The encapsulated ciphertext
            secret_key: The recipient's secret decapsulation key

        Returns:
            The decapsulated shared secret
        """
        start_time = time.perf_counter()

        liboqs_name = "Kyber768" if self._security_level == 768 else "Kyber1024"
        kem = oqs.KeyEncapsulation(liboqs_name, secret_key)
        shared_secret = kem.decap_secret(ciphertext)

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.log_crypto_operation(
            operation="decapsulate",
            algorithm=self._algorithm,
            success=True,
            duration_ms=duration_ms,
        )

        return shared_secret


class HybridEncryptor:
    """Hybrid encryption combining ML-KEM and AES-256-GCM.

    Provides quantum-resistant key exchange with proven symmetric encryption
    for defense in depth against both classical and quantum adversaries.

    Security Model:
        1. ML-KEM encapsulates a shared secret
        2. HKDF derives AES-256 key from shared secret
        3. AES-256-GCM encrypts the plaintext
        4. Both KEM ciphertext and AES ciphertext are returned

    Example:
        >>> encryptor = HybridEncryptor(security_level=768)
        >>> keypair = encryptor.generate_keypair()
        >>> ciphertext = encryptor.encrypt(b"secret message", keypair.public_key)
        >>> plaintext = encryptor.decrypt(ciphertext, keypair.secret_key)
    """

    def __init__(self, security_level: int = PQCSecurityLevel.LEVEL_768) -> None:
        """Initialize hybrid encryptor.

        Args:
            security_level: ML-KEM security level (768 or 1024)
        """
        self._pqc_engine = PQCEngine(security_level)
        self._algorithm = f"HYBRID-{self._pqc_engine.algorithm}-AES256GCM"

    @property
    def algorithm(self) -> str:
        """Get the hybrid algorithm identifier."""
        return self._algorithm

    def generate_keypair(self) -> MLKEMKeyPair:
        """Generate a new key pair for hybrid encryption."""
        return self._pqc_engine.generate_keypair()

    def _derive_aes_key(self, shared_secret: bytes, salt: bytes | None = None) -> bytes:
        """Derive AES-256 key from shared secret using HKDF.

        Args:
            shared_secret: The ML-KEM shared secret
            salt: Optional salt for key derivation

        Returns:
            32-byte AES-256 key
        """
        if salt is None:
            salt = b"\x00" * 32

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=AES_KEY_SIZE // 8,
            salt=salt,
            info=INFO_LABEL,
            backend=default_backend(),
        )
        return hkdf.derive(shared_secret)

    def encrypt(
        self,
        plaintext: bytes,
        public_key: bytes,
        associated_data: bytes | None = None,
    ) -> HybridCiphertext:
        """Encrypt plaintext using hybrid encryption.

        Args:
            plaintext: Data to encrypt
            public_key: Recipient's public key
            associated_data: Optional additional authenticated data

        Returns:
            HybridCiphertext containing encrypted data

        Performance:
            Target: < 100ms for typical payloads
        """
        start_time = time.perf_counter()

        # Step 1: ML-KEM encapsulation
        encap_result = self._pqc_engine.encapsulate(public_key)

        # Step 2: Derive AES key
        aes_key = self._derive_aes_key(encap_result.shared_secret)

        # Step 3: AES-GCM encryption
        nonce = os.urandom(GCM_NONCE_SIZE)
        aesgcm = AESGCM(aes_key)
        aes_ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.log_crypto_operation(
            operation="hybrid_encrypt",
            algorithm=self._algorithm,
            success=True,
            duration_ms=duration_ms,
        )

        return HybridCiphertext(
            kem_ciphertext=encap_result.ciphertext,
            aes_nonce=nonce,
            aes_ciphertext=aes_ciphertext,
            algorithm=self._algorithm,
        )

    def decrypt(
        self,
        ciphertext: HybridCiphertext,
        secret_key: bytes,
        associated_data: bytes | None = None,
    ) -> bytes:
        """Decrypt hybrid ciphertext.

        Args:
            ciphertext: The hybrid ciphertext to decrypt
            secret_key: Recipient's secret key
            associated_data: Optional additional authenticated data

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (authentication failure)
        """
        start_time = time.perf_counter()

        try:
            # Step 1: ML-KEM decapsulation
            shared_secret = self._pqc_engine.decapsulate(
                ciphertext.kem_ciphertext,
                secret_key,
            )

            # Step 2: Derive AES key
            aes_key = self._derive_aes_key(shared_secret)

            # Step 3: AES-GCM decryption
            aesgcm = AESGCM(aes_key)
            plaintext = aesgcm.decrypt(
                ciphertext.aes_nonce,
                ciphertext.aes_ciphertext,
                associated_data,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.log_crypto_operation(
                operation="hybrid_decrypt",
                algorithm=self._algorithm,
                success=True,
                duration_ms=duration_ms,
            )

            return plaintext

        except Exception as e:
            logger.log_crypto_operation(
                operation="hybrid_decrypt",
                algorithm=self._algorithm,
                success=False,
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )
            raise ValueError(f"Decryption failed: {e}") from e


class PQCEngineSimulated:
    """Simulated PQC engine for environments without liboqs.

    This provides API-compatible functionality using classical cryptography
    for testing and development purposes. NOT FOR PRODUCTION USE.

    Warning:
        This implementation does NOT provide quantum resistance.
        Use only for testing when liboqs is unavailable.
    """

    def __init__(self, security_level: int = PQCSecurityLevel.LEVEL_768) -> None:
        """Initialize simulated PQC engine."""
        self._security_level = security_level
        self._algorithm = f"SIMULATED-KEM-{security_level}"

        # Simulated key sizes based on ML-KEM specs
        self._public_key_size = 1184 if security_level == 768 else 1568
        self._secret_key_size = 2400 if security_level == 768 else 3168
        self._ciphertext_size = 1088 if security_level == 768 else 1568

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        return self._algorithm

    @property
    def security_level(self) -> int:
        """Get the security level."""
        return self._security_level

    def generate_keypair(self) -> MLKEMKeyPair:
        """Generate a simulated key pair."""
        # Use random bytes for simulated keys
        public_key = os.urandom(self._public_key_size)
        secret_key = os.urandom(self._secret_key_size)

        return MLKEMKeyPair(
            public_key=public_key,
            secret_key=secret_key,
            algorithm=self._algorithm,
        )

    def encapsulate(self, public_key: bytes) -> EncapsulationResult:
        """Simulate encapsulation using HKDF."""
        # Derive shared secret from public key hash (simulated)
        shared_secret = hashlib.sha256(public_key + os.urandom(32)).digest()
        ciphertext = os.urandom(self._ciphertext_size)

        return EncapsulationResult(
            ciphertext=ciphertext,
            shared_secret=shared_secret,
        )

    def decapsulate(self, ciphertext: bytes, secret_key: bytes) -> bytes:
        """Simulate decapsulation using HKDF."""
        # Derive shared secret from secret key and ciphertext (simulated)
        return hashlib.sha256(secret_key + ciphertext).digest()


def get_pqc_engine(
    security_level: int = PQCSecurityLevel.LEVEL_768,
    allow_simulated: bool = False,
) -> PQCEngine | PQCEngineSimulated:
    """Factory function to get appropriate PQC engine.

    Args:
        security_level: ML-KEM security level (768 or 1024)
        allow_simulated: If True, return simulated engine when liboqs unavailable

    Returns:
        PQCEngine if liboqs available, PQCEngineSimulated if allowed

    Raises:
        RuntimeError: If liboqs unavailable and simulated not allowed
    """
    if LIBOQS_AVAILABLE:
        return PQCEngine(security_level)

    if allow_simulated:
        import warnings
        warnings.warn(
            "Using simulated PQC engine - NOT QUANTUM RESISTANT! "
            "Install liboqs-python for production use.",
            RuntimeWarning,
        )
        return PQCEngineSimulated(security_level)

    raise RuntimeError(
        "liboqs-python is required for PQC operations. "
        "Install with: pip install liboqs-python"
    )
