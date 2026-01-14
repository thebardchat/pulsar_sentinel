"""FastAPI Server for PULSAR SENTINEL.

Main application server providing REST API endpoints for:
- Post-quantum and legacy cryptographic operations
- Wallet-based authentication
- Agent State Record management
- Governance and access control
- Cyberpunk UI Portal for PULSAR ecosystem

Run with: uvicorn api.server:app --host 0.0.0.0 --port 8000
"""

import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import router, init_routes
from api.auth import MetaMaskAuth
from api.ui_routes import ui_router
from core.asr_engine import ASREngine
from governance.access_control import AccessController
from governance.pts_calculator import PTSCalculator
from governance.rules_engine import RulesEngine
from config.settings import get_settings
from config.logging import setup_logging, get_logger

# Application metadata
APP_TITLE = "PULSAR SENTINEL"
APP_DESCRIPTION = """
Post-Quantum Cryptography Security Framework for Angel Cloud

## Features

- **ML-KEM Hybrid Encryption**: Quantum-resistant key encapsulation with AES-256-GCM
- **Legacy Cryptography**: AES-256-CBC for backwards compatibility
- **Wallet Authentication**: MetaMask-based passwordless authentication
- **Agent State Records**: Immutable security event logging
- **Governance Engine**: Self-governance rules and threat scoring

## Authentication

All endpoints (except /health and /auth/*) require JWT authentication.

1. Request a nonce: `POST /auth/nonce`
2. Sign the message with MetaMask
3. Submit signature: `POST /auth/verify`
4. Use returned token in `Authorization: Bearer <token>` header

## Rate Limiting

- Default: 5 requests/minute
- Sentinel Tier: 10 requests/minute
- Guild Tier: 100 requests/minute
"""
APP_VERSION = "1.0.0"

logger = get_logger("server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting PULSAR SENTINEL server")
    setup_logging()

    # Initialize services
    auth = MetaMaskAuth()
    access_controller = AccessController()
    asr_engine = ASREngine()
    pts_calculator = PTSCalculator()
    rules_engine = RulesEngine()

    # Initialize routes with dependencies
    init_routes(
        auth=auth,
        access_controller=access_controller,
        asr_engine=asr_engine,
        pts_calculator=pts_calculator,
        rules_engine=rules_engine,
    )

    # Store in app state for access
    app.state.auth = auth
    app.state.access_controller = access_controller
    app.state.asr_engine = asr_engine
    app.state.pts_calculator = pts_calculator
    app.state.rules_engine = rules_engine

    logger.info("Services initialized")

    yield

    # Shutdown
    logger.info("Shutting down PULSAR SENTINEL server")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router, prefix="/api/v1")

    # Include UI API routes
    app.include_router(ui_router, prefix="/api/v1")

    # Setup static files and templates
    project_root = Path(__file__).parent.parent.parent
    ui_dir = project_root / "ui"
    static_dir = ui_dir / "static"
    templates_dir = ui_dir / "templates"

    # Mount static files if directory exists
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Setup templates
    templates = None
    if templates_dir.exists():
        templates = Jinja2Templates(directory=str(templates_dir))

    # UI Page Routes
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        if templates:
            return templates.TemplateResponse("index.html", {"request": request})
        return HTMLResponse("<h1>PULSAR SENTINEL</h1><p>UI templates not found. API available at /docs</p>")

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if templates:
            return templates.TemplateResponse("login.html", {"request": request})
        return HTMLResponse("Login page - templates not found")

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page(request: Request):
        if templates:
            return templates.TemplateResponse("dashboard.html", {"request": request})
        return HTMLResponse("Dashboard - templates not found")

    @app.get("/wallet", response_class=HTMLResponse)
    async def wallet_page(request: Request):
        if templates:
            return templates.TemplateResponse("wallet.html", {"request": request})
        return HTMLResponse("Wallet - templates not found")

    @app.get("/mining", response_class=HTMLResponse)
    async def mining_page(request: Request):
        if templates:
            return templates.TemplateResponse("mining.html", {"request": request})
        return HTMLResponse("Mining - templates not found")

    @app.get("/marketplace", response_class=HTMLResponse)
    async def marketplace_page(request: Request):
        if templates:
            return templates.TemplateResponse("marketplace.html", {"request": request})
        return HTMLResponse("Marketplace - templates not found")

    @app.get("/shanebrain", response_class=HTMLResponse)
    async def shanebrain_page(request: Request):
        if templates:
            return templates.TemplateResponse("shanebrain.html", {"request": request})
        return HTMLResponse("SHANEBRAIN AI - templates not found")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": APP_TITLE,
            "version": APP_VERSION,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Create application instance
app = create_app()


def run_server():
    """Run the server using uvicorn."""
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level="info",
    )


def main():
    """Main entry point."""
    run_server()


if __name__ == "__main__":
    main()
