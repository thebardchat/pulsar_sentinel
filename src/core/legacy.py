"""Legacy Cryptography Module for PULSAR SENTINEL (Tier 2).

Provides classical cryptographic primitives for backwards compatibility
and environments where PQC is not required:

- AES-256-CBC with HMAC-SHA256 for authenticated encryption
- ECDSA (secp256k1) for Polygon-compatible signatures
- TLS 1.3 configuration and certificate management

Security Note:
    These algorithms are NOT quantum-resistant. Use PQC module for
    long-term security against quantum adversaries (2035+).
"""

import os
import time
import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from config.constants import AES_KEY_SIZE, AES_BLOCK_SIZE, HMAC_DIGEST_SIZE
from config.logging import SecurityEventLogger

# Constants
AES_IV_SIZE: Final[int] = 16  # 128 bits
SALT_SIZE: Final[int] = 32
PBKDF2_ITERATIONS: Final[int] = 600_000  # OWASP recommendation 2024
ECDSA_CURVE: Final[str] = "secp256k1"

logger = SecurityEventLogger("legacy")


@dataclass
class AESCiphertext:
    """AES-256-CBC ciphertext with HMAC authentication.

    Format: [salt][iv][ciphertext][hmac]

    Attributes:
        salt: Random salt for key derivation
        iv: Initialization vector
        ciphertext: Encrypted data
        hmac_tag: HMAC-SHA256 authentication tag
    """
    salt: bytes
    iv: bytes
    ciphertext: bytes
    hmac_tag: bytes

    def to_bytes(self) -> bytes:
        """Serialize to bytes format."""
        return self.salt + self.iv + self.ciphertext + self.hmac_tag

    @classmethod
    def from_bytes(cls, data: bytes) -> "AESCiphertext":
        """Deserialize from bytes format."""
        salt = data[:SALT_SIZE]
        iv = data[SALT_SIZE:SALT_SIZE + AES_IV_SIZE]
        hmac_tag = data[-HMAC_DIGEST_SIZE:]
        ciphertext = data[SALT_SIZE + AES_IV_SIZE:-HMAC_DIGEST_SIZE]
        return cls(salt=salt, iv=iv, ciphertext=ciphertext, hmac_tag=hmac_tag)


@dataclass
class ECDSAKeyPair:
    """ECDSA secp256k1 key pair for Polygon compatibility.

    Attributes:
        private_key: The private signing key (32 bytes)
        public_key: The public verification key (compressed, 33 bytes)
        address: Ethereum-style address derived from public key
        created_at: Key pair creation timestamp
    """
    private_key: bytes
    public_key: bytes
    address: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_private_key(cls, private_key: bytes) -> "ECDSAKeyPair":
        """Create key pair from private key bytes."""
        # Load private key
        private_key_obj = ec.derive_private_key(
            int.from_bytes(private_key, "big"),
            ec.SECP256K1(),
            default_backend(),
        )

        # Get public key
        public_key_obj = private_key_obj.public_key()
        public_key_bytes = public_key_obj.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint,
        )

        # Derive Ethereum-style address
        uncompressed = public_key_obj.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        # Hash uncompressed public key (without 0x04 prefix)
        address_hash = hashlib.sha3_256(uncompressed[1:]).digest()
        address = "0x" + address_hash[-20:].hex()

        return cls(
            private_key=private_key,
            public_key=public_key_bytes,
            address=address,
        )


@dataclass
class ECDSASignature:
    """ECDSA signature with recovery parameter.

    Attributes:
        r: Signature r component
        s: Signature s component
        v: Recovery parameter (27 or 28 for Ethereum compatibility)
    """
    r: bytes
    s: bytes
    v: int

    def to_bytes(self) -> bytes:
        """Serialize to 65-byte format (r + s + v)."""
        return self.r + self.s + bytes([self.v])

    @classmethod
    def from_bytes(cls, data: bytes) -> "ECDSASignature":
        """Deserialize from 65-byte format."""
        if len(data) != 65:
            raise ValueError("Signature must be 65 bytes")
        return cls(r=data[:32], s=data[32:64], v=data[64])


