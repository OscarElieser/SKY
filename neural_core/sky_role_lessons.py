"""Memoria operativa de fallos de SKY, para herramientas realmente ejecutadas.

Sólo almacena etiquetas cerradas, contadores y duraciones; jamás argumentos,
solicitudes, código, rutas de archivos, trazas, identidades ni credenciales.
Sus lecciones son consultivas: no alteran permisos ni ejecutan nuevas acciones.
"""
from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import re
import sqlite3
import threading
import time

_ROOT = Path(__file__).resolve().parents[1]
_LOCK = threading.RLock()
_TTL = 90 * 86400
_LIMIT = 2000
_ALLOWED_STATES = frozenset({"VERIFIED_LIMITED_SCOPE", "RETRIEVED_UNVERIFIED", "FAILED"})
_ISSUES = {
    "none": "",
    "invalid_input": "Revisá tipos, rangos y formato de los datos antes de ejecutar.",
    "permission_required": "Comprobá consentimiento explícito y el permiso de esta herramienta.",
    "dependency_unavailable": "Comprobá el conector o recurso externo; no inventés datos.",
    "verification_mismatch": "Contrastá las operaciones y corregí entradas o la herramienta, con pruebas.",
    "execution_failed": "Revisá la implementación y los tests antes de volver a intentar.",
}
_ID = re.compile(r"^[a-z][a-z0-9_]{1,59}$")

def _path():
    return Path(os.getenv("SKY_ROLE_LESSONS_DB") or _ROOT / "local_data" / "sky_role_lessons.sqlite3")

def _connect():
    target = _path()
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("""CREATE TABLE IF NOT EXISTS role_lessons(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL, tool TEXT NOT NULL,
        outcome TEXT NOT NULL, issue TEXT NOT NULL,
        attempts INTEGER NOT NULL, duration_ms INTEGER NOT NULL,
        observed_at INTEGER NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_role_lessons_lookup ON role_lessons(role, tool, observed_at)")
    db.commit()
    return db

def _validate(role, tool):
    if not isinstance(role, str) or not _ID.fullmatch(role):
        raise ValueError("Rol desconocido.")
    if not isinstance(tool, str) or not _ID.fullmatch(tool):
        raise ValueError("Herramienta desconocida.")

def record(role: str, tool: str, status: str, *, issue: str = "none",
           attempts: int = 1, duration_ms: int = 0) -> bool:
    """Registra SOLO resultado categórico de una operación que ya se ejecutó."""
    _validate(role, tool)
    if status not in _ALLOWED_STATES or issue not in _ISSUES:
        raise ValueError("Estado o clasificación fuera del catálogo.")
    if status != "FAILED" and issue != "none":
        raise ValueError("Un éxito no puede contener categoría de fallo.")
    if status == "FAILED" and issue == "none":
        raise ValueError("Un fallo necesita clasificación.")
    if type(attempts) is not int or not 0 <= attempts <= 2:
        raise ValueError("Intentos fuera de rango.")
    if type(duration_ms) is not int or not 0 <= duration_ms <= 3_600_000:
        raise ValueError("Duración fuera de rango.")
    now = int(time.time())
    with _LOCK, closing(_connect()) as db:
        with db:
            db.execute("""INSERT INTO role_lessons(role, tool, outcome, issue, attempts,
                          duration_ms, observed_at) VALUES(?,?,?,?,?,?,?)""",
                       (role, tool, status, issue, attempts, duration_ms, now))
            db.execute("DELETE FROM role_lessons WHERE observed_at < ?", (now - _TTL,))
            db.execute("""DELETE FROM role_lessons WHERE id IN
                           (SELECT id FROM role_lessons ORDER BY id DESC LIMIT -1 OFFSET ?)""", (_LIMIT,))
    return True

def lesson(role: str, tool: str) -> dict | None:
    """Recupera el patrón de fallo más frecuente, sin reutilizar entradas del usuario."""
    _validate(role, tool)
    cutoff = int(time.time()) - _TTL
    with _LOCK, closing(_connect()) as db:
        row = db.execute("""SELECT issue, COUNT(*) AS failures
                            FROM role_lessons
                            WHERE role=? AND tool=? AND outcome='FAILED'
                              AND observed_at>=? GROUP BY issue
                            ORDER BY failures DESC, issue ASC LIMIT 1""",
                         (role, tool, cutoff)).fetchone()
    if row is None:
        return None
    issue = row["issue"]
    return {"issue": issue, "prior_failures": int(row["failures"]),
            "guidance": _ISSUES[issue], "type": "advisory_only",
            "source": "past_tool_outcomes_not_user_content"}

def report() -> dict:
    """Métricas honestas; no confundir 'recuperado' con pruebas físicas o pesos."""
    cutoff = int(time.time()) - _TTL
    with _LOCK, closing(_connect()) as db:
        rows = db.execute("""SELECT role,tool,outcome,issue,COUNT(*) AS n,
                             SUM(CASE WHEN attempts=2 THEN 1 ELSE 0 END) AS retries,
                             SUM(duration_ms) AS elapsed
                             FROM role_lessons WHERE observed_at>=?
                             GROUP BY role,tool,outcome,issue
                             ORDER BY role,tool,outcome,issue""", (cutoff,)).fetchall()
    grouped = {}
    for row in rows:
        key = (row["role"], row["tool"])
        item = grouped.setdefault(key, {"role":key[0], "tool":key[1], "verified":0,
              "failed":0, "unverified_external":0, "retried_operations":0,
              "total_duration_ms":0, "failure_categories":{}})
        n = int(row["n"])
        if row["outcome"] == "FAILED":
            item["failed"] += n
            item["failure_categories"][row["issue"]] = n
        elif row["outcome"] == "VERIFIED_LIMITED_SCOPE":
            item["verified"] += n
        else:
            item["unverified_external"] += n
        item["retried_operations"] += int(row["retries"])
        item["total_duration_ms"] += int(row["elapsed"])
    tools = list(grouped.values())
    for item in tools:
        verified_and_failed = item["verified"] + item["failed"]
        item["local_verification_rate"] = (round(item["verified"]/verified_and_failed, 3)
                                            if verified_and_failed else None)
    return {"tools":tools,"total_observations":sum(
            x["verified"]+x["failed"]+x["unverified_external"] for x in tools),
            "retention_days":90,"contains_private_inputs":False,
            "model_weights_updated":False,"physical_device_verification":False,
            "advice_grants_permissions":False}
