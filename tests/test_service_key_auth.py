"""Regression tests for fail-closed PULSAR_SERVICE_KEY handling (issue #7).

Asserts:
- No hardcoded default service key in auth/routes/agent_routes sources
- Missing/blank env denies the internal admin/service-key path
- Matching configured env key grants admin metadata session
- Production-like startup (api_debug=False) refuses to start without key
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# Project uses top-level config/ and src/ packages
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

# Historical public default — used only as an attack token in tests; must not
# appear as a code default in production sources.
_LEGACY_PUBLIC_DEFAULT = "shanebrain-internal-2026"

_API_SOURCES = (
    SRC / "api" / "auth.py",
    SRC / "api" / "routes.py",
    SRC / "api" / "agent_routes.py",
)


def _load_auth_module():
    """Load api/auth.py without importing api package __init__ (avoids server deps)."""
    path = SRC / "api" / "auth.py"
    spec = importlib.util.spec_from_file_location("pulsar_auth_service_key_test", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_agent_routes_module(auth_mod):
    """Load agent_routes with auth helper already available under api.auth."""
    # agent_routes does `from api.auth import get_internal_service_key`
    sys.modules["api.auth"] = auth_mod
    # Minimal api package stub so `from api.auth` works without server import
    if "api" not in sys.modules:
        import types

        pkg = types.ModuleType("api")
        pkg.__path__ = [str(SRC / "api")]
        sys.modules["api"] = pkg
    path = SRC / "api" / "agent_routes.py"
    spec = importlib.util.spec_from_file_location("pulsar_agent_routes_service_key_test", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def auth_mod():
    return _load_auth_module()


@pytest.mark.security
class TestNoHardcodedServiceKey:
    def test_sources_do_not_contain_legacy_default_string(self):
        for path in _API_SOURCES:
            text = path.read_text(encoding="utf-8")
            assert _LEGACY_PUBLIC_DEFAULT not in text, (
                f"{path.relative_to(ROOT)} still contains hardcoded default"
            )

    def test_environ_get_has_no_hardcoded_default_arg(self):
        """Reject os.environ.get('PULSAR_SERVICE_KEY', '<secret>') patterns."""
        pattern = re.compile(
            r"""os\.environ\.get\(\s*["']PULSAR_SERVICE_KEY["']\s*,\s*["'][^"']+["']\s*\)"""
        )
        for path in _API_SOURCES:
            text = path.read_text(encoding="utf-8")
            match = pattern.search(text)
            assert match is None, (
                f"{path.relative_to(ROOT)} still passes a default to "
                f"environ.get for PULSAR_SERVICE_KEY: {match.group(0)!r}"
            )


@pytest.mark.security
class TestFailClosedAuthPath:
    @pytest.mark.asyncio
    async def test_missing_env_denies_legacy_default_bearer(self, auth_mod, monkeypatch):
        monkeypatch.delenv("PULSAR_SERVICE_KEY", raising=False)
        assert auth_mod.get_internal_service_key() is None

        with pytest.raises(HTTPException) as exc_info:
            await auth_mod.get_current_user(
                authorization=f"Bearer {_LEGACY_PUBLIC_DEFAULT}"
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_blank_env_denies_any_bearer(self, auth_mod, monkeypatch):
        monkeypatch.setenv("PULSAR_SERVICE_KEY", "   ")
        assert auth_mod.get_internal_service_key() is None

        with pytest.raises(HTTPException) as exc_info:
            await auth_mod.get_current_user(authorization="Bearer not-a-real-key")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_configured_key_grants_admin_metadata_session(
        self, auth_mod, monkeypatch
    ):
        test_key = "unit-test-service-key-not-for-production"
        monkeypatch.setenv("PULSAR_SERVICE_KEY", test_key)

        session = await auth_mod.get_current_user(
            authorization=f"Bearer {test_key}"
        )
        assert session.wallet_address == "0xSHANEBRAIN_INTERNAL"
        assert session.metadata.get("role") == "admin"
        assert session.metadata.get("source") == "internal_service_key"
        # Must not use invalid WalletSession(role=...) kwarg path
        assert not hasattr(session, "role") or "role" not in session.__dataclass_fields__

    @pytest.mark.asyncio
    async def test_mismatched_bearer_denied_when_key_configured(
        self, auth_mod, monkeypatch
    ):
        monkeypatch.setenv("PULSAR_SERVICE_KEY", "correct-key-value")
        with pytest.raises(HTTPException) as exc_info:
            await auth_mod.get_current_user(authorization="Bearer wrong-key-value")
        assert exc_info.value.status_code == 401


@pytest.mark.security
class TestAgentRoutesFailClosed:
    def test_agent_auth_denies_legacy_default_when_env_unset(self, auth_mod, monkeypatch):
        monkeypatch.delenv("PULSAR_SERVICE_KEY", raising=False)
        agent = _load_agent_routes_module(auth_mod)
        with pytest.raises(HTTPException) as exc_info:
            agent._auth(f"Bearer {_LEGACY_PUBLIC_DEFAULT}")
        assert exc_info.value.status_code == 401

    def test_agent_auth_accepts_configured_key(self, auth_mod, monkeypatch):
        test_key = "unit-test-agent-service-key"
        monkeypatch.setenv("PULSAR_SERVICE_KEY", test_key)
        agent = _load_agent_routes_module(auth_mod)
        # Should not raise
        agent._auth(f"Bearer {test_key}")


@pytest.mark.security
class TestProductionStartupGate:
    def test_require_key_when_not_debug(self, auth_mod, monkeypatch):
        monkeypatch.delenv("PULSAR_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError, match="PULSAR_SERVICE_KEY"):
            auth_mod.require_service_key_unless_debug(api_debug=False)

    def test_allow_missing_key_in_debug(self, auth_mod, monkeypatch):
        monkeypatch.delenv("PULSAR_SERVICE_KEY", raising=False)
        auth_mod.require_service_key_unless_debug(api_debug=True)  # no raise

    def test_require_passes_when_key_set(self, auth_mod, monkeypatch):
        monkeypatch.setenv("PULSAR_SERVICE_KEY", "startup-gate-test-key")
        auth_mod.require_service_key_unless_debug(api_debug=False)  # no raise

    def test_server_lifespan_calls_startup_gate(self):
        text = (SRC / "api" / "server.py").read_text(encoding="utf-8")
        assert "require_service_key_unless_debug" in text
