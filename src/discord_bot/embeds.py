"""Themed embed builders for PULSAR SENTINEL Discord bot."""

import discord
from datetime import datetime, timezone

# Brand colors
CYAN = 0x00FFFF
MAGENTA = 0xFF00FF
GOLD = 0xFFD700
GREEN = 0x00FF41
RED = 0xFF0040

FOOTER_TEXT = "PULSAR SENTINEL \u2022 Post-Quantum Security"


def base_embed(
    title: str,
    description: str = "",
    color: int = CYAN,
) -> discord.Embed:
    """Create a base embed with standard footer and timestamp."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=FOOTER_TEXT)
    return embed


def welcome_embed(member_name: str) -> discord.Embed:
    """Create a welcome embed for new members."""
    embed = base_embed(
        title=f"Welcome, {member_name}!",
        description=(
            "You've entered the quantum-safe zone.\n\n"
            "**Get started:**\n"
            "\u2022 `!help` \u2014 See all commands\n"
            "\u2022 `!status` \u2014 Check system health\n"
            "\u2022 `!pricing` \u2014 View subscription tiers\n"
            "\u2022 `!pts` \u2014 Learn about threat scoring\n\n"
            "*Build it once. Secure it forever.*"
        ),
        color=MAGENTA,
    )
    embed.set_thumbnail(url="https://raw.githubusercontent.com/thebardchat/pulsar-sentinel/main/docs/images/logo.png")
    return embed


def help_embed() -> discord.Embed:
    """Create the help/commands embed."""
    embed = base_embed(
        title="PULSAR SENTINEL \u2014 Commands",
        description="Available bot commands:",
        color=CYAN,
    )
    commands = {
        "!help": "Show this command list",
        "!status": "System health check",
        "!pricing": "View subscription tiers",
        "!pts": "PTS formula & thresholds",
        "!docs": "Documentation links",
        "!invite": "Get Discord invite link",
    }
    for cmd, desc in commands.items():
        embed.add_field(name=f"`{cmd}`", value=desc, inline=True)
    return embed


def status_embed(healthy: bool, pqc_available: bool) -> discord.Embed:
    """Create a system status embed."""
    if healthy:
        color = GREEN
        status_icon = "\u2705"
        status_text = "Online"
    else:
        color = RED
        status_icon = "\u274c"
        status_text = "Offline"

    pqc_icon = "\U0001f6e1\ufe0f" if pqc_available else "\u26a0\ufe0f"
    pqc_text = "Active" if pqc_available else "Unavailable"

    embed = base_embed(
        title="System Status",
        color=color,
    )
    embed.add_field(name="Server", value=f"{status_icon} {status_text}", inline=True)
    embed.add_field(name="PQC Engine", value=f"{pqc_icon} {pqc_text}", inline=True)
    return embed


def pricing_embed(tiers: list[dict]) -> discord.Embed:
    """Create a pricing tiers embed.

    Args:
        tiers: List of dicts with keys: name, price_usd, operations_per_month,
               pqc_enabled, smart_contract_enabled, asr_frequency
    """
    embed = base_embed(
        title="Subscription Tiers",
        description="Choose your security level:",
        color=GOLD,
    )
    for tier in tiers:
        ops = "Unlimited" if tier["operations_per_month"] == -1 else f"{tier['operations_per_month']:,}"
        pqc = "\u2705" if tier["pqc_enabled"] else "\u274c"
        sc = "\u2705" if tier["smart_contract_enabled"] else "\u274c"
        value = (
            f"**${tier['price_usd']:.2f}/mo**\n"
            f"Operations: {ops}/mo\n"
            f"PQC: {pqc} | Smart Contracts: {sc}\n"
            f"ASR: {tier['asr_frequency'].capitalize()}"
        )
        embed.add_field(name=tier["name"], value=value, inline=True)
    return embed


def pts_embed(weights: dict, thresholds: dict) -> discord.Embed:
    """Create a PTS explanation embed.

    Args:
        weights: Dict of factor_name -> weight (0-1)
        thresholds: Dict with tier1_max and tier2_max
    """
    weight_lines = "\n".join(
        f"\u2022 **{name.replace('_', ' ').title()}**: {weight:.0%}"
        for name, weight in weights.items()
    )

    t1 = thresholds["tier1_max"]
    t2 = thresholds["tier2_max"]

    embed = base_embed(
        title="Points Toward Threat Score (PTS)",
        description=(
            "PTS measures account threat level using weighted factors.\n\n"
            f"**Weights:**\n{weight_lines}"
        ),
        color=CYAN,
    )
    embed.add_field(
        name="\U0001f7e2 Safe",
        value=f"PTS < {t1}",
        inline=True,
    )
    embed.add_field(
        name="\U0001f7e1 Caution",
        value=f"{t1} \u2264 PTS < {t2}",
        inline=True,
    )
    embed.add_field(
        name="\U0001f534 Critical",
        value=f"PTS \u2265 {t2}",
        inline=True,
    )
    return embed


def docs_embed() -> discord.Embed:
    """Create a documentation links embed."""
    embed = base_embed(
        title="Documentation & Links",
        color=CYAN,
    )
    embed.add_field(
        name="Landing Page",
        value="[pulsar-sentinel.com](https://thebardchat.github.io/pulsar-sentinel/)",
        inline=False,
    )
    embed.add_field(
        name="GitHub",
        value="[github.com/thebardchat/pulsar-sentinel](https://github.com/thebardchat/pulsar-sentinel)",
        inline=False,
    )
    embed.add_field(
        name="API Docs",
        value="http://localhost:8000/docs (when server is running)",
        inline=False,
    )
    return embed


def threat_alert_embed(
    pts_score: float,
    tier: str,
    details: str = "",
) -> discord.Embed:
    """Create a threat alert embed for PTS tier changes.

    Args:
        pts_score: Current PTS score
        tier: One of 'safe', 'caution', 'critical'
        details: Optional details string
    """
    tier_config = {
        "safe": ("\U0001f7e2 Safe", GREEN),
        "caution": ("\u26a0\ufe0f Caution", GOLD),
        "critical": ("\U0001f6a8 Critical", RED),
    }
    label, color = tier_config.get(tier, ("\u2753 Unknown", CYAN))

    embed = base_embed(
        title="Threat Level Change",
        description=f"PTS tier changed to **{label}**",
        color=color,
    )
    embed.add_field(name="PTS Score", value=f"`{pts_score:.1f}`", inline=True)
    embed.add_field(name="Tier", value=label, inline=True)
    if details:
        embed.add_field(name="Details", value=details, inline=False)
    return embed
