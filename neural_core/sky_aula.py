"""SKY Aula: interactive stepwise teaching, evidence-labelled content, voice-ready.

No student personal data, no synthetic "official curriculum" claims, no
clinical advice, no unsupported grading. Lessons remain in volatile memory,
expire after 90 minutes, and are not used to retrain the model.
"""
from __future__ import annotations

import re
import secrets
import threading
import time
from typing import Any

from . import sky_evidence_lab as evidence

LEVELS = {
    "inicial": {
        "label": "Educación inicial — MEIDI",
        "method": "juego, exploración, movimiento, lenguaje oral, afectividad e imágenes",
        "assessment": "observación cualitativa de participación y desarrollo",
        "source": "mined_meidi",
        "age_notes": "acciones breves y supervisión de una persona adulta",
    },
    "primaria": {
        "label": "Educación primaria",
        "method": "experiencias concretas, preguntas guiadas, ejemplos cercanos y práctica",
        "assessment": "explicación con palabras propias, práctica y retroalimentación formativa",
        "source": "mined_primaria",
        "age_notes": "usar ejemplos apropiados a grado y diversidad de ritmos",
    },
    "secundaria": {
        "label": "Educación secundaria/media",
        "method": "análisis, diálogo, resolución de problemas y pensamiento crítico",
        "assessment": "argumentos, ejercicios, autoevaluación y revisión de evidencias",
        "source": "mined_secundaria",
        "age_notes": "no simplificar sin atender la complejidad curricular",
    },
    "tecnico": {
        "label": "Formación técnica y cursos profesionales",
        "method": "demostración, práctica por competencias, seguridad y aplicación laboral",
        "assessment": "desempeño demostrado con instrumentos/rúbrica del programa",
        "source": "inatec_portal",
        "age_notes": "comprobar requisitos de seguridad específicos de cada oficio",
    },
    "universitario": {
        "label": "Educación superior / licenciatura",
        "method": "estudio de casos, análisis de literatura, laboratorio cuando corresponda",
        "assessment": "resolución fundada y discusión con fuentes académicas",
        "source": None,
        "age_notes": "evitar fuentes no contrastadas",
    },
    "maestria": {
        "label": "Maestría",
        "method": "seminario, debates metodológicos, síntesis de evidencia y casos",
        "assessment": "lectura crítica, protocolo o aplicación argumentada",
        "source": None,
        "age_notes": "afirmaciones y bibliografía deben poder auditarse",
    },
    "doctorado": {
        "label": "Doctorado / investigación avanzada",
        "method": "preguntas originales, metodología, revisión crítica y reproducibilidad",
        "assessment": "defensa de hipótesis, límites, sesgos y replicabilidad",
        "source": None,
        "age_notes": "no inventar hallazgos, resultados ni artículos",
    },
}
STAGES = (
    ("bienvenida", "Conexión y propósito", 0.08),
    ("saberes", "Explorar conocimientos previos", 0.12),
    ("explicacion", "Explicación por partes", 0.24),
    ("demostracion", "Demostración o ejemplo", 0.16),
    ("practica", "Práctica interactiva", 0.20),
    ("reflexion", "Comprobar comprensión", 0.12),
    ("cierre", "Síntesis y próxima actividad", 0.08),
)
_LOCK = threading.RLock()
_SESSIONS: dict[str, dict] = {}
_TTL = 90 * 60
_MAX_SESSIONS = 60


def _clean(value: str, maximum: int, label: str, minimum: int = 4) -> str:
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f"{label}: ingresá de {minimum} a {maximum} caracteres.")
    text = " ".join(value.strip().split())
    if any(ord(c) < 32 for c in text):
        raise ValueError("No se permiten caracteres de control.")
    return text


