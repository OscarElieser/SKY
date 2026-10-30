"""Puente consultivo de calidad entre SKY Reflexivo y los subagentes.

No ejecuta acciones ni decide permisos. Las lecciones vienen exclusivamente
de etiquetas de fallos en pruebas del Skill Builder, no de datos privados.
Un diagnóstico determinista puede pedir UNA segunda síntesis; no valida hechos.
"""
from __future__ import annotations

import re
import sqlite3

MAX_ADVICE = 2

# Únicamente declaraciones afirmativas de acciones hechas POR SKY, no
# propuestas ni órdenes del usuario. Esta heurística evita falsos éxitos.
_UNVERIFIED_ACTIONS = re.compile(
    r"(?im)(?:^|[.!?]\s+)(?:sky[\s,:-]+)?"
    r"(?:ya\s+)?(?:he\s+|hemos\s+|acabo\s+de\s+|ya\s+)"
    r"(?:instalad[oa]|eliminad[oa]|borrad[oa]|enviad[oa]|publicad[oa]|"
    r"ejecutad[oa]|desplegad[oa]|subid[oa]|modificad[oa]|"
    r"descargad[oa]|abierto|creado|consultado|verificado|"
    r"instal[eé]|borr[eé]|envi[eé]|publiqu[eé]|"
    r"ejecut[eé]|desplegu[eé]|sub[ií]|modifiqu[eé]|"
    r"descargu[eé]|abr[ií]|cre[eé]|consult[eé]|verifiqu[eé])\b"
)
_FALSE_GROUNDING = re.compile(
    r"(?im)(?:^|[.!?]\s+)(?:ya\s+)?(?:investigu[eé]|navegu[eé]|"
    r"busqu[eé]\s+en\s+internet|revis[eé]\s+(?:en\s+)?(?:la\s+)?web)\b"
)


def advice(request: str) -> list[dict]:
    """Consejos agregados de pruebas anteriores, sin prompts, rutas ni texto crudo."""
    if not isinstance(request, str) or len(request) > 4000:
        return []
    try:
        from . import sky_reflective_core as reflex
        topic = reflex.topic_for(request)
        if topic == "general":
            return []
        with reflex._LOCK, reflex._connect() as db:
            rows = db.execute(
                """SELECT issue, COUNT(*) AS n FROM reflective_experiences
                   WHERE topic = ? AND outcome = 'failed_tests'
                     AND observed_at >= ?
                   GROUP BY issue ORDER BY n DESC, issue LIMIT ?""",
                (topic, int(reflex.time.time()) - reflex._RETENTION_SECONDS, MAX_ADVICE)
            ).fetchall()
        return [
            {"category": row["issue"], "check": reflex._LESSONS[row["issue"]],
             "source": "skill_builder_test_failure"}
            for row in rows if row["issue"] in reflex._LESSONS
        ]
    except (OSError, sqlite3.Error, ValueError):
        return []


def assess(answer: str) -> dict:
    """Gate de afirmaciones de ejecución ficticia; no es fact-check académico."""
    if not isinstance(answer, str) or not answer.strip():
        return {"accepted": False, "reason": "empty", "verified_facts": False}
    if _UNVERIFIED_ACTIONS.search(answer) or _FALSE_GROUNDING.search(answer):
        return {"accepted": False, "reason": "unverified_execution_claim", "verified_facts": False}
    return {"accepted": True, "reason": "no_unverified_execution_claim_detected",
            "verified_facts": False}


def repair_instruction() -> str:
    return ("Reescribí únicamente la síntesis anterior, sin añadir datos nuevos. "
            "Tu respuesta afirmó haber ejecutado acciones o consultado fuentes "
            "sin herramientas ni evidencias. Reemplazá esas afirmaciones por "
            "orientaciones o limitaciones explícitas. Nunca inventés resultados.")


def capabilities() -> dict:
    return {
        "role": "consultive_quality_gate",
        "quality_lessons": "anonymized_builder_test_categories",
        "repair_attempts_max": 1,
        "device_actions_allowed": False,
        "model_training": False,
        "fact_checker": False,
        "external_research": False,
    }
