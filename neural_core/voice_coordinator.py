"""Coordinador de turnos y conversación natural bidireccional para SKY-IA.

Gestiona:
- Estados oficiales del coordinador de voz.
- Tres modos de interacción:
    A) Conversación Natural (manos libres continuo, VAD, barge-in / interrupciones).
    B) Micrófono Manual (grabación controlada por botón, push-to-talk, respuesta hablada).
    C) Chat Escrito (modo texto flotante sin pérdida de contexto ni tareas).
- Retención de contexto conversacional (reproductor activo, documento activo, referencias anafóricas).
- Manejo de interrupciones (cancelación de habla de SKY al hablar el usuario).
- Supresión de eco y prevención de autorreconocimiento.
- Controles conversacionales: velocidad, repetición de último turno, pausa y finalización.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class VoiceState(str, Enum):
    ESPERANDO_ACTIVACION = "ESPERANDO_ACTIVACION"
    ESCUCHANDO = "ESCUCHANDO"
    PROCESANDO = "PROCESANDO"
    RESPONDIENDO = "RESPONDIENDO"
    EJECUTANDO_HERRAMIENTA = "EJECUTANDO_HERRAMIENTA"
    ESPERANDO_SIGUIENTE_INTERVENCION = "ESPERANDO_SIGUIENTE_INTERVENCION"
    PAUSADO = "PAUSADO"


class InteractionMode(str, Enum):
    MODO_A_NATURAL = "MODO_A_NATURAL"    # Manos libres continuo, turnos automáticos
    MODO_B_MANUAL = "MODO_B_MANUAL"      # Micrófono bajo demanda (push-to-talk)
    MODO_C_TEXTO = "MODO_C_TEXTO"        # Chat escrito sin perder contexto


@dataclass
class ConversationalContext:
    active_mode: InteractionMode = InteractionMode.MODO_A_NATURAL
    current_state: VoiceState = VoiceState.ESPERANDO_ACTIVACION
    last_user_utterance: str = ""
    last_assistant_response: str = ""
    last_activity_time: float = field(default_factory=time.time)
    session_timeout_seconds: float = 35.0  # Ventana de diálogo continuo sin reactivación
    is_session_active: bool = False
    is_speaking: bool = False
    interrupt_flag: bool = False
    speech_rate: float = 1.0  # 1.0 normal, 0.8 más despacio, etc.
    active_player: Optional[Dict[str, Any]] = None
    active_document: Optional[Dict[str, Any]] = None
    history: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_mode": self.active_mode.value,
            "current_state": self.current_state.value,
            "last_user_utterance": self.last_user_utterance,
            "last_assistant_response": self.last_assistant_response,
            "last_activity_time": self.last_activity_time,
            "session_timeout_seconds": self.session_timeout_seconds,
            "is_session_active": self.is_session_active,
            "is_speaking": self.is_speaking,
            "speech_rate": self.speech_rate,
            "active_player": self.active_player,
            "active_document": self.active_document,
            "history_length": len(self.history),
        }


class VoiceCoordinator:
    """Coordinador singleton para sincronizar el motor de audio, la UI y el agente local."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._context = ConversationalContext()
        self._state_file = Path(__file__).resolve().parent.parent / "local_data" / "voice_coordinator_state.json"
        self._persist_state()

    def set_mode(self, mode: InteractionMode) -> None:
        with self._lock:
            self._context.active_mode = mode
            if mode == InteractionMode.MODO_A_NATURAL:
                self._context.current_state = VoiceState.ESPERANDO_ACTIVACION
            elif mode == InteractionMode.MODO_B_MANUAL:
                self._context.current_state = VoiceState.ESPERANDO_ACTIVACION
            elif mode == InteractionMode.MODO_C_TEXTO:
                self._context.current_state = VoiceState.ESPERANDO_SIGUIENTE_INTERVENCION
            self._persist_state()

    def get_mode(self) -> InteractionMode:
        with self._lock:
            return self._context.active_mode

    def set_state(self, state: VoiceState) -> None:
        with self._lock:
            self._context.current_state = state
            self._context.last_activity_time = time.time()
            self._persist_state()

    def get_state(self) -> VoiceState:
        with self._lock:
            return self._context.current_state

    def start_listening(self) -> None:
        with self._lock:
            self._context.current_state = VoiceState.ESCUCHANDO
            self._context.interrupt_flag = False
            self._persist_state()

    def stop_listening(self) -> None:
        with self._lock:
            if self._context.current_state == VoiceState.ESCUCHANDO:
                self._context.current_state = VoiceState.ESPERANDO_SIGUIENTE_INTERVENCION
            self._persist_state()

    def set_speaking(self, speaking: bool) -> None:
        with self._lock:
            self._context.is_speaking = speaking
            if speaking:
                self._context.current_state = VoiceState.RESPONDIENDO
                self._context.interrupt_flag = False
            else:
                if self._context.is_session_active:
                    self._context.current_state = VoiceState.ESPERANDO_SIGUIENTE_INTERVENCION
                else:
                    self._context.current_state = VoiceState.ESPERANDO_ACTIVACION
            self._persist_state()

    def interrupt(self) -> None:
        """El usuario interrumpe a SKY mientras está hablando (barge-in)."""
        with self._lock:
            self._context.interrupt_flag = True
            self._context.is_speaking = False
            self._context.current_state = VoiceState.ESCUCHANDO
            self._persist_state()

    def is_interrupted(self) -> bool:
        with self._lock:
            return self._context.interrupt_flag

    def is_in_follow_up_window(self) -> bool:
        """Verifica si la sesión conversacional continua está activa."""
        with self._lock:
            if not self._context.is_session_active:
                return False
            elapsed = time.time() - self._context.last_activity_time
            return elapsed < self._context.session_timeout_seconds

    def activate_session(self) -> None:
        with self._lock:
            self._context.is_session_active = True
            self._context.last_activity_time = time.time()
            self._context.current_state = VoiceState.ESPERANDO_SIGUIENTE_INTERVENCION
            self._persist_state()

    def pause_session(self) -> None:
        with self._lock:
            self._context.current_state = VoiceState.PAUSADO
            self._context.is_session_active = False
            self._persist_state()

    def resume_session(self) -> None:
        with self._lock:
            self._context.current_state = VoiceState.ESPERANDO_SIGUIENTE_INTERVENCION
            self._context.is_session_active = True
            self._context.last_activity_time = time.time()
            self._persist_state()

    def end_session(self) -> None:
        with self._lock:
            self._context.is_session_active = False
            self._context.current_state = VoiceState.ESPERANDO_ACTIVACION
            self._persist_state()

    def set_speech_rate(self, rate: float) -> None:
        with self._lock:
            self._context.speech_rate = max(0.5, min(2.0, rate))
            self._persist_state()

    def get_speech_rate(self) -> float:
        with self._lock:
            return self._context.speech_rate

    def record_turn(self, user_text: str, assistant_text: str) -> None:
        with self._lock:
            self._context.last_user_utterance = user_text
            self._context.last_assistant_response = assistant_text
            self._context.last_activity_time = time.time()
            self._context.history.append({"role": "user", "content": user_text})
            self._context.history.append({"role": "assistant", "content": assistant_text})
            self._context.history = self._context.history[-20:]
            self._persist_state()

    def get_last_response(self) -> str:
        with self._lock:
            return self._context.last_assistant_response

    def update_active_player(self, player_info: Optional[Dict[str, Any]]) -> None:
        with self._lock:
            self._context.active_player = player_info
            self._persist_state()

    def get_active_player(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._context.active_player

    def update_active_document(self, doc_info: Optional[Dict[str, Any]]) -> None:
        with self._lock:
            self._context.active_document = doc_info
            self._persist_state()

    def get_active_document(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._context.active_document

    def check_voice_control_command(self, clean_text: str) -> Optional[Dict[str, Any]]:
        """Interpreta comandos conversacionales específicos (dejar de hablar, más despacio, etc)."""
        import re

        # Interrumpir habla actual
        if re.search(r'\b(?:deja|deje|para|para\s+de|basta\s+de|deten|detente|calla|callate)\s+(?:de\s+)?hablar\b', clean_text):
            self.interrupt()
            return {"action": "voice_control", "subaction": "stop_speech", "message": "He detenido mi respuesta."}

        # Hablar más despacio
        if re.search(r'\b(?:habla|hablar|podes\s+hablar|puedes\s+hablar)\s+(?:mas\s+)?(?:despacio|lento|pausado)\b', clean_text):
            self.set_speech_rate(0.8)
            return {"action": "voice_control", "subaction": "slower", "message": "Entendido. A partir de ahora hablaré más pausadamente."}

        # Velocidad normal
        if re.search(r'\b(?:habla|hablar)\s+(?:normal|a\s+velocidad\s+normal)\b', clean_text):
            self.set_speech_rate(1.0)
            return {"action": "voice_control", "subaction": "normal_speed", "message": "Restauré mi velocidad de habla normal."}

        # Repetir lo último
        if re.search(r'\b(?:que\s+dijiste|repeti|repetir|repite|podes\s+repetir|puedes\s+repetir)\s*(?:lo\s+ultimo|el\s+ultimo\s+mensaje)?\b', clean_text):
            last = self.get_last_response()
            if last:
                return {"action": "voice_control", "subaction": "repeat_last", "message": f"Repito lo último que te dije: {last}"}
            return {"action": "voice_control", "subaction": "repeat_last", "message": "Aún no tengo un mensaje anterior registrado."}

        # Pausar conversación
        if re.search(r'\b(?:pausa|pausar)\s+(?:la\s+)?conversacion\b', clean_text):
            self.pause_session()
            return {"action": "voice_control", "subaction": "pause_session", "message": "Conversación pausada. Decí 'volvé a escuchar' para reanudar."}

        # Reanudar conversación
        if re.search(r'\b(?:volve|volver|continua|continuar|reanuda|reanudar)\s+(?:a\s+escuchar|la\s+conversacion)\b', clean_text):
            self.resume_session()
            return {"action": "voice_control", "subaction": "resume_session", "message": "Te escucho de nuevo. Continuemos."}

        # Finalizar conversación / cerrar micrófono
        if re.search(r'\b(?:cerra|cerrar|apaga|apagar)\s+(?:el\s+)?microfono\b|\b(?:terminamos|es\s+todo|hasta\s+luego)\s+por\s+ahora\b', clean_text):
            self.end_session()
            return {"action": "voice_control", "subaction": "end_session", "message": "Sesión finalizada. Decí SKY cuando desees volver a hablar."}

        # Activación explícita de diálogo
        if re.search(r'\b(?:escuchame|activa\s+la\s+conversacion|ya\s+no\s+quiero\s+repetir\s+sky)\b', clean_text):
            self.activate_session()
            return {"action": "voice_control", "subaction": "activate_natural", "message": "Te escucho. Ya no es necesario que repitas SKY, conversemos de forma continua."}

        return None

    def _persist_state(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(self._context.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


# Instancia compartida global
coordinador_voz = VoiceCoordinator()
