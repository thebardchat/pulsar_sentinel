"""Tests for Post-Quantum Cryptography module.

Tests cover:
- ML-KEM key generation
- Hybrid encryption/decryption
- Legacy AES encryption/decryption
- ECDSA signatures
- ASR generation and verification
"""

import os
import sys
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))


class TestPQCEngineSimulated:
    """Tests for simulated PQC engine (when liboqs not available)."""

    def test_simulated_keypair_generation(self):
        """Test key pair generation with simulated engine."""
        from core.pqc import PQCEngineSimulated, MLKEMKeyPair

        engine = PQCEngineSimulated(security_level=768)
        keypair = engine.generate_keypair()

        assert isinstance(keypair, MLKEMKeyPair)
        assert len(keypair.public_key) == 1184  # ML-KEM-768 public key size
        assert len(keypair.secret_key) == 2400  # ML-KEM-768 secret key size
        assert keypair.algorithm == "SIMULATED-KEM-768"
        assert keypair.key_id is not None

    def test_simulated_keypair_1024(self):
        """Test key pair generation with ML-KEM-1024."""
        from core.pqc import PQCEngineSimulated

        engine = PQCEngineSimulated(security_level=1024)
        keypair = engine.generate_keypair()

        assert len(keypair.public_key) == 1568  # ML-KEM-1024 public key size
        assert len(keypair.secret_key) == 3168  # ML-KEM-1024 secret key size

    def test_simulated_encapsulation(self):
        """Test encapsulation with simulated engine."""
        from core.pqc import PQCEngineSimulated

        engine = PQCEngineSimulated()
        keypair = engine.generate_keypair()

        result = engine.encapsulate(keypair.public_key)

        assert len(result.shared_secret) == 32  # SHA-256 output
        assert len(result.ciphertext) == 1088  # ML-KEM-768 ciphertext size

    def test_simulated_decapsulation(self):
        """Test decapsulation with simulated engine."""
        from core.pqc import PQCEngineSimulated

        engine = PQCEngineSimulated()
        keypair = engine.generate_keypair()
        result = engine.encapsulate(keypair.public_key)

        # Note: Simulated decapsulation doesn't match encapsulation
        # This is expected - simulated engine is for API testing only
        decap_secret = engine.decapsulate(result.ciphertext, keypair.secret_key)

        assert len(decap_secret) == 32


class TestHybridCiphertext:
    """Tests for hybrid ciphertext serialization."""

    def test_ciphertext_serialization(self):
        """Test HybridCiphertext to_bytes and from_bytes."""
        from core.pqc import HybridCiphertext

        original = HybridCiphertext(
            kem_ciphertext=b"kem_cipher_data_here",
            aes_nonce=b"123456789012",  # 12 bytes
            aes_ciphertext=b"encrypted_data_here",
            algorithm="TEST-ALGORITHM",
        )

        serialized = original.to_bytes()
        restored = HybridCiphertext.from_bytes(serialized, "TEST-ALGORITHM")

        assert restored.kem_ciphertext == original.kem_ciphertext
        assert restored.aes_nonce == original.aes_nonce
        assert restored.aes_ciphertext == original.aes_ciphertext

    def test_ciphertext_roundtrip(self):
        """Test full serialization roundtrip."""
        from core.pqc import HybridCiphertext

        kem_ct = os.urandom(1088)
        nonce = os.urandom(12)
        aes_ct = os.urandom(100)

        original = HybridCiphertext(
            kem_ciphertext=kem_ct,
            aes_nonce=nonce,
            aes_ciphertext=aes_ct,
            algorithm="HYBRID-ML-KEM-768-AES256GCM",
        )

        serialized = original.to_bytes()
        restored = HybridCiphertext.from_bytes(serialized, original.algorithm)

        assert restored.kem_ciphertext == kem_ct
        assert restored.aes_nonce == nonce
        assert restored.aes_ciphertext == aes_ct


