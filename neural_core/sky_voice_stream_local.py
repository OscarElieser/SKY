"""Primeras frases habladas de SKY sin esperar el texto completo de Ollama.

Ruta opcional para consultas públicas de voz aisladas. Nunca ejecuta
herramientas, no solicita claves ni envía mensajes a proveedores externos.
La misma política del agente aplica a las órdenes en sky_manos_libres.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
import time
from typing import Callable, Iterable


@dataclass(frozen=True)
class VoiceStreamResult:
    ok: bool
    text: str = ""
    spoken: bool = False
    first_tts_s: float | None = None
    error: str = ""


def eligible(text: str, history: list[dict] | None = None) -> bool:
    """Opt-in deliberado. La función requiere además el modo local breve."""
    if os.getenv("SKY_VOICE_STREAM_LOCAL", "0").lower() not in ("1", "true", "yes", "si"):
        return False
    from .sky_cerebro import contexto_local_breve
    return contexto_local_breve(text, history)


def _next_phrase(buffer: str, final: bool = False) -> tuple[str, str]:
    """Entrega una frase completa o un tramo acotado sin romper palabras."""
    if not buffer:
        return "", ""
    punctuation = re.search(r"[.!?](?:\s|$)", buffer)
    if punctuation and punctuation.end() >= 20 and punctuation.end() <= 150:
        end = punctuation.end()
        return buffer[:end].strip(), buffer[end:].lstrip()
    if len(buffer) >= 140:
        end = buffer.rfind(" ", 25, 140)
        if end > 0:
            return buffer[:end].strip(), buffer[end:].lstrip()
    if final:
        return buffer.strip(), ""
    return "", buffer


def speak_stream(
    text: str,
    speak: Callable[[str], None],
    *,
    cancelled: Callable[[], bool],
    events: Iterable[tuple[str, object]] | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> VoiceStreamResult:
    """Consume deltas y envía frases al TTS serial sin acciones de dispositivo.

    El trabajador del micrófono y la cola de órdenes permanecen independientes.
    Se mide el instante del PRIMER ENVÍO al TTS, no el primer audio audible.
    Si la respuesta falla después de hablar, nunca se solicita otra respuesta
    automáticamente: eso podría repetir voz o ejecutar una propuesta tardía.
    """
    if events is None:
        from . import sky_cerebro
        # El contexto local breve se valida ANTES de llamar esta función.
        # El preferido dura solo este turno en el único worker de voz.
        sky_cerebro.preferir("ollama")
        try:
            yield_events = sky_cerebro.decidir_eventos(text, modo="voz")
            return _consume(yield_events, speak, cancelled=cancelled, clock=clock)
        finally:
            sky_cerebro.preferir(None)
    return _consume(events, speak, cancelled=cancelled, clock=clock)


def _consume(
    events: Iterable[tuple[str, object]],
    speak: Callable[[str], None],
    *,
    cancelled: Callable[[], bool],
    clock: Callable[[], float],
) -> VoiceStreamResult:
    start = clock()
    first_s: float | None = None
    spoken = False
    buffer = ""
    complete = ""
    done = False

    def speak_part(phrase: str) -> None:
        nonlocal first_s, spoken
        if phrase and not cancelled():
            if first_s is None:
                first_s = max(0.0, clock() - start)
            speak(phrase)
            spoken = True

    iterator = iter(events)
    try:
        for kind, payload in iterator:
            if cancelled():
                return VoiceStreamResult(False, spoken=spoken, first_tts_s=first_s, error="cancelled")
            if kind == "herramienta":
                # Nunca ejecutar propuestas inesperadas a través de este canal.
                return VoiceStreamResult(False, spoken=spoken, first_tts_s=first_s, error="tool_not_permitted")
            if kind == "error":
                return VoiceStreamResult(False, spoken=spoken, first_tts_s=first_s, error="inference_error")
            if kind == "delta":
                chunk = str(payload or "")
                buffer += chunk
                while True:
                    phrase, remainder = _next_phrase(buffer)
                    if not phrase:
                        break
                    buffer = remainder
                    speak_part(phrase)
                    if cancelled():
                        return VoiceStreamResult(False, spoken=spoken, first_tts_s=first_s, error="cancelled")
            if kind == "fin":
                complete = str(payload or "").strip()
                done = True
                break
    finally:
        closer = getattr(iterator, "close", None)
        if callable(closer):
            closer()
    if not done or not complete or cancelled():
        return VoiceStreamResult(False, spoken=spoken, first_tts_s=first_s,
                                 error="cancelled" if cancelled() else "incomplete")
    phrase, _ = _next_phrase(buffer, final=True)
    speak_part(phrase)
    return VoiceStreamResult(True, text=complete, spoken=spoken, first_tts_s=first_s)
