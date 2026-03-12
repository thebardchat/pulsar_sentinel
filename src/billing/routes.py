"""Billing API routes for PULSAR SENTINEL."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import WalletSession
from api.routes import get_current_session
from billing.stripe_client import StripeClient
from config.constants import TierType
from config.logging import get_logger
from governance.access_control import AccessController

logger = get_logger("billing.routes")

billing_router = APIRouter(prefix="/billing", tags=["Billing"])

_stripe_client: StripeClient | None = None
_access_controller: AccessController | None = None


def init_billing(access_controller: AccessController) -> None:
    """Initialize billing routes with dependencies."""
    global _stripe_client, _access_controller
    _stripe_client = StripeClient()
    _access_controller = access_controller


# Request/Response models

class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    tier: TierType = Field(..., description="Subscription tier to purchase")
    success_url: str = Field(
        default="/dashboard?billing=success",
        description="URL to redirect to after successful payment",
    )
    cancel_url: str = Field(
        default="/dashboard?billing=cancelled",
        description="URL to redirect to if payment is cancelled",
    )


class CheckoutResponse(BaseModel):
    """Response containing checkout session URL."""
    checkout_url: str


class PortalRequest(BaseModel):
    """Request to create a billing portal session."""
    return_url: str = Field(
        default="/dashboard",
        description="URL to redirect to when leaving the portal",
    )


class PortalResponse(BaseModel):
    """Response containing portal session URL."""
    portal_url: str


# Routes

@billing_router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    session: WalletSession = Depends(get_current_session),
) -> CheckoutResponse:
    """Create a Stripe Checkout session for subscribing to a tier."""
    if _stripe_client is None:
        raise HTTPException(status_code=500, detail="Billing not configured")

    try:
        customer_id = _stripe_client.get_or_create_customer(
            session.wallet_address
        )
        checkout_url = _stripe_client.create_checkout_session(
            customer_id=customer_id,
            tier=request.tier,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutResponse(checkout_url=checkout_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("checkout_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@billing_router.post("/portal", response_model=PortalResponse)
async def create_portal(
    request: PortalRequest,
    session: WalletSession = Depends(get_current_session),
) -> PortalResponse:
    """Create a Stripe billing portal session for managing subscription."""
    if _stripe_client is None:
        raise HTTPException(status_code=500, detail="Billing not configured")

    try:
        customer_id = _stripe_client.get_or_create_customer(
            session.wallet_address
        )
        portal_url = _stripe_client.create_portal_session(
            customer_id=customer_id,
            return_url=request.return_url,
        )
        return PortalResponse(portal_url=portal_url)
    except Exception as e:
        logger.error("portal_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@billing_router.get("/subscription")
async def get_subscription(
    session: WalletSession = Depends(get_current_session),
) -> dict:
    """Get the current subscription status for the authenticated user."""
    if _stripe_client is None:
        raise HTTPException(status_code=500, detail="Billing not configured")

    try:
        customer_id = _stripe_client.get_or_create_customer(
            session.wallet_address
        )
        subscription = _stripe_client.get_subscription(customer_id)
        if subscription is None:
            return {"status": "none", "tier": "free"}
        return subscription
    except Exception as e:
        logger.error("subscription_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch subscription")


@billing_router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Handle Stripe webhook events. No auth — uses signature verification."""
    if _stripe_client is None:
        raise HTTPException(status_code=500, detail="Billing not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = _stripe_client.handle_webhook(payload, sig_header)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle subscription events
    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data_object)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_object)

    return {"status": "ok"}


def _handle_checkout_completed(session_data: dict) -> None:
    """Update user tier after successful checkout."""
    customer_id = session_data.get("customer")
    tier_value = session_data.get("metadata", {}).get("tier")

    if not customer_id or not tier_value or not _access_controller:
        return

    try:
        tier = TierType(tier_value)
    except ValueError:
        logger.warning("unknown_tier_in_checkout", tier=tier_value)
        return

    # Look up wallet address from Stripe customer
    if _stripe_client is None:
        return

    import stripe
    customer = stripe.Customer.retrieve(customer_id)
    wallet_address = customer.get("metadata", {}).get("wallet_address")

    if wallet_address:
        user = _access_controller.get_user(wallet_address)
        if user:
            user.tier = tier
            logger.info(
                "user_tier_upgraded",
                wallet_address=wallet_address,
                tier=tier.value,
            )


def _handle_subscription_updated(sub_data: dict) -> None:
    """Handle subscription changes (upgrades, downgrades)."""
    logger.info(
        "subscription_updated",
        subscription_id=sub_data.get("id"),
        status=sub_data.get("status"),
    )


def _handle_subscription_deleted(sub_data: dict) -> None:
    """Downgrade user to free tier when subscription is cancelled."""
    customer_id = sub_data.get("customer")
    if not customer_id or not _access_controller or not _stripe_client:
        return

    import stripe
    customer = stripe.Customer.retrieve(customer_id)
    wallet_address = customer.get("metadata", {}).get("wallet_address")

    if wallet_address:
        user = _access_controller.get_user(wallet_address)
        if user:
            user.tier = TierType.LEGACY_BUILDER
            logger.info(
                "user_tier_downgraded",
                wallet_address=wallet_address,
                tier=TierType.LEGACY_BUILDER.value,
            )
