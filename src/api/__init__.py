"""API module for PULSAR SENTINEL.

Provides:
- FastAPI REST server
- MetaMask wallet-based authentication
- Rate-limited API routes
"""

from api.server import create_app, run_server
from api.auth import MetaMaskAuth, WalletSession
from api.routes import router

__all__ = [
    "create_app",
    "run_server",
    "MetaMaskAuth",
    "WalletSession",
    "router",
]
