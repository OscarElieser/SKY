"""Opt-in scoped Android chat credentials: separate from SKY owner and agent tokens.

Owner+MFA creates a device-bound, single-use invitation. Only an already paired
agent can exchange it for a short-lived chat token. No conversation content is
persisted here, and a chat token cannot call device/owner API routes.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from neural_core import sky_mobile_agent as agent

_LOCK = threading.RLock()
ROOT = Path(__file__).resolve().parents[1]
INVITE_TTL = 300
SESSION_TTL = 24 * 60 * 60
RATE_LIMIT = 12
WINDOW = 60


def _path() -> Path:
    return Path(os.getenv("SKY_MOBILE_CHAT_DB") or ROOT / "local_data" / "sky_mobile_chat.sqlite3")


@contextmanager
def _db():
    with _LOCK:
        target = _path()
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(target, timeout=10)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS invitations (
                code_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, expires REAL NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, created REAL NOT NULL,
                expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
                window_start REAL NOT NULL, calls INTEGER NOT NULL DEFAULT 0)""")
            with conn:
                yield conn
        finally:
            conn.close()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _active(device_id: str) -> bool:
    # One active pairing in the existing Android Agent; revoke there also
    # invalidates chat immediately. No agent token ever becomes a chat token.
    return any(device["id"] == device_id for device in agent.devices())


def invite(device_id: str) -> dict:
    if not _active(device_id):
        raise ValueError("Teléfono sin emparejamiento activo")
    code = secrets.token_urlsafe(24)
    now = time.time()
    with _db() as db:
        db.execute("DELETE FROM invitations WHERE expires<=? OR device_id=?", (now, device_id))
        db.execute("INSERT INTO invitations VALUES (?,?,?)", (_hash(code), device_id, now + INVITE_TTL))
    return {"code": code, "device_id": device_id, "expires_seconds": INVITE_TTL, "scope": "chat:write"}


def pair(device_id: str, agent_token: str, code: str) -> dict:
    if not isinstance(code, str) or not 16 <= len(code) <= 128:
        raise PermissionError("Autorización de chat inválida")
    agent.device_status(device_id, agent_token)  # requires the genuine paired agent token
    now = time.time()
    with _db() as db:
        row = db.execute("SELECT device_id,expires FROM invitations WHERE code_hash=?",
                         (_hash(code),)).fetchone()
        if not row or not hmac.compare_digest(row[0], device_id) or row[1] <= now:
            raise PermissionError("Autorización de chat inválida o caducada")
        # Consume before minting credentials, and revoke any earlier chat session.
        db.execute("DELETE FROM invitations WHERE code_hash=?", (_hash(code),))
        db.execute("UPDATE sessions SET revoked=1 WHERE device_id=?", (device_id,))
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO sessions VALUES (?,?,?,?,0,?,0)",
                   (_hash(token), device_id, now, now + SESSION_TTL, now))
    return {"token": token, "device_id": device_id, "expires_seconds": SESSION_TTL,
            "scope": "chat:write", "owner_key": False}


def authorize(device_id: str, token: str) -> None:
    """One bounded chat request; rejects revoked agent pairing and rate abuse."""
    if not isinstance(token, str) or not 32 <= len(token) <= 128:
        raise PermissionError("Sesión móvil inválida")
    if not _active(device_id):
        raise PermissionError("Dispositivo revocado o inexistente")
    now = time.time()
    with _db() as db:
        row = db.execute("""SELECT device_id,expires,revoked,window_start,calls
            FROM sessions WHERE token_hash=?""", (_hash(token),)).fetchone()
        if not row or not hmac.compare_digest(row[0], device_id) or row[1] <= now or row[2]:
            raise PermissionError("Sesión móvil inválida o caducada")
        start, used = (now, 0) if now - row[3] >= WINDOW else (row[3], row[4])
        if used >= RATE_LIMIT:
            raise PermissionError("Límite de solicitudes de chat; intentá después")
        db.execute("UPDATE sessions SET window_start=?,calls=? WHERE token_hash=?",
                   (start, used + 1, _hash(token)))


def revoke(device_id: str) -> None:
    """Owner can invalidate the chat session independently of the agent."""
    with _db() as db:
        db.execute("UPDATE sessions SET revoked=1 WHERE device_id=?", (device_id,))
        db.execute("DELETE FROM invitations WHERE device_id=?", (device_id,))
