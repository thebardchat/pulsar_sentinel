"""API module for PULSAR SENTINEL.

Provides:
- FastAPI REST server
- MetaMask wallet-based authentication
- Rate-limited API routes
"""

from api.auth import MetaMaskAuth, WalletSession
from api.routes import router
from api.server import create_app, run_server

__all__ = [
    "MetaMaskAuth",
    "WalletSession",
    "create_app",
    "router",
    "run_server",
]
