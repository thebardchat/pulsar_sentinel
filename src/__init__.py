"""PULSAR SENTINEL - Post-Quantum Cryptography Security Framework.

A production-grade blockchain-integrated security layer for the Angel Cloud ecosystem.
Provides ML-KEM based post-quantum cryptography, hybrid encryption, and immutable
Agent State Recording (ASR) on the Polygon blockchain.

Main Components:
- core: PQC engine, legacy cryptography, ASR generation
- blockchain: Polygon integration, smart contracts, event logging
- governance: Self-governance rules, threat scoring, access control
- api: FastAPI REST server with MetaMask authentication
"""

__version__ = "1.0.0"
__author__ = "Angel Cloud"
__license__ = "MIT"

from core.pqc import PQCEngine, HybridEncryptor
from core.legacy import LegacyCrypto, ECDSASigner
from core.asr_engine import ASREngine, AgentStateRecord

__all__ = [
    "PQCEngine",
    "HybridEncryptor",
    "LegacyCrypto",
    "ECDSASigner",
    "ASREngine",
    "AgentStateRecord",
]
