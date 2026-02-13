"""Threat alert cog for PULSAR SENTINEL Discord bot.

Provides an async queue that the bot polls to send PTS tier change
notifications to a configured alerts channel.
"""

import asyncio
from dataclasses import dataclass

import discord
from discord.ext import commands, tasks

from discord_bot.embeds import threat_alert_embed


@dataclass
class ThreatAlert:
    """A queued threat alert."""

    pts_score: float
    tier: str  # 'safe', 'caution', 'critical'
    details: str = ""


# Module-level queue so other parts of the app can push alerts
alert_queue: asyncio.Queue[ThreatAlert] = asyncio.Queue()


def push_alert(pts_score: float, tier: str, details: str = "") -> None:
    """Push a threat alert onto the queue (thread-safe with running loop).

    Call this from anywhere in the application to queue a Discord alert.
    """
    alert = ThreatAlert(pts_score=pts_score, tier=tier, details=details)
    try:
        alert_queue.put_nowait(alert)
    except asyncio.QueueFull:
        pass  # Drop alert if queue is full (shouldn't happen with unbounded queue)


class AlertsCog(commands.Cog):
    """Polls the alert queue and sends threat notifications."""

    def __init__(self, bot: commands.Bot, alerts_channel_id: int) -> None:
        self.bot = bot
        self.alerts_channel_id = alerts_channel_id

    async def cog_load(self) -> None:
        """Start the polling loop when the cog loads."""
        if self.alerts_channel_id:
            self.poll_alerts.start()

    async def cog_unload(self) -> None:
        """Stop the polling loop when the cog unloads."""
        self.poll_alerts.cancel()

    @tasks.loop(seconds=5.0)
    async def poll_alerts(self) -> None:
        """Check the queue for new alerts and send them."""
        channel = self.bot.get_channel(self.alerts_channel_id)
        if channel is None:
            return

        while not alert_queue.empty():
            try:
                alert = alert_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            embed = threat_alert_embed(
                pts_score=alert.pts_score,
                tier=alert.tier,
                details=alert.details,
            )
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass  # Channel permissions issue - log in production

    @poll_alerts.before_loop
    async def before_poll(self) -> None:
        """Wait until the bot is ready before polling."""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot, alerts_channel_id: int = 0) -> None:
    """Add AlertsCog to bot."""
    await bot.add_cog(AlertsCog(bot, alerts_channel_id))
