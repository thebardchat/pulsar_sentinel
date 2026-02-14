"""Command cog for PULSAR SENTINEL Discord bot."""

import sys
from pathlib import Path

import discord
from discord.ext import commands

# Add project root to path for config imports (do NOT add config/ directly - it shadows stdlib logging)
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from config.constants import TIER_CONFIGS, PTS_WEIGHTS, PTSThreshold
from config.settings import get_settings
from discord_bot.embeds import (
    help_embed,
    status_embed,
    pricing_embed,
    pts_embed,
    docs_embed,
    base_embed,
    CYAN,
)


class PulsarCommands(commands.Cog):
    """Core commands for the Pulsar Sentinel community bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context) -> None:
        """Show all available commands."""
        await ctx.send(embed=help_embed())

    @commands.command(name="status")
    async def status_command(self, ctx: commands.Context) -> None:
        """Check system health by hitting the local API."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                settings = get_settings()
                url = f"http://localhost:{settings.api_port}/api/v1/health"
                resp = await client.get(url)
                data = resp.json()
                healthy = data.get("status") == "healthy"
                pqc = data.get("pqc_available", False)
        except Exception:
            healthy = False
            pqc = False

        await ctx.send(embed=status_embed(healthy, pqc))

    @commands.command(name="pricing")
    async def pricing_command(self, ctx: commands.Context) -> None:
        """Show subscription tier pricing."""
        tiers = [
            {
                "name": cfg.name,
                "price_usd": cfg.price_usd,
                "operations_per_month": cfg.operations_per_month,
                "pqc_enabled": cfg.pqc_enabled,
                "smart_contract_enabled": cfg.smart_contract_enabled,
                "asr_frequency": cfg.asr_frequency,
            }
            for cfg in TIER_CONFIGS.values()
        ]
        await ctx.send(embed=pricing_embed(tiers))

    @commands.command(name="pts")
    async def pts_command(self, ctx: commands.Context) -> None:
        """Explain PTS formula and thresholds."""
        thresholds = {
            "tier1_max": PTSThreshold.TIER1_MAX,
            "tier2_max": PTSThreshold.TIER2_MAX,
        }
        await ctx.send(embed=pts_embed(PTS_WEIGHTS, thresholds))

    @commands.command(name="docs")
    async def docs_command(self, ctx: commands.Context) -> None:
        """Show documentation links."""
        await ctx.send(embed=docs_embed())

    @commands.command(name="invite")
    async def invite_command(self, ctx: commands.Context) -> None:
        """Show Discord server invite link."""
        settings = get_settings()
        invite_url = settings.discord_invite_url or "No invite link configured."
        embed = base_embed(
            title="Join PULSAR SENTINEL",
            description=f"**Invite Link:**\n{invite_url}",
            color=CYAN,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Add PulsarCommands cog to bot."""
    await bot.add_cog(PulsarCommands(bot))
