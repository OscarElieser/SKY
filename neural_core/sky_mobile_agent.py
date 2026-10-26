"""SKY Mobile Agent: cola privada para Android. No ejecuta nada en Windows.

Los comandos son de alcance mínimo: el dueño autenticado los solicita y
el teléfono, con su propio token y autorización visible, los procesa.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
import unicodedata
import uuid
from contextlib import contextmanager
from pathlib import Path

_LOCK = threading.RLock()
ROOT = Path(__file__).resolve().parents[1]
TARGETS = {"youtube": "YouTube", "chrome": "Chrome", "whatsapp": "WhatsApp", "gmail": "Gmail"}
PAIR_TTL = 300
COMMAND_TTL = 120


def _db_path() -> Path:
    return Path(os.getenv("SKY_MOBILE_AGENT_DB") or ROOT / "local_data" / "sky_mobile_agent.sqlite3")


@contextmanager
def _db():
    with _LOCK:
        path = _db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=10)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("""CREATE TABLE IF NOT EXISTS pairing (
                code_hash TEXT PRIMARY KEY, expires REAL NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS mobile_devices (
                id TEXT PRIMARY KEY, label TEXT NOT NULL, token_hash TEXT NOT NULL,
                created REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS mobile_commands (
                id TEXT PRIMARY KEY, device_id TEXT NOT NULL,
                action TEXT NOT NULL, target TEXT NOT NULL, state TEXT NOT NULL,
                created REAL NOT NULL, expires REAL NOT NULL,
                claimed REAL, message TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(device_id) REFERENCES mobile_devices(id))""")
            with conn:
                yield conn
        finally:
            conn.close()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pairing_code() -> dict:
    code = secrets.token_urlsafe(18)
    now = time.time()
    with _db() as conn:
        conn.execute("DELETE FROM pairing WHERE expires < ?", (now,))
        conn.execute("INSERT INTO pairing(code_hash,expires) VALUES(?,?)",
                     (_hash(code), now + PAIR_TTL))
    return {"code": code, "expires_seconds": PAIR_TTL}


def pair(code: str, label: str) -> dict:
    if not isinstance(code, str) or len(code) > 128 or not isinstance(label, str) or not re.fullmatch(r"[\w .-]{3,60}", label, flags=re.UNICODE):
        raise ValueError("Datos de emparejamiento inválidos")
    now = time.time()
    with _db() as conn:
        found = conn.execute("SELECT expires FROM pairing WHERE code_hash=?", (_hash(code),)).fetchone()
        if not found or found[0] <= now:
            raise PermissionError("Código caducado o inválido")
        conn.execute("DELETE FROM pairing WHERE code_hash=?", (_hash(code),))
        device_id, token = uuid.uuid4().hex, secrets.token_urlsafe(32)
        conn.execute("INSERT INTO mobile_devices(id,label,token_hash,created) VALUES(?,?,?,?)",
                     (device_id, label.strip(), _hash(token), now))
    return {"device_id": device_id, "token": token, "label": label.strip()}


def _authorized(conn: sqlite3.Connection, device_id: str, token: str) -> bool:
    if not isinstance(token, str) or len(token) > 128:
        return False
    found = conn.execute("SELECT token_hash,revoked FROM mobile_devices WHERE id=?", (device_id,)).fetchone()
    return bool(found and not found[1] and hmac.compare_digest(found[0], _hash(token)))


def devices() -> list[dict]:
    with _db() as conn:
        rows = conn.execute("SELECT id,label,created FROM mobile_devices WHERE revoked=0 ORDER BY created").fetchall()
    return [{"id": a, "label": b, "created": c} for a, b, c in rows]


def revoke(device_id: str, token: str | None = None) -> None:
    with _db() as conn:
        if token is not None and not _authorized(conn, device_id, token):
            raise PermissionError("Dispositivo no autorizado")
        updated = conn.execute("UPDATE mobile_devices SET revoked=1 WHERE id=? AND revoked=0", (device_id,))
        if not updated.rowcount:
            raise ValueError("Dispositivo no encontrado")
        conn.execute("UPDATE mobile_commands SET state='REVOKED' WHERE device_id=? AND state IN ('PENDING','CLAIMED')", (device_id,))


def queue(device_id: str, target: str) -> dict:
    if target not in TARGETS:
        raise ValueError("Aplicación no permitida")
    now = time.time()
    with _db() as conn:
        found = conn.execute("SELECT 1 FROM mobile_devices WHERE id=? AND revoked=0", (device_id,)).fetchone()
        if not found:
            raise ValueError("Teléfono no emparejado")
        # Límite por dispositivo, inclusive ante solicitudes rápidas por voz.
        num = conn.execute("SELECT COUNT(*) FROM mobile_commands WHERE device_id=? AND created>?",
                           (device_id, now - 60)).fetchone()[0]
        if num >= 10:
            raise ValueError("Demasiadas solicitudes: intentá más tarde")
        command_id = uuid.uuid4().hex
        conn.execute("""INSERT INTO mobile_commands
            (id,device_id,action,target,state,created,expires) VALUES(?,?,? ,?,'PENDING',?,?)""",
            (command_id, device_id, "launch_app", target, now, now + COMMAND_TTL))
    return {"command_id": command_id, "state": "PENDING", "target": target, "expires_seconds": COMMAND_TTL}


def poll(device_id: str, token: str) -> dict:
    now = time.time()
    with _db() as conn:
        if not _authorized(conn, device_id, token):
            raise PermissionError("Dispositivo no autorizado")
        conn.execute("UPDATE mobile_commands SET state='EXPIRED' WHERE device_id=? AND state IN ('PENDING','CLAIMED') AND expires<=?",
                     (device_id, now))
        item = conn.execute("""SELECT id,action,target FROM mobile_commands
            WHERE device_id=? AND state='PENDING' AND expires>? ORDER BY created LIMIT 1""",
            (device_id, now)).fetchone()
        if not item:
            return {"command": None}
        conn.execute("UPDATE mobile_commands SET state='CLAIMED',claimed=? WHERE id=?", (now, item[0]))
        return {"command": {"id": item[0], "action": item[1], "target": item[2]}}


def complete(device_id: str, token: str, command_id: str, state: str, message: str = "") -> dict:
    if state not in {"SENT", "FAILED", "REJECTED"}:
        raise ValueError("Estado de ejecución inválido")
    with _db() as conn:
        if not _authorized(conn, device_id, token):
            raise PermissionError("Dispositivo no autorizado")
        changed = conn.execute("""UPDATE mobile_commands SET state=?,message=?
            WHERE id=? AND device_id=? AND state='CLAIMED' AND expires>?""",
            (state, str(message)[:180], command_id, device_id, time.time()))
        if changed.rowcount != 1:
            raise ValueError("Orden no encontrada, vencida o ya procesada")
    return {"command_id": command_id, "state": state}


def command_status(device_id: str, command_id: str) -> dict:
    with _db() as conn:
        row = conn.execute("SELECT state,target,message,expires FROM mobile_commands WHERE id=? AND device_id=?",
                           (command_id, device_id)).fetchone()
    if not row:
        raise ValueError("Orden no encontrada")
    state = "EXPIRED" if row[0] in ("PENDING", "CLAIMED") and row[3] <= time.time() else row[0]
    return {"state": state, "target": row[1], "message": row[2]}


def parse_voice(text: str) -> str | None:
    normalized = unicodedata.normalize("NFKD", str(text).casefold())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", normalized)).strip()
    normalized = re.sub(r"^(?:(?:oye|hey) )?(?:sky )?", "", normalized)
    match = re.fullmatch(
        r"(?:abre|abri|abrir) (?:el )?(youtube|chrome|whatsapp|gmail) "
        r"en (?:mi |el )?(?:telefono|celular|android)", normalized
    )
    return match.group(1) if match else None


def voice_request(text: str) -> dict | None:
    target = parse_voice(text)
    if not target:
        return None
    available = devices()
    if len(available) != 1:
        message = ("Primero emparejá tu teléfono en SKY Mobile Agent." if not available else
                   "Hay varios teléfonos emparejados. Elegí uno en el panel de dispositivos.")
        return {"tipo": "respuesta", "proveedor": "sky-mobile", "mensaje": message}
    try:
        queued = queue(available[0]["id"], target)
    except ValueError as exc:
        return {"tipo": "respuesta", "proveedor": "sky-mobile", "mensaje": str(exc)}
    return {"tipo": "respuesta", "proveedor": "sky-mobile",
            "mensaje": "Envié la solicitud para abrir " + TARGETS[target] +
                       " en " + available[0]["label"] + ". Confirmala en SKY Mobile Agent.",
            "mobile_command_id": queued["command_id"]}
