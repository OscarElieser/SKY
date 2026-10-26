"""Diagnóstico honesto de escucha continua de SKY.

Un servicio/archivo existente NO prueba que el micrófono esté capturando audio.
Comprobamos latido del consumidor de audio y llegada reciente de frames;
no se conserva contenido grabado.
"""
from __future__ import annotations

import time


def resumen_escucha(estado: dict, ahora: float | None = None) -> dict:
    ahora = time.time() if ahora is None else float(ahora)
    if not isinstance(estado, dict):
        estado = {}

    def antiguedad(clave: str) -> float | None:
        try:
            marca = float(estado.get(clave) or 0)
        except (ValueError, TypeError, OverflowError):
            return None
        delta = ahora - marca
        return round(delta, 1) if marca > 0 and 0 <= delta <= 86400 else None

    latido = antiguedad('last_seen')
    audio = antiguedad('last_audio')
    proceso = (
        bool(estado.get('hands_free_listening'))
        and estado.get('status') != 'stopped'
        and latido is not None and latido <= 15.0
    )
    microfono = bool(proceso and audio is not None and audio <= 15.0)
    return {
        'escucha_continua': microfono,
        'consumiendo_audio': proceso,
        'microfono_recibiendo_audio': microfono,
        'escucha_natural_sin_sky': bool(microfono and estado.get('wordless_active')),
        'segundos_desde_latido': latido,
        'segundos_desde_audio': audio,
        'aviso': (
            'Escucha y entrada de micrófono verificadas recientemente.'
            if microfono else
            'Servicio activo, pero sin audio reciente del micrófono.'
            if proceso else
            'No se ha confirmado escucha activa reciente. Revisá el servicio de voz.'
        ),
    }
