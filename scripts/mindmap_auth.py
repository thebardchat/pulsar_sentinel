"""
mindmap_auth.py — Multi-user cookie auth for the ShaneBrain Mindmap server.

Designed for a family-sized user count (≤ 20). Local-first. No external auth
providers. Credentials live on the NAS (bullfrog) under /mnt/tank/shanebrain
and are NFS-mounted by the Pi at /mnt/nas/shanebrain. The Pi reads the file;
nothing in the auth layer talks to the cloud.

Design choices:
- bcrypt for password hashing (12-round default, slow enough on Pi 5)
- HttpOnly + SameSite=Strict cookies for session tokens
- Sessions are in-memory + persisted to JSON so Pi reboots don't kick users
- One JSON file per role: users.json (creds) + sessions.json (live tokens)
- "Owner" role can do anything; "family" role can read all + post deltas
- "viewer" role can read but not POST

If USERS_FILE env var is not set, auth is disabled (backward compatible —
the original public-on-Tailscale behavior keeps working).

Usage from mindmap_server.py:

    from mindmap_auth import Auth, require_login

    auth = Auth(
        users_file=os.environ.get("USERS_FILE"),
        sessions_file=os.environ.get("SESSIONS_FILE"),
    )

    @app.post("/api/login")
    async def login(req: Request):
        body = await req.json()
        token = auth.login(body["username"], body["password"])
        if not token:
            raise HTTPException(401, "bad credentials")
        resp = JSONResponse({"ok": True, "user": body["username"]})
        resp.set_cookie("mm_session", token, httponly=True, samesite="strict")
        return resp

    @app.get("/api/state")
    async def get_state(req: Request, user=Depends(require_login(auth))):
        # user is the dict for the logged-in account
        return load_state()
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Callable

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False  # fallback to scrypt; see _hash_password / _verify

from fastapi import Cookie, HTTPException, Request

SESSION_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


# ── Password hashing ───────────────────────────────────────────────────────


def _hash_password(plain: str) -> str:
    """Return a salted hash. bcrypt if available, else scrypt-from-hashlib."""
    if HAS_BCRYPT:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()
    # scrypt fallback so the server still works on a Pi without bcrypt installed
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(plain.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return "scrypt$" + salt.hex() + "$" + h.hex()


def _verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith("scrypt$"):
        _, salt_hex, hash_hex = hashed.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.scrypt(plain.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(expected, actual)
    if HAS_BCRYPT:
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except ValueError:
            return False
    # bcrypt-hashed creds but no bcrypt installed = fail closed
    return False


# ── Auth core ──────────────────────────────────────────────────────────────


class Auth:
    """File-backed cookie auth. Reload-friendly: re-reads users.json on every
    login check so adding/removing users via add_mindmap_user.py takes effect
    without restarting the server."""

    def __init__(
        self,
        users_file: str | None,
        sessions_file: str | None = None,
    ):
        self.users_file = Path(users_file) if users_file else None
        self.sessions_file = Path(sessions_file) if sessions_file else None
        self.enabled = bool(self.users_file)
        # In-memory session cache: token -> {"user": ..., "exp": ...}
        self.sessions: dict[str, dict[str, Any]] = {}
        if self.sessions_file and self.sessions_file.exists():
            try:
                self.sessions = json.loads(self.sessions_file.read_text())
            except json.JSONDecodeError:
                self.sessions = {}

    # ── User file ──────────────────────────────────────────────────────────

    def _load_users(self) -> dict[str, dict[str, Any]]:
        if not self.users_file or not self.users_file.exists():
            return {}
        try:
            data = json.loads(self.users_file.read_text())
        except json.JSONDecodeError:
            return {}
        # Backward-compat: file is either {username: {...}} or {users: [...]}
        if isinstance(data, dict) and "users" in data and isinstance(data["users"], list):
            return {u["username"]: u for u in data["users"]}
        return data if isinstance(data, dict) else {}

    # ── Session persistence ────────────────────────────────────────────────

    def _persist_sessions(self) -> None:
        if not self.sessions_file:
            return
        self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write
        tmp = self.sessions_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.sessions, indent=2))
        tmp.replace(self.sessions_file)

    def _prune_expired(self) -> None:
        now = int(time.time())
        for tok in list(self.sessions.keys()):
            if self.sessions[tok].get("exp", 0) < now:
                del self.sessions[tok]

    # ── Public API ─────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> str | None:
        """Return a fresh session token on success, None on failure."""
        if not self.enabled:
            return None
        users = self._load_users()
        user = users.get(username)
        if not user:
            return None
        if not _verify_password(password, user.get("password_hash", "")):
            return None
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            "user": username,
            "role": user.get("role", "family"),
            "display_name": user.get("display_name", username),
            "exp": int(time.time()) + SESSION_TTL_SECONDS,
        }
        self._prune_expired()
        self._persist_sessions()
        return token

    def logout(self, token: str | None) -> None:
        if token and token in self.sessions:
            del self.sessions[token]
            self._persist_sessions()

    def whoami(self, token: str | None) -> dict[str, Any] | None:
        """Return session dict if valid, None otherwise."""
        if not self.enabled:
            # Auth disabled — return a sentinel "everyone is shane" user.
            return {
                "user": "shane",
                "role": "owner",
                "display_name": "Shane",
                "exp": 2**31 - 1,
            }
        if not token:
            return None
        sess = self.sessions.get(token)
        if not sess:
            return None
        if sess.get("exp", 0) < int(time.time()):
            del self.sessions[token]
            self._persist_sessions()
            return None
        return sess


# ── Dependency factory ─────────────────────────────────────────────────────


def require_login(auth: Auth, min_role: str | None = None) -> Callable:
    """Return a FastAPI dependency that enforces login + optional role."""
    role_order = ["viewer", "family", "owner"]

    def _dep(mm_session: str | None = Cookie(default=None)) -> dict[str, Any]:
        sess = auth.whoami(mm_session)
        if not sess:
            raise HTTPException(status_code=401, detail="login required")
        if min_role:
            try:
                if role_order.index(sess["role"]) < role_order.index(min_role):
                    raise HTTPException(status_code=403, detail="insufficient role")
            except ValueError:
                raise HTTPException(status_code=403, detail="unknown role")
        return sess

    return _dep
