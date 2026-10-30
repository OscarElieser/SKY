"""Memoria reflexiva de SKY Skill Builder, local y sin datos del usuario.

Las pruebas reales las ejecuta sky_skill_builder.probar en el runner existente.
Este módulo NO ejecuta código, instala habilidades, concede permisos, ni aprende pesos.
Las experiencias sólo contienen etiquetas cerradas (tema, fallo, resultado) y un
vector hashing 32D: recuperación aproximada, NO embeddings semánticos de un LLM.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import time

_LOCK = threading.RLock()
_ROOT = Path(__file__).resolve().parents[1]
_DIMENSIONS = 32
_MAX_ROWS = 1500
_RETENTION_SECONDS = 90 * 86400
_TOPICS = {
    "calculo": ("calcula", "calculo", "sumar", "restar", "porcentaje", "ecuacion"),
    "texto": ("texto", "resumen", "traduc", "corrig", "redact", "escrib"),
    "fechas": ("fecha", "calendario", "horario", "agenda", "dia", "mes"),
    "formato": ("formato", "tabla", "json", "csv", "lista"),
    "datos": ("datos", "estadistica", "contar", "promedio", "ordena"),
}
_ISSUES = frozenset({"syntax", "prohibited_code", "invalid_contract", "test_mismatch",
                     "sandbox_failure", "timeout", "unclassified", "none"})
_LESSONS = {
    "syntax": "Comprobá la sintaxis de Python antes de proponer la solución.",
    "prohibited_code": "Usá sólo los módulos y las funciones permitidas por SKY Skill Builder.",
    "invalid_contract": "Respetá la función ejecutar(entrada, contexto) y su resultado JSON.",
    "test_mismatch": "Contrastá la respuesta de cada prueba con su salida esperada.",
    "sandbox_failure": "Evitá excepciones de ejecución; contemplá entradas y casos extremos.",
    "timeout": "Reducí el trabajo y evitá bucles o cálculos excesivos.",
    "unclassified": "Comprobá las reglas de la habilidad y el resultado de sus pruebas.",
}


def _path() -> Path:
    return Path(os.environ.get("SKY_REFLECTIVE_DB") or _ROOT / "local_data" / "sky_reflective.sqlite3")


def topic_for(request: str) -> str:
    """Clasificación cerrada; nunca conserva el pedido ni sus palabras."""
    lower = request.casefold() if isinstance(request, str) else ""
    for topic, stems in _TOPICS.items():
        if any(stem in lower for stem in stems):
            return topic
    return "general"


def issue_for(report: dict) -> str:
    """Convierte resultados no confiables en etiquetas seguras; sin texto de errores."""
    if not isinstance(report, dict):
        return "unclassified"
    if report.get("aprobada") is True:
        return "none"
    static = report.get("estatica") or []
    if isinstance(static, list) and static:
        joined = " ".join(str(s)[:160] for s in static[:4]).casefold()
        if "sintaxis" in joined or "syntax" in joined:
            return "syntax"
        if "permitid" in joined or "prohibid" in joined or "import" in joined:
            return "prohibited_code"
        if "función" in joined or "ejecutar(" in joined or "formato" in joined:
            return "invalid_contract"
        return "unclassified"
    error = str(report.get("error", ""))[:160].casefold()
    if "tiempo" in error or "timeout" in error or "time limit" in error:
        return "timeout"
    if error:
        return "sandbox_failure"
    cases = report.get("pruebas")
    if isinstance(cases, list) and any(isinstance(x, dict) and x.get("ok") is False for x in cases):
        return "test_mismatch"
    return "unclassified"


def _vector(topic: str, issue: str) -> list[float]:
    """Vector de características no personalizadas, estable y acotado."""
    if topic not in {*_TOPICS, "general"} or issue not in _ISSUES:
        raise ValueError("Etiquetas reflexivas inválidas")
    vector = [0.0] * _DIMENSIONS
    for key, weight in (("topic:" + topic, 1.0), ("issue:" + issue, 0.25)):
        digest = hashlib.sha256(key.encode("ascii")).digest()
        index = int.from_bytes(digest[:2], "big") % _DIMENSIONS
        vector[index] += weight if digest[2] & 1 else -weight
    length = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [round(v / length, 6) for v in vector]


def _connect():
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("""CREATE TABLE IF NOT EXISTS reflective_experiences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL, issue TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK(outcome IN ('passed_tests', 'failed_tests')),
        vector_json TEXT NOT NULL, observed_at INTEGER NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS reflective_time ON reflective_experiences(observed_at)")
    db.commit()
    return db


def record(request: str, report: dict) -> dict:
    """Persiste sólo evidencia categórica; no escribe código, pruebas, rutas ni prompts."""
    topic = topic_for(request)
    issue = issue_for(report)
    passed = isinstance(report, dict) and report.get("aprobada") is True
    outcome = "passed_tests" if passed else "failed_tests"
    now = int(time.time())
    with _LOCK, closing(_connect()) as db:
        with db:
            db.execute("INSERT INTO reflective_experiences(topic,issue,outcome,vector_json,observed_at) "
                       "VALUES (?,?,?,?,?)",
                       (topic, issue, outcome, json.dumps(_vector(topic, issue)), now))
            db.execute("DELETE FROM reflective_experiences WHERE observed_at < ?", (now - _RETENTION_SECONDS,))
            db.execute("""DELETE FROM reflective_experiences WHERE id IN (
                SELECT id FROM reflective_experiences ORDER BY id DESC LIMIT -1 OFFSET ?)""", (_MAX_ROWS,))
    return {"topic": topic, "issue": issue, "outcome": outcome,
            "model_weights_updated": False, "skill_installed": False}


def recall(request: str, *, limit: int = 2) -> list[dict]:
    """RAG local de etiquetas verificables, nunca fuente de instrucciones ejecutables."""
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("Límite fuera de rango")
    target = _vector(topic_for(request), "none")
    with _LOCK, closing(_connect()) as db:
        rows = db.execute("""SELECT issue, outcome, vector_json, observed_at
                             FROM reflective_experiences WHERE observed_at >= ?
                             ORDER BY id DESC LIMIT 300""", (int(time.time()) - _RETENTION_SECONDS,)).fetchall()
    candidates = []
    for row in rows:
        if row["outcome"] != "failed_tests" or row["issue"] not in _LESSONS:
            continue
        try:
            vector = json.loads(row["vector_json"])
            if not isinstance(vector, list) or len(vector) != _DIMENSIONS:
                continue
            score = sum(float(a) * float(b) for a, b in zip(target, vector))
        except (ValueError, TypeError):
            continue
        if score >= 0.5:
            candidates.append((score, row["observed_at"], row["issue"]))
    seen = set()
    results = []
    for score, _, issue in sorted(candidates, key=lambda x: (x[0], x[1]), reverse=True):
        if issue in seen:
            continue
        seen.add(issue)
        results.append({"issue": issue, "lesson": _LESSONS[issue], "similarity": round(score, 3),
                        "source": "local_failed_test_evidence"})
        if len(results) >= limit:
            break
    return results


def safe_feedback(report: dict) -> str:
    """Diagnóstico seguro para el generador: jamás devuelve datos de pruebas o stack traces."""
    code = issue_for(report)
    return _LESSONS.get(code, "")


def capabilities() -> dict:
    return {"storage": "local_sqlite", "vector": "fixed_feature_hashing_32d",
            "semantic_llm_embeddings": False, "retention_days": 90,
            "stores_raw_prompts_or_errors": False, "runs_generated_code": False,
            "automatic_install": False, "model_weights_updated": False}
