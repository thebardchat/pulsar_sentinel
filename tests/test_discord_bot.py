"""Tests for PULSAR SENTINEL Discord bot components.

Tests cover:
- Embed builders (pure functions, no Discord connection needed)
- Alert queue operations
"""

import sys
import asyncio
from pathlib import Path

import pytest

# Add src and config to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))


class TestEmbeds:
    """Tests for embed builder functions."""

    def test_base_embed_has_footer(self):
        from discord_bot.embeds import base_embed, FOOTER_TEXT

        embed = base_embed("Test Title", "Test description")
        assert embed.title == "Test Title"
        assert embed.description == "Test description"
        assert embed.footer.text == FOOTER_TEXT
        assert embed.timestamp is not None

    def test_base_embed_default_color(self):
        from discord_bot.embeds import base_embed, CYAN

        embed = base_embed("Test")
        assert embed.color.value == CYAN

    def test_base_embed_custom_color(self):
        from discord_bot.embeds import base_embed, RED

        embed = base_embed("Test", color=RED)
        assert embed.color.value == RED

    def test_welcome_embed_contains_member_name(self):
        from discord_bot.embeds import welcome_embed, MAGENTA

        embed = welcome_embed("Shane")
        assert "Shane" in embed.title
        assert embed.color.value == MAGENTA
        assert "!help" in embed.description

    def test_help_embed_has_all_commands(self):
        from discord_bot.embeds import help_embed

        embed = help_embed()
        field_names = [f.name for f in embed.fields]
        expected = ["!help", "!status", "!pricing", "!pts", "!docs", "!invite"]
        for cmd in expected:
            assert f"`{cmd}`" in field_names, f"Missing command: {cmd}"

    def test_status_embed_healthy(self):
        from discord_bot.embeds import status_embed, GREEN

        embed = status_embed(healthy=True, pqc_available=True)
        assert embed.color.value == GREEN
        assert any("Online" in f.value for f in embed.fields)

    def test_status_embed_unhealthy(self):
        from discord_bot.embeds import status_embed, RED

        embed = status_embed(healthy=False, pqc_available=False)
        assert embed.color.value == RED
        assert any("Offline" in f.value for f in embed.fields)

    def test_pricing_embed_shows_all_tiers(self):
        from discord_bot.embeds import pricing_embed

        tiers = [
            {
                "name": "Sentinel Core",
                "price_usd": 16.99,
                "operations_per_month": 10_000_000,
                "pqc_enabled": True,
                "smart_contract_enabled": False,
                "asr_frequency": "daily",
            },
            {
                "name": "Legacy Builder",
                "price_usd": 10.99,
                "operations_per_month": 5_000_000,
                "pqc_enabled": False,
                "smart_contract_enabled": False,
                "asr_frequency": "weekly",
            },
            {
                "name": "Autonomous Guild",
                "price_usd": 29.99,
                "operations_per_month": -1,
                "pqc_enabled": True,
                "smart_contract_enabled": True,
                "asr_frequency": "realtime",
            },
        ]
        embed = pricing_embed(tiers)
        assert len(embed.fields) == 3
        assert embed.fields[0].name == "Sentinel Core"
        assert "$16.99" in embed.fields[0].value
        assert "Unlimited" in embed.fields[2].value

    def test_pts_embed_shows_weights_and_thresholds(self):
        from discord_bot.embeds import pts_embed

        weights = {"quantum_risk_factor": 0.4, "access_violation_count": 0.3}
        thresholds = {"tier1_max": 50, "tier2_max": 150}
        embed = pts_embed(weights, thresholds)
        assert "40%" in embed.description
        assert "30%" in embed.description
        assert any("50" in f.value for f in embed.fields)
        assert any("150" in f.value for f in embed.fields)

    def test_docs_embed_has_links(self):
        from discord_bot.embeds import docs_embed

        embed = docs_embed()
        assert len(embed.fields) == 3
        assert "GitHub" in embed.fields[1].name

    def test_threat_alert_embed_safe(self):
        from discord_bot.embeds import threat_alert_embed, GREEN

        embed = threat_alert_embed(pts_score=25.0, tier="safe")
        assert embed.color.value == GREEN
        assert "25.0" in embed.fields[0].value

    def test_threat_alert_embed_critical(self):
        from discord_bot.embeds import threat_alert_embed, RED

        embed = threat_alert_embed(pts_score=200.0, tier="critical", details="Breach detected")
        assert embed.color.value == RED
        assert len(embed.fields) == 3
        assert "Breach detected" in embed.fields[2].value


class TestAlertQueue:
    """Tests for the alert queue system."""

    def test_push_alert_adds_to_queue(self):
        from discord_bot.alerts import alert_queue, push_alert, ThreatAlert

        # Clear queue
        while not alert_queue.empty():
            alert_queue.get_nowait()

        push_alert(pts_score=75.0, tier="caution", details="Test alert")
        assert not alert_queue.empty()

        alert = alert_queue.get_nowait()
        assert isinstance(alert, ThreatAlert)
        assert alert.pts_score == 75.0
        assert alert.tier == "caution"
        assert alert.details == "Test alert"

    def test_push_multiple_alerts(self):
        from discord_bot.alerts import alert_queue, push_alert

        # Clear queue
        while not alert_queue.empty():
            alert_queue.get_nowait()

        push_alert(25.0, "safe")
        push_alert(100.0, "caution")
        push_alert(200.0, "critical")

        assert alert_queue.qsize() == 3
