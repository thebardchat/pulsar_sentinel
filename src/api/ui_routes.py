"""
PULSAR SENTINEL - UI API Routes
Backend endpoints for the Cyberpunk UI portal
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import os

from api.auth import get_current_user, WalletSession


# Router for UI endpoints
ui_router = APIRouter(prefix="/ui", tags=["UI"])


# ============================================================================
# Models
# ============================================================================

class DeploymentType(str, Enum):
    SENTINEL = "sentinel"
    MINING = "mining"
    VALIDATOR = "validator"


class DeploymentStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MINING = "mining"
    STARTING = "starting"
    STOPPING = "stopping"


class DeploymentCreate(BaseModel):
    """Request model for creating a new deployment"""
    name: str = Field(..., min_length=3, max_length=50)
    type: DeploymentType = DeploymentType.SENTINEL
    security_level: int = Field(default=768, ge=768, le=1024)
    auto_update: bool = True


class Deployment(BaseModel):
    """Deployment response model"""
    id: str
    name: str
    type: DeploymentType
    status: DeploymentStatus
    security_level: int
    created_at: datetime
    uptime_seconds: int
    hashrate: Optional[float] = None
    memory_mb: float
    requests_per_min: int


class WalletBalance(BaseModel):
    """Wallet balance response"""
    pls: float
    matic: float
    staked: float
    rewards: float
    usd_value: float


class Transaction(BaseModel):
    """Transaction model"""
    id: str
    type: str
    amount: float
    token: str
    from_address: Optional[str]
    to_address: Optional[str]
    timestamp: datetime
    status: str
    tx_hash: Optional[str]


class MiningStats(BaseModel):
    """Mining statistics"""
    hashrate: float
    valid_shares: int
    rejected_shares: int
    today_earnings: float
    total_mined: float
    blocks_found: int
    is_active: bool


class NFTItem(BaseModel):
    """NFT/MINT item model"""
    id: str
    name: str
    collection: str
    category: str
    price: float
    owner: str
    creator: str
    image_url: Optional[str]
    pqc_signed: bool
    rarity: str
    likes: int
    created_at: datetime


class AIMessage(BaseModel):
    """AI chat message"""
    message: str
    context: Optional[str] = None


class AIResponse(BaseModel):
    """AI response model"""
    response: str
    confidence: float
    suggestions: List[str]


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@ui_router.get("/dashboard/stats")
async def get_dashboard_stats(
    user: WalletSession = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get dashboard statistics for the authenticated user"""
    return {
        "security_score": 98.5,
        "encrypted_today": 1247,
        "pulsar_balance": 2450.00,
        "pts_score": 32,
        "pts_tier": "safe",
        "pts_factors": {
            "quantum_risk": 2,
            "access_violations": 18,
            "rate_limit_violations": 8,
            "signature_failures": 4
        },
        "pqc_status": {
            "level": "ML-KEM-768",
            "nist_level": 3,
            "operations_today": 14247,
            "vulnerabilities": 0
        }
    }


# ============================================================================
# Deployment Endpoints
# ============================================================================

@ui_router.get("/deployments")
async def list_deployments(
    user: WalletSession = Depends(get_current_user)
) -> List[Deployment]:
    """List all deployments for the authenticated user"""
    # In production, fetch from database
    return [
        Deployment(
            id="sentinel-node-7f3a2b",
            name="Primary Sentinel Node",
            type=DeploymentType.SENTINEL,
            status=DeploymentStatus.ONLINE,
            security_level=768,
            created_at=datetime.now() - timedelta(days=14, hours=7),
            uptime_seconds=14 * 24 * 3600 + 7 * 3600,
            memory_mb=4200,
            requests_per_min=247
        ),
        Deployment(
            id="miner-alpha-9c4d1e",
            name="Mining Node Alpha",
            type=DeploymentType.MINING,
            status=DeploymentStatus.MINING,
            security_level=768,
            created_at=datetime.now() - timedelta(days=7),
            uptime_seconds=7 * 24 * 3600,
            hashrate=42.5,
            memory_mb=2800,
            requests_per_min=0
        )
    ]


@ui_router.post("/deployments")
async def create_deployment(
    deployment: DeploymentCreate,
    user: WalletSession = Depends(get_current_user)
) -> Deployment:
    """Create a new deployment"""
    # In production, create actual deployment
    deployment_id = f"{deployment.type.value}-{uuid.uuid4().hex[:6]}"

    return Deployment(
        id=deployment_id,
        name=deployment.name,
        type=deployment.type,
        status=DeploymentStatus.STARTING,
        security_level=deployment.security_level,
        created_at=datetime.now(),
        uptime_seconds=0,
        memory_mb=0,
        requests_per_min=0
    )