class TestLegacyCrypto:
    """Tests for legacy AES-256-CBC encryption."""

    def test_key_derivation(self):
        """Test PBKDF2 key derivation."""
        from core.legacy import LegacyCrypto

        crypto = LegacyCrypto()
        password = b"test_password_123"

        key1, salt1 = crypto.derive_key(password)
        key2, salt2 = crypto.derive_key(password, salt1)

        # Same password + salt should give same key
        assert key1 == key2
        assert salt1 == salt2
        assert len(key1) == 64  # 32 bytes AES + 32 bytes HMAC

    def test_different_salts_different_keys(self):
        """Test that different salts produce different keys."""
        from core.legacy import LegacyCrypto

        crypto = LegacyCrypto()
        password = b"test_password"

        key1, salt1 = crypto.derive_key(password)
        key2, salt2 = crypto.derive_key(password)

        # Different salts should give different keys
        assert salt1 != salt2
        assert key1 != key2

    def test_aes_encrypt_decrypt(self):
        """Test AES encryption and decryption roundtrip."""
        from core.legacy import LegacyCrypto

        crypto = LegacyCrypto()
        plaintext = b"This is a secret message for testing AES encryption."
        password = b"secure_password"

        key, salt = crypto.derive_key(password)
        ciphertext = crypto.encrypt(plaintext, key, salt)

        # Decrypt
        decrypted = crypto.decrypt(ciphertext, key)

        assert decrypted == plaintext

    def test_aes_different_messages(self):
        """Test that different messages produce different ciphertexts."""
        from core.legacy import LegacyCrypto

        crypto = LegacyCrypto()
        password = b"password"
        key, salt = crypto.derive_key(password)

        msg1 = b"Message one"
        msg2 = b"Message two"

        ct1 = crypto.encrypt(msg1, key, salt)
        ct2 = crypto.encrypt(msg2, key, salt)

        # Ciphertexts should be different
        assert ct1.ciphertext != ct2.ciphertext

        # Both should decrypt correctly
        assert crypto.decrypt(ct1, key) == msg1
        assert crypto.decrypt(ct2, key) == msg2

    def test_aes_hmac_verification_failure(self):
        """Test that tampered ciphertext fails HMAC verification."""
        from core.legacy import LegacyCrypto, AESCiphertext

        crypto = LegacyCrypto()
        plaintext = b"Secret data"
        key, salt = crypto.derive_key(b"password")

        ciphertext = crypto.encrypt(plaintext, key, salt)

        # Tamper with ciphertext
        tampered = AESCiphertext(
            salt=ciphertext.salt,
            iv=ciphertext.iv,
            ciphertext=b"tampered_data" + ciphertext.ciphertext[13:],
            hmac_tag=ciphertext.hmac_tag,
        )

        with pytest.raises(ValueError, match="HMAC verification failed"):
            crypto.decrypt(tampered, key)

    def test_aes_ciphertext_serialization(self):
        """Test AESCiphertext serialization."""
        from core.legacy import AESCiphertext

        original = AESCiphertext(
            salt=os.urandom(32),
            iv=os.urandom(16),
            ciphertext=os.urandom(64),
            hmac_tag=os.urandom(32),
        )

        serialized = original.to_bytes()
        restored = AESCiphertext.from_bytes(serialized)

        assert restored.salt == original.salt
        assert restored.iv == original.iv
        assert restored.ciphertext == original.ciphertext
        assert restored.hmac_tag == original.hmac_tag


class TestECDSA:
    """Tests for ECDSA signatures."""

    def test_ecdsa_key_generation(self):
        """Test ECDSA key pair generation."""
        from core.legacy import ECDSASigner

        signer = ECDSASigner.generate()
        keypair = signer.get_keypair()

        assert len(keypair.private_key) == 32
        assert len(keypair.public_key) == 33  # Compressed
        assert keypair.address.startswith("0x")
        assert len(keypair.address) == 42

    def test_ecdsa_sign_verify(self):
        """Test ECDSA signature and verification."""
        from core.legacy import ECDSASigner
        import hashlib

        signer = ECDSASigner.generate()
        message = b"Test message to sign"
        message_hash = hashlib.sha256(message).digest()

        signature = signer.sign(message_hash)

        assert len(signature.r) == 32
        assert len(signature.s) == 32
        assert signature.v in (27, 28)

        # Verify signature
        is_valid = ECDSASigner.verify(
            message_hash,
            signature,
            signer.public_key_bytes,
        )
        assert is_valid

    def test_ecdsa_invalid_signature(self):
        """Test that invalid signatures fail verification."""
        from core.legacy import ECDSASigner, ECDSASignature
        import hashlib

        signer = ECDSASigner.generate()
        message_hash = hashlib.sha256(b"Test").digest()

        signature = signer.sign(message_hash)

        # Create invalid signature
        invalid_sig = ECDSASignature(
            r=os.urandom(32),
            s=signature.s,
            v=signature.v,
        )

        is_valid = ECDSASigner.verify(
            message_hash,
            invalid_sig,
            signer.public_key_bytes,
        )
        assert not is_valid

    def test_ecdsa_from_private_key(self):
        """Test creating signer from private key bytes."""
        from core.legacy import ECDSASigner

        # Generate random private key
        private_key = os.urandom(32)
        signer = ECDSASigner.from_private_key(private_key)

        keypair = signer.get_keypair()
        assert keypair.private_key == private_key


