"""Main Discord bot for PULSAR SENTINEL."""

import sys
from pathlib import Path

import discord
from discord.ext import commands

# Add project root to path for config imports
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "config"))

from config.settings import get_settings
from discord_bot import embeds
from discord_bot import commands as pulsar_commands
from discord_bot import alerts


def create_bot() -> commands.Bot:
    """Create and configure the PULSAR SENTINEL Discord bot."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
        help_command=None,  # We use our own !help
    )

    @bot.event
    async def on_ready() -> None:
        print(f"[PULSAR SENTINEL] Bot connected as {bot.user}")
        print(f"[PULSAR SENTINEL] Serving {len(bot.guilds)} server(s)")
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="quantum threats | !help",
            )
        )

    @bot.event
    async def on_member_join(member: discord.Member) -> None:
        settings = get_settings()
        channel_id = settings.discord_general_channel_id
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel is not None:
                embed = embeds.welcome_embed(member.display_name)
                await channel.send(embed=embed)

    return bot


async def setup_bot(bot: commands.Bot) -> None:
    """Load all cogs onto the bot."""
    settings = get_settings()
    await pulsar_commands.setup(bot)
    await alerts.setup(bot, alerts_channel_id=settings.discord_alerts_channel_id)


def run_bot() -> None:
    """Run the bot (blocking). Call this from the launcher script."""
    settings = get_settings()
    token = settings.discord_bot_token

    if not token:
        print("[ERROR] DISCORD_BOT_TOKEN not set in .env")
        print("  1. Create a bot at https://discord.com/developers/applications")
        print("  2. Copy the bot token to your .env file")
        sys.exit(1)

    bot = create_bot()

    @bot.event
    async def setup_hook() -> None:
        await setup_bot(bot)

    print("[PULSAR SENTINEL] Starting Discord bot...")
    bot.run(token, log_handler=None)
