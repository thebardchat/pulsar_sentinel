"""Blockchain integration module for PULSAR SENTINEL.

Provides:
- Polygon client with Web3.py integration
- Smart contract deployment and interaction
- Immutable event logging to blockchain
"""

from blockchain.polygon_client import PolygonClient, TransactionResult
from blockchain.smart_contract import GovernanceContract, ContractConfig
from blockchain.event_logger import BlockchainEventLogger, MerkleProof

__all__ = [
    "PolygonClient",
    "TransactionResult",
    "GovernanceContract",
    "ContractConfig",
    "BlockchainEventLogger",
    "MerkleProof",
]