def lesson(topic: str, level: str, duration_minutes: int = 45,
           learning_goal: str = "", reference_text: str = "",
           grade: str = "") -> dict[str, Any]:
    if level not in LEVELS:
        raise ValueError("Nivel educativo no reconocido.")
    if not isinstance(duration_minutes, int) or not 15 <= duration_minutes <= 180:
        raise ValueError("La clase debe durar entre 15 y 180 minutos.")
    topic = _clean(topic, 160, "Tema")
    if len(reference_text) > 12000 or not isinstance(reference_text, str):
        raise ValueError("El material de referencia debe ser menor a 12.000 caracteres.")
    grade = _clean(grade, 55, "Grado o curso", 0) if grade else ""
    goal = _clean(learning_goal, 250, "Aprendizaje esperado") if learning_goal else ""
    spec = LEVELS[level]
    source = evidence.OFFICIAL_REGISTRY.get(spec["source"]) if spec["source"] else None
    has_material = bool(reference_text.strip())
    remaining = duration_minutes
    stages = []
    for i, (ident, name, fraction) in enumerate(STAGES):
        minutes = remaining if i == len(STAGES)-1 else max(1, round(duration_minutes*fraction))
        remaining -= minutes
        stages.append({"id":ident,"name":name,"minutes":minutes,
                       "requires_material_for_factual_explanation":
                           ident in {"explicacion","demostracion"} and not has_material})
    return {
        "central_agent": "SKY",
        "level": level, "level_label":spec["label"],
        "grade":grade, "topic":topic,
        "duration_minutes":duration_minutes,
        "goal":goal or "Propuesta docente pendiente de definir según el programa oficial.",
        "goal_verified_against_curriculum":False,
        "method":spec["method"],
        "assessment_method":spec["assessment"],
        "notes":spec["age_notes"],
        "stages":stages,
        "material_supplied":has_material,
        "source_trust":"user_provided_unverified" if has_material else "not_provided",
        "official_source_reference": (
            {"url":source["url"],"label":source["label"],"status":"reference_only_not_fetched"}
            if source else None),
        "lesson_ready_to_teach_verified_facts":False,
        "speak_supported_by_client":True,
        "speech_engine_status":"client_must_verify_available_speech_synthesis",
        "child_data_collected":False,
        "evidence_gaps":([
            "Falta contenido didáctico respaldado por fuentes y el programa oficial."
        ] if not has_material else [
            "El texto aportado todavía no fue contrastado con fuentes oficiales."
        ]),
    }


def _intro(spec: dict, stage: str, content: str) -> tuple[str, str]:
    topic, level = spec["topic"], spec["level"]
    objective = spec["goal"]
    if stage == "bienvenida":
        return (
            f"¡Hola! Soy SKY, y vamos a aprender sobre {topic}. "
            f"Hoy nuestra meta es: {objective} "
            "Vamos paso a paso; podés pedirme que repita o continúe.",
            f"¿Qué te gustaría descubrir sobre {topic}?"
        )
    if stage == "saberes":
        return (
            f"Antes de comenzar, pensemos qué conocemos sobre {topic}. "
            "No importa si todavía no sabés la respuesta.",
            f"¿Dónde has observado o escuchado hablar de {topic}?"
        )
    if stage == "explicacion":
        if not content:
            return (
                f"Voy a ayudarte a estudiar {topic}; antes de explicar datos concretos, "
                "necesito el texto, el material del curso o una fuente contrastada. "
                "No quiero darte información inventada.",
                "¿Podés facilitarme el contenido o el aprendizaje esperado?"
            )
        return (
            f"Comencemos con el material que compartiste sobre {topic}. "
            "Este contenido todavía necesita verificarse con la fuente curricular. "
            f"Leamos un fragmento: {content[:700]} "
            "Ahora revisemos la idea principal con calma.",
            "¿Cómo explicarías con tus palabras la idea central de ese fragmento?"
        )
    if stage == "demostracion":
        if not content:
            return (
                "Prepararemos un ejemplo o una demostración cuando tengamos "
                "material confiable. No voy a inventar fórmulas, datos ni experimentos.",
                f"¿Qué ejemplo real de {topic} podés aportar?"
            )
        return (
            f"Para aplicar {topic}, seleccioná un caso del material aportado. "
            "Primero identificá los datos; después explicá qué operación, "
            "argumento o procedimiento corresponde; finalmente comprobá tu resultado.",
            "¿Cuál de esos pasos necesitarías revisar nuevamente?"
        )
    if stage == "practica":
        activities = {
            "inicial":"dibujá, señalá o representá la idea mediante un juego breve",
            "primaria":"realizá un ejemplo concreto y explicá cada decisión",
            "secundaria":"resolvé una situación y justificá tus pasos",
            "tecnico":"describí el procedimiento seguro y los criterios para comprobarlo",
            "universitario":"aplicá el concepto a un caso y justificá la fuente",
            "maestria":"contrastá dos enfoques y sus limitaciones",
            "doctorado":"formulá una hipótesis y explicá cómo podrías refutarla",
        }
        return (
            f"Ahora es tu turno: sobre {topic}, {activities[level]}. "
            "No compartiré respuestas privadas de estudiantes y no calificaré sin una rúbrica validada.",
            "¿Qué solución proponés y cómo la comprobarías?"
        )
    if stage == "reflexion":
        return (
            f"Revisemos lo aprendido sobre {topic}. "
            "Busquemos lo que quedó claro, lo que necesita práctica y "
            "las dudas que vamos a verificar con fuentes.",
            "¿Qué comprendiste y qué parte todavía te parece difícil?"
        )
    return (
        f"¡Terminamos esta sesión sobre {topic}! "
        "Resumí las ideas principales con tus propias palabras y "
        "elegí una actividad sencilla para continuar aprendiendo.",
        "¿Qué te gustaría estudiar en nuestra próxima clase?"
    )


