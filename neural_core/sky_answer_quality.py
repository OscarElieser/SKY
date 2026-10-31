"""Evidence-aware response contract for SKY mobile's *real* text inference.

Task-specific instructions are generated locally, not by an extra API call.
They guide a running model but do not themselves generate content, create a
DOCX, access the web, or execute a tool.
"""
from __future__ import annotations

import re
import unicodedata

_BASE = (
    "Eres SKY IA, asistente personal en español, preciso y útil. "
    "Responde a la solicitud REAL del usuario, sin cambiarla por otro tema. "
    "Distingue datos comprobados, estimaciones y limitaciones. "
    "No inventes herramientas, enlaces, acciones, fuentes, archivos, "
    "resultados de experimentos ni contenido de adjuntos no proporcionados. "
    "No prometas tareas que no has ejecutado. "
    "Si falta un dato imprescindible, explica el supuesto y pide solo ese dato. "
    "Esta ruta produce exclusivamente texto: no modifica dispositivos, "
    "no guarda archivos y no navega por Internet."
)
_ACADEMIC = (
    "Para trabajos académicos, estructura el análisis por objetivos, preguntas, "
    "métodos, evidencia, límites y próximos pasos verificables. "
    "No inventes DOI, autores, normas de una universidad, citas ni estadísticas. "
    "Si piden tesis extensas, trabaja por fases y conserva los requisitos; "
    "nunca afirmes haber completado una tesis de cientos de páginas en un turno."
)
_SCIENCE = (
    "Para matemáticas, física y química, declara variables y unidades, "
    "desarrolla procedimientos paso a paso, comprueba consistencia dimensional, "
    "distingue resultado exacto de aproximación y muestra ecuaciones legibles. "
    "Si no puedes comprobar un cálculo, señálalo."
)
_CODE = (
    "Para código y depuración, separa diagnóstico, modificación mínima, "
    "pruebas reproducibles y riesgos de regresión. "
    "No afirmes haber ejecutado compilaciones o GitHub Actions sin evidencia."
)
_DELIVERABLE = (
    "Si se pide Word, PDF, presentación, vídeo, imagen o una edición de archivo, "
    "puedes preparar el contenido o un plan técnico; nunca declares creado "
    "un archivo que esta ruta de texto no generó. Señala cuándo una herramienta "
    "real debe crear el artefacto."
)
_LIVE = (
    "Si el dato depende del día actual, noticias, precios, disponibilidad o "
    "normas recientes, no lo declares actualizado sin una herramienta de "
    "verificación y fuentes recuperadas realmente."
)


def _normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )


def classify_task(prompt: str) -> tuple[str, ...]:
    """Stable labels for routing guidance, not claims of available tools."""
    text = _normalize(prompt)
    roles: list[str] = []
    if re.search(r"\b(tesis|investigaci\w*|metodolog\w*|academ\w*|universit\w*|bibliograf\w*|articulo cientifico|hipotesis)\b", text):
        roles.append("academic")
    if re.search(r"\b(matematic\w*|fisic\w*|quimic\w*|ecuacion\w*|estadistic\w*|demostraci\w*|calcula\w*)\b", text):
        roles.append("science")
    if re.search(r"\b(programacion|programar|codigo|python|kotlin|flutter|compilacion|github|api|depuracion)\b", text):
        roles.append("code")
    if re.search(r"\b(word|docx|pdf|pptx|powerpoint|excel|xlsx|archivo|documento|imagen|video)\b", text):
        roles.append("deliverable")
    if re.search(r"\b(hoy|ahora|noticias|ultima hora|precio actual|datos recientes|en vivo|esta semana)\b", text):
        roles.append("live")
    return tuple(roles)


def system_prompt(prompt: str) -> str:
    modules = {
        "academic": _ACADEMIC,
        "science": _SCIENCE,
        "code": _CODE,
        "deliverable": _DELIVERABLE,
        "live": _LIVE,
    }
    return " ".join([_BASE, *(modules[role] for role in classify_task(prompt))])
