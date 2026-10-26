"""Ruta ultrarrápida para órdenes locales EXACTAS y de bajo riesgo.

No ejecuta herramientas, no concede permisos y no consulta modelos de IA.
La API entrega la propuesta al mismo _completar() autenticado de siempre.
Si el texto incluye más de una instrucción, no aplica el atajo.
"""
from __future__ import annotations

import re
import unicodedata


def _normalizar(texto: str) -> str:
    letras = unicodedata.normalize("NFKD", texto.casefold())
    limpio = "".join(c for c in letras if not unicodedata.combining(c))
    limpio = re.sub(r"^[\s]*(?:oye|hey|ok)\s+sky[\s,.:;!¡]*", "", limpio)
    limpio = re.sub(r"^[\s]*sky[\s,.:;!¡]*", "", limpio)
    limpio = re.sub(r"[.,:;!?¡¿]+", " ", limpio)
    return " ".join(limpio.split())


# No incluir comandos destructivos, de comunicaciones, ni de privacidad.
_APLICACIONES = {
    "word": "word",
    "excel": "excel",
    "powerpoint": "powerpoint",
    "power point": "powerpoint",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "edge",
    "spotify": "spotify",
    "vlc": "vlc",
    "visual studio code": "vscode",
    "vs code": "vscode",
}
_MULTIMEDIA = {
    "pausa": "play_pause",
    "pausar": "play_pause",
    "pausa la musica": "play_pause",
    "pausa el video": "play_pause",
    "reanuda la musica": "play_pause",
    "siguiente cancion": "next",
    "siguiente pista": "next",
    "anterior cancion": "previous",
    "cancion anterior": "previous",
}
_VOLUMEN = {
    "silencia": "mute",
    "silenciar": "mute",
    "silencia el sonido": "mute",
    "sube el volumen": "up",
    "subi el volumen": "up",
    "baja el volumen": "down",
    "bajá el volumen": "down",
}


def accion_directa(texto: str) -> dict | None:
    """Reconoce sólo comandos completos. El agente valida permisos por separado."""
    if not isinstance(texto, str) or len(texto) > 140:
        return None
    frase = _normalizar(texto)
    app = re.fullmatch(r"(?:abre|abri|abrir) (.+)", frase)
    if app and app.group(1) in _APLICACIONES:
        identificador = _APLICACIONES[app.group(1)]
        return {
            "action": "launch_app",
            "params": {"app": identificador},
            "description": "Abrir " + app.group(1),
        }
    if frase in _MULTIMEDIA:
        return {
            "action": "media_control",
            "params": {"command": _MULTIMEDIA[frase]},
            "description": "Controlar reproducción",
        }
    if frase in _VOLUMEN:
        return {
            "action": "volume",
            "params": {"command": _VOLUMEN[frase]},
            "description": "Controlar volumen",
        }
    return None
