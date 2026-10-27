"""Registro minimo de experiencias operativas, compartido entre modulos SKY.

Solo guarda huellas de ciclos aleatorios y resultado FINAL del agente autorizado.
Nunca guarda voces, texto, comandos, rutas, claves, prompts ni parametros.
Las observaciones no autorizan acciones, reentrenamiento ni cambios de codigo.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import threading
import time

_LOCK = threading.RLock()
_ROOT = Path(__file__).resolve().parents[1]
_MAX_ROWS = 10000
_RETENTION_DAYS = 90
_CYCLE = re.compile(r"[A-Za-z0-9_-]{20,60}\Z")
_MODULE = re.compile(r"[a-z0-9_-]{2,65}\Z")


def _path() -> Path:
    return Path(os.getenv("SKY_MODULE_EXPERIENCE_DB") or _ROOT / "local_data" / "sky_module_experience.sqlite3")


def _connection():
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("""CREATE TABLE IF NOT EXISTS module_experiences (
        digest TEXT PRIMARY KEY, module TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK(outcome IN ('verified_success','reported_failure')),
        observed_at INTEGER NOT NULL)""")
    conn.execute("CREATE INDEX IF NOT EXISTS experience_time ON module_experiences(observed_at)")
    conn.commit()
    return conn


def _recognized(module: str) -> bool:
    """Registrados en el catalogo, no solo cadenas arbitrarias del modelo."""
    if not isinstance(module, str) or not _MODULE.fullmatch(module):
        return False
    from .sky_module_registry import lookup
    if lookup(module):
        return True
    from .sky_modulos import catalogo
    return any(item["id"] == module for item in catalogo())


def record_cycle(cycle_id: str, module: str, result: str, *, verified: bool) -> bool:
    """Acepta un ciclo terminal; repetidos no incrementan las estadisticas.

    El unico punto de llamada del agente esta en sky_execution_cycle.
    Una accion en estado PENDING/SENT/RUNNING nunca puede registrarse.
    """
    if (not isinstance(cycle_id, str) or not _CYCLE.fullmatch(cycle_id)
            or not _recognized(module) or type(verified) is not bool):
        return False
    if result == "completed" and verified is True:
        outcome = "verified_success"
    elif result == "failed" and verified is False:
        outcome = "reported_failure"
    else:
        return False
    digest = hashlib.sha256(cycle_id.encode("ascii")).hexdigest()
    now = int(time.time())
    with _LOCK, closing(_connection()) as db:
        with db:
            cur = db.execute("""INSERT OR IGNORE INTO module_experiences
                (digest,module,outcome,observed_at) VALUES (?,?,?,?)""",
                (digest, module, outcome, now))
            db.execute("DELETE FROM module_experiences WHERE observed_at < ?",
                       (now - _RETENTION_DAYS * 86400,))
            db.execute("""DELETE FROM module_experiences WHERE digest IN (
                SELECT digest FROM module_experiences
                ORDER BY observed_at DESC LIMIT -1 OFFSET ?)""", (_MAX_ROWS,))
        return cur.rowcount == 1


def report() -> dict:
    """El registro esta separado de sky_neural_memory y no duplica sus roles."""
    path = _path()
    if not path.is_file():
        return {"total": 0, "verified_success": 0, "reported_failure": 0,
                "by_module": {}, "model_weights_updated": False}
    with _LOCK, closing(_connection()) as db:
        rows = db.execute("""SELECT module,outcome,COUNT(*) AS n FROM module_experiences
                              GROUP BY module,outcome ORDER BY module""").fetchall()
    modules: dict[str, dict] = {}
    for row in rows:
        item = modules.setdefault(row["module"], {"verified_success": 0, "reported_failure": 0})
        item[row["outcome"]] = int(row["n"])
    return {"total": sum(sum(item.values()) for item in modules.values()),
            "verified_success": sum(item["verified_success"] for item in modules.values()),
            "reported_failure": sum(item["reported_failure"] for item in modules.values()),
            "by_module": modules, "model_weights_updated": False}