class LegacyCrypto:
    """Legacy AES-256-CBC encryption with HMAC authentication.

    Provides authenticated encryption using AES-256-CBC with HMAC-SHA256
    (Encrypt-then-MAC construction).

    Security:
        - AES-256-CBC: 256-bit security against classical attacks
        - HMAC-SHA256: Authentication prevents tampering
        - PBKDF2: Key derivation with 600,000 iterations
        - Random salt and IV per encryption

    Example:
        >>> crypto = LegacyCrypto()
        >>> key = crypto.derive_key(b"password", salt=os.urandom(32))
        >>> ciphertext = crypto.encrypt(b"secret", key)
        >>> plaintext = crypto.decrypt(ciphertext, key)
    """

    def __init__(self) -> None:
        """Initialize legacy crypto engine."""
        self._algorithm = "AES-256-CBC-HMAC-SHA256"

    @property
    def algorithm(self) -> str:
        """Get the algorithm identifier."""
        return self._algorithm

    def derive_key(
        self,
        password: bytes,
        salt: bytes | None = None,
        iterations: int = PBKDF2_ITERATIONS,
    ) -> tuple[bytes, bytes]:
        """Derive encryption key from password using PBKDF2.

        Args:
            password: Password or passphrase
            salt: Optional salt (random if not provided)
            iterations: PBKDF2 iteration count

        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = os.urandom(SALT_SIZE)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=AES_KEY_SIZE // 8 + HMAC_DIGEST_SIZE,  # AES key + HMAC key
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        derived = kdf.derive(password)

        return derived, salt

    def _split_keys(self, derived: bytes) -> tuple[bytes, bytes]:
        """Split derived key into encryption and HMAC keys."""
        enc_key = derived[:AES_KEY_SIZE // 8]
        mac_key = derived[AES_KEY_SIZE // 8:]
        return enc_key, mac_key

    def encrypt(
        self,
        plaintext: bytes,
        key: bytes,
        salt: bytes | None = None,
    ) -> AESCiphertext:
        """Encrypt plaintext using AES-256-CBC with HMAC.

        Args:
            plaintext: Data to encrypt
            key: Derived key (64 bytes: 32 AES + 32 HMAC)
            salt: Salt used for key derivation

        Returns:
            AESCiphertext with encrypted data and authentication tag
        """
        start_time = time.perf_counter()

        if salt is None:
            salt = os.urandom(SALT_SIZE)

        enc_key, mac_key = self._split_keys(key)

        # Generate random IV
        iv = os.urandom(AES_IV_SIZE)

        # Pad plaintext to block size
        padder = PKCS7(AES_BLOCK_SIZE).padder()
        padded = padder.update(plaintext) + padder.finalize()

        # Encrypt with AES-CBC
        cipher = Cipher(
            algorithms.AES(enc_key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        # Compute HMAC over salt + iv + ciphertext
        mac_data = salt + iv + ciphertext
        hmac_tag = hmac.new(mac_key, mac_data, hashlib.sha256).digest()

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.log_crypto_operation(
            operation="aes_encrypt",
            algorithm=self._algorithm,
            success=True,
            duration_ms=duration_ms,
        )

        return AESCiphertext(
            salt=salt,
            iv=iv,
            ciphertext=ciphertext,
            hmac_tag=hmac_tag,
        )

    def decrypt(self, ciphertext: AESCiphertext, key: bytes) -> bytes:
        """Decrypt AES-256-CBC ciphertext with HMAC verification.

        Args:
            ciphertext: AESCiphertext to decrypt
            key: Derived key (64 bytes: 32 AES + 32 HMAC)

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If HMAC verification fails
        """
        start_time = time.perf_counter()

        enc_key, mac_key = self._split_keys(key)

        # Verify HMAC first (constant-time comparison)
        mac_data = ciphertext.salt + ciphertext.iv + ciphertext.ciphertext
        expected_tag = hmac.new(mac_key, mac_data, hashlib.sha256).digest()

        if not hmac.compare_digest(ciphertext.hmac_tag, expected_tag):
            logger.log_crypto_operation(
                operation="aes_decrypt",
                algorithm=self._algorithm,
                success=False,
            )
            raise ValueError("HMAC verification failed - data may be tampered")

        # Decrypt with AES-CBC
        cipher = Cipher(
            algorithms.AES(enc_key),
            modes.CBC(ciphertext.iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext.ciphertext) + decryptor.finalize()

        # Remove padding
        unpadder = PKCS7(AES_BLOCK_SIZE).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.log_crypto_operation(
            operation="aes_decrypt",
            algorithm=self._algorithm,
            success=True,
            duration_ms=duration_ms,
        )

        return plaintext


class ECDSASigner:
    """ECDSA secp256k1 signer for Polygon-compatible signatures.

    Provides digital signatures compatible with Ethereum/Polygon
    using the secp256k1 curve.

    Example:
        >>> signer = ECDSASigner.from_private_key(private_key_bytes)
        >>> signature = signer.sign(message_hash)
        >>> is_valid = ECDSASigner.verify(message_hash, signature, public_key)
    """

    def __init__(self, private_key: ec.EllipticCurvePrivateKey) -> None:
        """Initialize ECDSA signer with private key.

        Args:
            private_key: The ECDSA private key object
        """
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @classmethod
    def from_private_key(cls, private_key_bytes: bytes) -> "ECDSASigner":
        """Create signer from private key bytes.

        Args:
            private_key_bytes: 32-byte private key

        Returns:
            ECDSASigner instance
        """
        private_key = ec.derive_private_key(
            int.from_bytes(private_key_bytes, "big"),
            ec.SECP256K1(),
            default_backend(),
        )
        return cls(private_key)

    @classmethod
    def generate(cls) -> "ECDSASigner":
        """Generate a new ECDSA key pair.

        Returns:
            ECDSASigner instance with new key pair
        """
        private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
        return cls(private_key)

    def get_keypair(self) -> ECDSAKeyPair:
        """Get the key pair associated with this signer."""
        private_numbers = self._private_key.private_numbers()
        private_key_bytes = private_numbers.private_value.to_bytes(32, "big")
        return ECDSAKeyPair.from_private_key(private_key_bytes)

    @property
    def address(self) -> str:
        """Get the Ethereum-style address."""
        return self.get_keypair().address

    @property
    def public_key_bytes(self) -> bytes:
        """Get the public key as compressed bytes."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint,
        )

    def sign(self, message_hash: bytes) -> ECDSASignature:
        """Sign a 32-byte message hash.

        Args:
            message_hash: 32-byte hash of the message to sign

        Returns:
            ECDSASignature with r, s, v components
        """
        start_time = time.perf_counter()

        if len(message_hash) != 32:
            raise ValueError("Message hash must be 32 bytes")

        # Sign using ECDSA
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

        signature_der = self._private_key.sign(
            message_hash,
            ec.ECDSA(hashes.SHA256()),
        )

        # Decode DER signature to r, s
        r, s = decode_dss_signature(signature_der)

        # Normalize s to low-S form (BIP-62)
        order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        if s > order // 2:
            s = order - s

        r_bytes = r.to_bytes(32, "big")
        s_bytes = s.to_bytes(32, "big")

        # Calculate recovery parameter (simplified - may need refinement)
        v = 27  # Default, would need proper recovery calculation for production

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.log_crypto_operation(
            operation="ecdsa_sign",
            algorithm="ECDSA-secp256k1",
            success=True,
            duration_ms=duration_ms,
        )

        return ECDSASignature(r=r_bytes, s=s_bytes, v=v)

    @staticmethod
    def verify(
        message_hash: bytes,
        signature: ECDSASignature,
        public_key: bytes,
    ) -> bool:
        """Verify an ECDSA signature.

        Args:
            message_hash: 32-byte hash of the signed message
            signature: The signature to verify
            public_key: The signer's public key (compressed)

        Returns:
            True if signature is valid, False otherwise
        """
        start_time = time.perf_counter()

        try:
            # Load public key
            public_key_obj = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256K1(),
                public_key,
            )

            # Encode signature to DER format
            from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

            r = int.from_bytes(signature.r, "big")
            s = int.from_bytes(signature.s, "big")
            signature_der = encode_dss_signature(r, s)

            # Verify signature
            public_key_obj.verify(
                signature_der,
                message_hash,
                ec.ECDSA(hashes.SHA256()),
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.log_crypto_operation(
                operation="ecdsa_verify",
                algorithm="ECDSA-secp256k1",
                success=True,
                duration_ms=duration_ms,
            )

            return True

        except InvalidSignature:
            logger.log_crypto_operation(
                operation="ecdsa_verify",
                algorithm="ECDSA-secp256k1",
                success=False,
            )
            return False


class TLSManager:
    """TLS 1.3 configuration manager.

    Provides configuration for enforcing TLS 1.3 on all transport
    connections and certificate pinning for API endpoints.
    """

    # Recommended TLS 1.3 cipher suites
    TLS13_CIPHERS: Final[list[str]] = [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256",
    ]

    def __init__(self) -> None:
        """Initialize TLS manager."""
        self._pinned_certs: dict[str, bytes] = {}

    def pin_certificate(self, hostname: str, cert_hash: bytes) -> None:
        """Pin a certificate hash for a hostname.

        Args:
            hostname: The hostname to pin
            cert_hash: SHA-256 hash of the certificate
        """
        self._pinned_certs[hostname] = cert_hash

    def verify_pin(self, hostname: str, cert_hash: bytes) -> bool:
        """Verify a certificate against pinned hash.

        Args:
            hostname: The hostname being verified
            cert_hash: SHA-256 hash of the presented certificate

        Returns:
            True if certificate matches pin or no pin exists
        """
        if hostname not in self._pinned_certs:
            return True  # No pin set, allow

        return hmac.compare_digest(self._pinned_certs[hostname], cert_hash)

    @staticmethod
    def get_ssl_context():
        """Get an SSL context configured for TLS 1.3.

        Returns:
            ssl.SSLContext configured for TLS 1.3
        """
        import ssl

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        ctx.maximum_version = ssl.TLSVersion.TLSv1_3

        # Set recommended ciphers
        ctx.set_ciphers(":".join(TLSManager.TLS13_CIPHERS))

        return ctx

    @staticmethod
    def hash_certificate(cert_der: bytes) -> bytes:
        """Compute SHA-256 hash of a certificate.

        Args:
            cert_der: DER-encoded certificate

        Returns:
            32-byte SHA-256 hash
        """
        return hashlib.sha256(cert_der).digest()
