"""Texto pronunciable para TTS de Windows; el mensaje escrito NO se modifica.

El motor de voz recibe únicamente una copia limpia: mantiene las pausas y
los decimales, pero no verbaliza Markdown, URL ni símbolos decorativos.
"""
from __future__ import annotations

import re
import unicodedata


def preparar_voz(texto: str) -> str:
    spoken = str(texto or "")
    if not spoken.strip():
        return ""
    # Nunca leer código de pantalla ni direcciones web en voz alta.
    spoken = re.sub(r"```[\s\S]*?```", " Código disponible en pantalla. ", spoken)
    spoken = re.sub(r"\[([^\]\n]{1,150})\]\(https?://[^)\s]+\)", r"\1", spoken)
    spoken = re.sub(r"https?://\S+", " un enlace ", spoken)
    spoken = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", spoken)
    spoken = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", spoken)
    # Los párrafos dan una pequeña pausa, sin decir "salto de línea".
    spoken = re.sub(r"\n\s*\n+", ". ", spoken)
    spoken = spoken.replace("\n", ". ")
    spoken = re.sub(r"\*\*|__|~~|[`#*_>|~{}\[\]<>«»]", " ", spoken)
    spoken = re.sub(r"[¿¡]", "", spoken)
    # Conservar coma/punto para entonación y números: 3,14; 1.500.
    spoken = "".join(
        " " if unicodedata.category(char) in ("So", "Sk") else char
        for char in spoken
    )
    spoken = re.sub(r"\s+([,.!?;:])", r"\1", spoken)
    spoken = re.sub(r"\s+", " ", spoken).strip()
    spoken = re.sub(r"(?:\.\s*){2,}", ". ", spoken)
    return spoken.strip()