@ui_router.delete("/deployments/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    user: WalletSession = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete a deployment"""
    return {"status": "deleted", "deployment_id": deployment_id}


@ui_router.post("/deployments/{deployment_id}/restart")
async def restart_deployment(
    deployment_id: str,
    user: WalletSession = Depends(get_current_user)
) -> Dict[str, str]:
    """Restart a deployment"""
    return {"status": "restarting", "deployment_id": deployment_id}


# ============================================================================
# Wallet Endpoints
# ============================================================================

@ui_router.get("/wallet/balance")
async def get_wallet_balance(
    user: WalletSession = Depends(get_current_user)
) -> WalletBalance:
    """Get wallet balance for the authenticated user"""
    return WalletBalance(
        pls=2450.00,
        matic=125.50,
        staked=500.00,
        rewards=48.50,
        usd_value=4900.00 + 112.95 + 1000.00 + 97.00
    )


@ui_router.get("/wallet/transactions")
async def get_transactions(
    user: WalletSession = Depends(get_current_user),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    tx_type: Optional[str] = None
) -> List[Transaction]:
    """Get wallet transaction history"""
    # In production, fetch from blockchain/database
    transactions = [
        Transaction(
            id="tx-001",
            type="mining_reward",
            amount=12.50,
            token="PLS",
            from_address=None,
            to_address=user.wallet_address,
            timestamp=datetime.now() - timedelta(hours=2),
            status="confirmed",
            tx_hash="0x8f3a2b1c..."
        ),
        Transaction(
            id="tx-002",
            type="send",
            amount=50.00,
            token="PLS",
            from_address=user.wallet_address,
            to_address="0x8f3a...2b1c",
            timestamp=datetime.now() - timedelta(days=1),
            status="confirmed",
            tx_hash="0x7e2b9c4d..."
        ),
        Transaction(
            id="tx-003",
            type="stake",
            amount=500.00,
            token="PLS",
            from_address=user.wallet_address,
            to_address=None,
            timestamp=datetime.now() - timedelta(days=3),
            status="confirmed",
            tx_hash="0x6d1a8b3e..."
        )
    ]

    if tx_type:
        transactions = [t for t in transactions if t.type == tx_type]

    return transactions[offset:offset + limit]


@ui_router.post("/wallet/send")
async def send_tokens(
    recipient: str,
    amount: float,
    token: str = "PLS",
    user: WalletSession = Depends(get_current_user)
) -> Transaction:
    """Send tokens to another address"""
    # In production, create blockchain transaction
    return Transaction(
        id=f"tx-{uuid.uuid4().hex[:8]}",
        type="send",
        amount=amount,
        token=token,
        from_address=user.wallet_address,
        to_address=recipient,
        timestamp=datetime.now(),
        status="pending",
        tx_hash=None
    )


@ui_router.post("/wallet/claim-rewards")
async def claim_mining_rewards(
    user: WalletSession = Depends(get_current_user)
) -> Transaction:
    """Claim pending mining rewards"""
    return Transaction(
        id=f"tx-{uuid.uuid4().hex[:8]}",
        type="claim",
        amount=48.50,
        token="PLS",
        from_address=None,
        to_address=user.wallet_address,
        timestamp=datetime.now(),
        status="pending",
        tx_hash=None
    )


@ui_router.post("/wallet/stake")
async def stake_tokens(
    amount: float,
    duration_days: int = 90,
    user: WalletSession = Depends(get_current_user)
) -> Dict[str, Any]:
    """Stake PLS tokens"""
    apy_rates = {30: 0.08, 60: 0.10, 90: 0.125}
    apy = apy_rates.get(duration_days, 0.125)

    return {
        "staked_amount": amount,
        "duration_days": duration_days,
        "apy": apy,
        "estimated_reward": amount * apy * (duration_days / 365),
        "unlock_date": (datetime.now() + timedelta(days=duration_days)).isoformat(),
        "status": "pending"
    }


# ============================================================================
# Mining Endpoints
# ============================================================================

@ui_router.get("/mining/stats")
async def get_mining_stats(
    user: WalletSession = Depends(get_current_user)
) -> MiningStats:
    """Get mining statistics"""
    return MiningStats(
        hashrate=42.5,
        valid_shares=1247,
        rejected_shares=12,
        today_earnings=12.50,
        total_mined=48.50,
        blocks_found=12,
        is_active=True
    )


@ui_router.post("/mining/start")
async def start_mining(
    worker_name: str = "pulsar-miner-01",
    threads: int = 4,
    intensity: int = 75,
    user: WalletSession = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start mining operation"""
    return {
        "status": "started",
        "worker_name": worker_name,
        "threads": threads,
        "intensity": intensity,
        "pool": "stratum+tcp://pool.pulsar.cloud:3333"
    }


@ui_router.post("/mining/stop")
async def stop_mining(
    user: WalletSession = Depends(get_current_user)
) -> Dict[str, str]:
    """Stop mining operation"""
    return {"status": "stopped"}


@ui_router.get("/mining/pool-stats")
async def get_pool_stats() -> Dict[str, Any]:
    """Get mining pool statistics"""
    return {
        "pool_hashrate": 428.5,
        "active_miners": 2847,
        "blocks_found_24h": 156,
        "pool_fee": 0.01,
        "minimum_payout": 10.0,
        "payout_interval": "hourly"
    }


# ============================================================================
# Marketplace Endpoints
# ============================================================================

@ui_router.get("/marketplace/items")
async def list_marketplace_items(
    category: Optional[str] = None,
    sort: str = "recent",
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0)
) -> List[NFTItem]:
    """List marketplace items"""
    # In production, fetch from database
    items = [
        NFTItem(
            id="qg-001",
            name="Guardian #001",
            collection="Quantum Guardians",
            category="collectibles",
            price=75.0,
            owner="0x742d...f8c9",
            creator="0x5c0f...7a2d",
            image_url=None,
            pqc_signed=True,
            rarity="legendary",
            likes=142,
            created_at=datetime.now() - timedelta(days=30)
        ),
        NFTItem(
            id="sk-042",
            name="Guild Access Pass",
            collection="Sentinel Keys",
            category="utility",
            price=250.0,
            owner="0x8f3a...2b1c",
            creator="0x742d...f8c9",
            image_url=None,
            pqc_signed=True,
            rarity="epic",
            likes=89,
            created_at=datetime.now() - timedelta(days=14)
        )
    ]

    if category:
        items = [i for i in items if i.category == category]

    return items[offset:offset + limit]


@ui_router.post("/marketplace/create")
async def create_nft(
    name: str,
    description: Optional[str] = None,
    price: float = 0,
    collection: Optional[str] = None,
    category: str = "art",
    royalties: float = 10.0,
    pqc_sign: bool = True,
    user: WalletSession = Depends(get_current_user)
) -> NFTItem:
    """Create a new NFT"""
    return NFTItem(
        id=f"nft-{uuid.uuid4().hex[:8]}",
        name=name,
        collection=collection or "Uncategorized",
        category=category,
        price=price,
        owner=user.wallet_address,
        creator=user.wallet_address,
        image_url=None,
        pqc_signed=pqc_sign,
        rarity="common",
        likes=0,
        created_at=datetime.now()
    )


@ui_router.post("/marketplace/buy/{item_id}")
async def buy_nft(
    item_id: str,
    user: WalletSession = Depends(get_current_user)
) -> Dict[str, Any]:
    """Purchase an NFT"""
    return {
        "status": "purchased",
        "item_id": item_id,
        "buyer": user.wallet_address,
        "tx_hash": f"0x{uuid.uuid4().hex}"
    }


# ============================================================================
# SHANEBRAIN AI Endpoints
# ============================================================================

@ui_router.post("/ai/chat")
async def ai_chat(
    request: AIMessage,
    user: WalletSession = Depends(get_current_user)
) -> AIResponse:
    """Chat with SHANEBRAIN AI"""
    message_lower = request.message.lower()

    # Generate contextual response
    if "threat" in message_lower or "pts" in message_lower:
        response = "Your current PTS score is 32 (SAFE tier). Quantum risk is minimal."
        suggestions = ["View detailed breakdown", "Check recent events", "Export report"]
    elif "pqc" in message_lower or "encryption" in message_lower:
        response = "Your system uses ML-KEM-768 (NIST Level 3). No vulnerabilities detected."
        suggestions = ["Upgrade to ML-KEM-1024", "View encryption stats", "Rotate keys"]
    elif "mining" in message_lower:
        response = "Current hashrate: 42.5 TH/s. Optimization available for +35% performance."
        suggestions = ["Apply optimizations", "View pool stats", "Check earnings"]
    else:
        response = "I'm SHANEBRAIN, your quantum-enhanced AI assistant. How can I help?"
        suggestions = ["Analyze threats", "Check PQC status", "Optimize mining", "Create NFT"]

    return AIResponse(
        response=response,
        confidence=0.95,
        suggestions=suggestions
    )


@ui_router.get("/ai/analytics")
async def get_ai_analytics(
    period: str = "24h",
    user: WalletSession = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get AI analytics data"""
    return {
        "period": period,
        "threats_detected": 247,
        "threats_breakdown": {
            "critical": 3,
            "warning": 28,
            "info": 216
        },
        "recommendations_applied": 89,
        "art_generated": 42,
        "messages_processed": 1247,
        "avg_response_time_ms": 180,
        "accuracy": 98.7
    }


# ============================================================================
# Analytics Endpoints
# ============================================================================

@ui_router.post("/analytics/download")
async def track_download(
    platform: str,
    wallet: Optional[str] = None
) -> Dict[str, str]:
    """Track download analytics"""
    return {"status": "tracked", "platform": platform}


@ui_router.get("/analytics/network")
async def get_network_stats() -> Dict[str, Any]:
    """Get network-wide statistics"""
    return {
        "active_nodes": 2847,
        "total_transactions": 14200000,
        "threat_prevention_rate": 99.97,
        "network_hashrate": 428.5,
        "pqc_operations_24h": 1420000
    }


# ============================================================================
# Helper function to mount static files and templates
# ============================================================================

def setup_ui_routes(app):
    """Setup UI routes and static file serving"""
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ui_dir = os.path.join(project_root, "ui")

    # Mount static files
    static_dir = os.path.join(ui_dir, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Include UI router
    app.include_router(ui_router)

    return app
