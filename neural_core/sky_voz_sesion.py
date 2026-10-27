"""Puerta de voz de la sesión del dueño (v12.6) — lo que la escucha manos libres hace ANTES de obedecer.

Recorrido: micrófono → Vosk (local) → **esta puerta** → interpretación → autorización del agente → respuesta hablada.

  * Con PIN configurado y la sesión bloqueada, la única frase que se procesa es el PIN (dígitos dichos de a uno:
    «cuatro siete dos …») y la parada de emergencia (que la escucha atiende antes de llegar acá).
  * El PIN se convierte a dígitos localmente y se compara con el verificador scrypt de SENTINEL. Ni el audio ni la
    transcripción se guardan, imprimen ni envían a la IA.
  * «SKY, bloquéate» vuelve a bloquear todo SKY (voz, HUD, WhatsApp, agente).
  * Conocer el PIN no identifica a quien habla: alguien que lo escuche o lo grabe puede repetirlo. Por eso lo crítico
    (nivel 3, correos, cerraduras) sigue pidiendo confirmación en la pantalla.
"""
from __future__ import annotations

import re
import time

from .sentinel_identidad import (bloquear_sesion, desbloquear_sesion, estado_sesion, pin_configurado,
                                 pin_desde_voz)
from .sky_aprendizaje import _norm

PREGUNTA = '¿Cuál es tu PIN?'
_BLOQUEO = re.compile(r'^(?:sky )?(?:bloqueate|bloquea (?:a )?sky|bloquear sky|bloquea la sesion|cierra la sesion)$')
_PARECE_NUMERO = re.compile(r'\b(?:cero|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|'
                            r'catorce|quince|veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|'
                            r'mil|pin|\d+)\b')


def es_orden_bloqueo(texto: str) -> bool:
    return bool(_BLOQUEO.match(_norm(texto)))


class PuertaVoz:
    """Decide qué hacer con una frase ya reconocida. `evaluar` devuelve None si la frase sigue el camino normal."""

    def __init__(self, reloj=time.monotonic, aviso_cada: float = 12.0):
        self._reloj = reloj
        self._aviso_cada = aviso_cada
        self._ultimo_aviso = -1e9

    def bloqueada(self) -> bool:
        try:
            return bool(estado_sesion()['bloqueada'])
        except Exception:
            return True

    def saludo_inicial(self) -> str | None:
        """Qué decir al arrancar la escucha."""
        if not pin_configurado():
            return None
        return PREGUNTA if self.bloqueada() else None

    def evaluar(self, frase: str, orden_tras_activacion: str | None) -> dict | None:
        """frase: lo que reconoció Vosk; orden_tras_activacion: el texto después de «SKY» (None si no dijo SKY).
        Resultado: {'decir': str|None, 'desbloqueada': bool, 'bloqueada': bool, 'privado': True}."""
        if not self.bloqueada():
            return None
        candidato = orden_tras_activacion if orden_tras_activacion is not None else frase
        if es_orden_bloqueo(candidato):
            return {'decir': 'SKY ya está bloqueada. ' + PREGUNTA, 'desbloqueada': False, 'bloqueada': True, 'privado': True}
        pin = pin_desde_voz(candidato)
        if pin:
            r = desbloquear_sesion(pin, 'voz')
            pin = None   # no conservar el PIN más de lo necesario
            mensaje = r['mensaje'] + (f" Te quedan {r['restantes']} intentos." if 'restantes' in r else '')
            return {'decir': mensaje, 'desbloqueada': bool(r['ok']), 'bloqueada': not r['ok'], 'privado': True}
        # Si te dirigiste a SKY (o dijiste números que no forman un PIN válido), recordarle qué falta, sin insistir.
        dirigido = orden_tras_activacion is not None or bool(_PARECE_NUMERO.search(_norm(frase)))
        ahora = self._reloj()
        if dirigido and ahora - self._ultimo_aviso >= self._aviso_cada:
            self._ultimo_aviso = ahora
            return {'decir': 'SKY está bloqueada. ' + PREGUNTA + ' Decí los dígitos de a uno.',
                    'desbloqueada': False, 'bloqueada': True, 'privado': True}
        return {'decir': None, 'desbloqueada': False, 'bloqueada': True, 'privado': True}

    def bloquear_por_voz(self, orden: str) -> dict | None:
        """Con la sesión abierta: «SKY, bloquéate» bloquea todo SKY. None si no es esa orden."""
        if not es_orden_bloqueo(orden):
            return None
        if bloquear_sesion('pedido por voz', 'voz'):
            return {'decir': 'SKY bloqueada. ' + PREGUNTA + ' cuando quieras volver.'}
        return {'decir': 'Para bloquear SKY primero configurá un PIN: python sky_pin.py configurar.'}
