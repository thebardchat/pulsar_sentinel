"""Stripe subscription billing integration for PULSAR SENTINEL."""

from __future__ import annotations

import stripe
from config.settings import get_settings
from config.constants import TierType, TIER_CONFIGS
from config.logging import get_logger

logger = get_logger("billing")


class StripeClient:
    """Manages Stripe subscription operations."""

    def __init__(self) -> None:
        settings = get_settings()
        stripe.api_key = settings.stripe_secret_key
        self._webhook_secret = settings.stripe_webhook_secret

        # Map TierType to Stripe Price IDs from settings
        self._price_map: dict[TierType, str] = {
            TierType.LEGACY_BUILDER: settings.stripe_price_legacy,
            TierType.SENTINEL_CORE: settings.stripe_price_sentinel,
            TierType.AUTONOMOUS_GUILD: settings.stripe_price_guild,
        }

    def create_customer(
        self, wallet_address: str, email: str | None = None
    ) -> str:
        """Create a Stripe customer linked to a wallet address.

        Returns:
            Stripe customer ID
        """
        params: dict = {
            "metadata": {"wallet_address": wallet_address},
        }
        if email:
            params["email"] = email

        customer = stripe.Customer.create(**params)
        logger.info(
            "stripe_customer_created",
            wallet_address=wallet_address,
            customer_id=customer.id,
        )
        return customer.id

    def get_or_create_customer(
        self, wallet_address: str, email: str | None = None
    ) -> str:
        """Find existing customer by wallet address or create a new one."""
        customers = stripe.Customer.search(
            query=f'metadata["wallet_address"]:"{wallet_address}"',
            limit=1,
        )
        if customers.data:
            return customers.data[0].id
        return self.create_customer(wallet_address, email)

    def create_checkout_session(
        self,
        customer_id: str,
        tier: TierType,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout session for a subscription.

        Returns:
            Checkout session URL to redirect the user to
        """
        price_id = self._price_map.get(tier)
        if not price_id:
            raise ValueError(f"No Stripe Price ID configured for tier: {tier.value}")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"tier": tier.value},
        )
        logger.info(
            "stripe_checkout_created",
            customer_id=customer_id,
            tier=tier.value,
            session_id=session.id,
        )
        return session.url

    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create a Stripe billing portal session.

        Returns:
            Portal URL for the customer to manage their subscription
        """
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    def get_subscription(self, customer_id: str) -> dict | None:
        """Get the active subscription for a customer.

        Returns:
            Subscription info dict or None if no active subscription
        """
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status="active",
            limit=1,
        )
        if not subscriptions.data:
            return None

        sub = subscriptions.data[0]
        # Determine tier from price ID
        price_id = sub["items"]["data"][0]["price"]["id"]
        tier = None
        for t, pid in self._price_map.items():
            if pid == price_id:
                tier = t
                break

        tier_config = TIER_CONFIGS.get(tier) if tier else None

        return {
            "subscription_id": sub.id,
            "status": sub.status,
            "tier": tier.value if tier else "unknown",
            "tier_name": tier_config.name if tier_config else "Unknown",
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }

    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription at period end."""
        sub = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )
        logger.info(
            "stripe_subscription_cancelled",
            subscription_id=subscription_id,
        )
        return sub.cancel_at_period_end

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        """Verify and parse a Stripe webhook event.

        Returns:
            Parsed event dict

        Raises:
            ValueError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self._webhook_secret
            )
        except stripe.SignatureVerificationError:
            logger.warning("stripe_webhook_invalid_signature")
            raise ValueError("Invalid webhook signature")

        logger.info(
            "stripe_webhook_received",
            event_type=event.type,
            event_id=event.id,
        )
        return event