class TestASREngine:
    """Tests for Agent State Record engine."""

    def test_asr_creation(self, tmp_path):
        """Test ASR creation."""
        from core.asr_engine import ASREngine, ThreatLevel, PQCStatus

        engine = ASREngine(storage_path=tmp_path)

        asr = engine.create_asr(
            agent_id="test_user_123",
            action="test_action",
            threat_level=ThreatLevel.INFO,
            pqc_status=PQCStatus.SAFE,
            metadata={"test_key": "test_value"},
        )

        assert asr.asr_id.startswith("asr_")
        assert asr.agent_id == "test_user_123"
        assert asr.action == "test_action"
        assert asr.threat_level == 1
        assert asr.pqc_status == "safe"
        assert asr.metadata["test_key"] == "test_value"
        assert asr.signature != ""

    def test_asr_signature_verification(self, tmp_path):
        """Test ASR signature verification."""
        from core.asr_engine import ASREngine, ThreatLevel

        engine = ASREngine(storage_path=tmp_path)

        asr = engine.create_asr(
            agent_id="user",
            action="action",
            threat_level=ThreatLevel.WARNING,
        )

        assert asr.verify_signature()

        # Tamper with ASR
        asr.action = "tampered_action"
        assert not asr.verify_signature()

    def test_asr_storage_and_retrieval(self, tmp_path):
        """Test ASR storage and retrieval."""
        from core.asr_engine import ASREngine, ThreatLevel

        engine = ASREngine(storage_path=tmp_path)

        asr = engine.create_asr(
            agent_id="storage_test_user",
            action="storage_test",
            threat_level=ThreatLevel.CAUTION,
        )

        # Store ASR
        file_path = engine.store_asr(asr)
        assert file_path.exists()

        # Retrieve ASR
        retrieved = engine.load_asr(asr.asr_id)
        assert retrieved is not None
        assert retrieved.asr_id == asr.asr_id
        assert retrieved.agent_id == asr.agent_id
        assert retrieved.action == asr.action

    def test_asr_list_by_agent(self, tmp_path):
        """Test listing ASRs by agent."""
        from core.asr_engine import ASREngine, ThreatLevel

        engine = ASREngine(storage_path=tmp_path)

        # Create multiple ASRs for same agent
        for i in range(3):
            asr = engine.create_asr(
                agent_id="list_test_agent",
                action=f"action_{i}",
                threat_level=ThreatLevel.INFO,
            )
            engine.store_asr(asr)

        # Create ASR for different agent
        other_asr = engine.create_asr(
            agent_id="other_agent",
            action="other_action",
            threat_level=ThreatLevel.INFO,
        )
        engine.store_asr(other_asr)

        # List ASRs
        records = engine.list_asr_by_agent("list_test_agent")
        assert len(records) == 3

    def test_asr_serialization(self, tmp_path):
        """Test ASR JSON serialization."""
        from core.asr_engine import ASREngine, AgentStateRecord, ThreatLevel

        engine = ASREngine(storage_path=tmp_path)

        asr = engine.create_asr(
            agent_id="serial_test",
            action="test",
            threat_level=ThreatLevel.ALERT,
            metadata={"key": "value"},
        )

        json_str = asr.to_json()
        restored = AgentStateRecord.from_json(json_str)

        assert restored.asr_id == asr.asr_id
        assert restored.agent_id == asr.agent_id
        assert restored.threat_level == asr.threat_level
        assert restored.metadata == asr.metadata

    def test_asr_batch_and_merkle_root(self, tmp_path):
        """Test ASR batching and Merkle root calculation."""
        from core.asr_engine import ASREngine, ThreatLevel

        engine = ASREngine(storage_path=tmp_path)

        # Create and add ASRs to batch
        asrs = []
        for i in range(5):
            asr = engine.create_asr(
                agent_id=f"batch_user_{i}",
                action=f"batch_action_{i}",
                threat_level=ThreatLevel.INFO,
            )
            asrs.append(asr)
            engine.add_to_batch(asr)

        # Flush batch
        batch = engine.flush_batch()
        assert batch is not None
        assert len(batch.records) == 5
        assert batch.merkle_root != ""

        # Verify Merkle root is consistent
        merkle_root = engine._compute_merkle_root(asrs)
        assert merkle_root == batch.merkle_root


class TestPQCStatusDetermination:
    """Tests for PQC status determination."""

    def test_quantum_safe_algorithms(self):
        """Test that quantum-safe algorithms return SAFE status."""
        from core.asr_engine import determine_pqc_status, PQCStatus

        assert determine_pqc_status("ML-KEM-768") == PQCStatus.SAFE
        assert determine_pqc_status("ML-KEM-1024") == PQCStatus.SAFE
        assert determine_pqc_status("HYBRID-ML-KEM-768-AES256GCM") == PQCStatus.SAFE

    def test_classical_algorithms(self):
        """Test that classical algorithms return WARNING status."""
        from core.asr_engine import determine_pqc_status, PQCStatus

        assert determine_pqc_status("AES-256-GCM") == PQCStatus.WARNING
        assert determine_pqc_status("ECDSA-secp256k1") == PQCStatus.WARNING
        assert determine_pqc_status("RSA-2048") == PQCStatus.WARNING

    def test_unknown_algorithms(self):
        """Test that unknown algorithms return CRITICAL status."""
        from core.asr_engine import determine_pqc_status, PQCStatus

        assert determine_pqc_status("UNKNOWN-CIPHER") == PQCStatus.CRITICAL

    def test_old_quantum_safe_keys(self):
        """Test that old quantum-safe keys get WARNING status."""
        from core.asr_engine import determine_pqc_status, PQCStatus

        # Keys older than 365 days should get WARNING even if quantum-safe
        assert determine_pqc_status("ML-KEM-768", key_age_days=400) == PQCStatus.WARNING
