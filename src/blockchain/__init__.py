"""Blockchain integration module for PULSAR SENTINEL.

Provides:
- Polygon client with Web3.py integration
- Smart contract deployment and interaction
- Immutable event logging to blockchain
"""

from blockchain.event_logger import BlockchainEventLogger, MerkleProof
from blockchain.polygon_client import PolygonClient, TransactionResult
from blockchain.smart_contract import ContractConfig, GovernanceContract

__all__ = [
    "BlockchainEventLogger",
    "ContractConfig",
    "GovernanceContract",
    "MerkleProof",
    "PolygonClient",
    "TransactionResult",
]