def stage_output(plan: dict, index: int) -> dict:
    if not 0 <= index < len(STAGES):
        raise ValueError("Etapa de clase no encontrada.")
    ident, name, _ = STAGES[index]
    speech, question = _intro(plan, ident, plan.get("_source_text", ""))
    return {
        "central_agent":"SKY",
        "stage_number":index+1,"total_stages":len(STAGES),
        "stage_id":ident,"stage_name":name,
        "minutes":plan["stages"][index]["minutes"],
        "voice_ready_text":speech,"question":question,
        "speech_audio_generated":False,
        "may_speak_using_browser_tts":True,
        "requires_human_evaluation":True,
        "knowledge_from_verified_source":False,
        "message":speech,
    }


def _prune():
    now=time.monotonic()
    for ident in list(_SESSIONS):
        if now-_SESSIONS[ident]["updated"] > _TTL:
            del _SESSIONS[ident]


def start(topic: str, level: str, duration_minutes: int=45,
          learning_goal: str="", reference_text: str="", grade: str="") -> dict:
    plan=lesson(topic, level, duration_minutes, learning_goal, reference_text, grade)
    with _LOCK:
        _prune()
        if len(_SESSIONS)>=_MAX_SESSIONS:
            raise RuntimeError("Hay demasiadas clases activas. Cerrá sesiones antiguas.")
        ident="lesson_"+secrets.token_hex(12)
        _SESSIONS[ident]={
            "plan":{**plan,"_source_text":reference_text.strip()[:12000]},
            "index":0,"updated":time.monotonic(),
        }
    return {"lesson_id":ident,"status":"active","step":stage_output(_SESSIONS[ident]["plan"],0),
            "plan":plan,"privacy":"in_memory_ttl_90_minutes_no_student_pii"}


def next_stage(ident: str) -> dict:
    with _LOCK:
        _prune()
        session=_SESSIONS.get(ident)
        if not session:
            raise KeyError("La sesión expiró o no existe.")
        if session["index"]>=len(STAGES)-1:
            return {"lesson_id":ident,"status":"completed","no_more_steps":True}
        session["index"]+=1
        session["updated"]=time.monotonic()
        return {"lesson_id":ident,"status":"active",
                "step":stage_output(session["plan"],session["index"])}


def current(ident: str) -> dict:
    with _LOCK:
        _prune()
        session=_SESSIONS.get(ident)
        if not session:
            raise KeyError("Clase inexistente o expirada.")
        session["updated"]=time.monotonic()
        return {"lesson_id":ident,"status":"active",
                "step":stage_output(session["plan"],session["index"])}


def end(ident: str) -> bool:
    with _LOCK:
        return _SESSIONS.pop(ident,None) is not None


def catalogue() -> dict:
    return {
        "central_agent":"SKY",
        "levels":[{"id":k,"label":v["label"],"method":v["method"]} for k,v in LEVELS.items()],
        "stages":[{"id":x[0],"name":x[1]} for x in STAGES],
        "supports_any_subject_with_verified_material":True,
        "automatic_curriculum_verification":False,
        "independent_live_voice_output":False,
        "voice_ready_text":True,
        "safe_for_minors": "no_student_data_collected_or_persisted",
        "medical_instruction":"educational_only_no_diagnosis_or_treatment",
    }
