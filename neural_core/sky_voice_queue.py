"""Cola independiente del micrófono para consultas y reproducción de voz de SKY.

El hilo principal de Vosk sigue capturando audio aunque un proveedor de IA se
demore. Únicamente el trabajador serial accede a pyttsx3 y a las acciones del
agente; la cola tiene capacidad limitada, sin órdenes paralelas no autorizadas.
"""
from __future__ import annotations

import queue
import re
import sys
import threading
import time
import unicodedata
from typing import Callable


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", str(text or "").casefold())
    plain = "".join(c for c in folded if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", plain).split())


_WAKE = r"(?:oye |hey )?(?:sky|esquai|es kay|es cai|escai)"
_INTERRUPT = frozenset({
    "callate", "silencio", "para de hablar", "deja de hablar", "deja de responder",
    "detente", "para", "basta",
})


def wake_during_speech(text: str) -> bool:
    """Durante el TTS, reconocer una petición a SKY sólo para callar, nunca ejecutar."""
    clean = _normalize(text)
    return bool(re.fullmatch(_WAKE + r"(?: .+)", clean))


def interrupt_during_speech(text: str) -> bool:
    clean = _normalize(text)
    match = re.fullmatch(_WAKE + r" (.+)", clean)
    return bool(match and match.group(1) in _INTERRUPT)


_EMERGENCIA = frozenset({
    "para todo", "parada de emergencia", "cancela todo", "alto total",
    "frena todo", "modo emergencia",
})


def parada_emergencia_voz(text: str, *, exigir_activacion: bool = False) -> bool:
    """La parada debe procesarse por el hilo del micrófono, aun si Ollama está ocupado."""
    clean = _normalize(text)
    match = re.fullmatch(_WAKE + r" (.+)", clean)
    if match:
        return match.group(1) in _EMERGENCIA
    return not exigir_activacion and clean in _EMERGENCIA


def _interactivo() -> bool:
    try:
        return bool(sys.stdout is not None and sys.stdout.isatty())
    except (AttributeError, ValueError):
        return False


class VoiceWorkQueue:
    """Una tarea activa + hasta dos pendientes; sin acceso al micrófono."""

    def __init__(self, handle_command: Callable[[str], None], *,
                 tts_factory=None, rate_factory=None, speech_state=None, capacity: int = 2):
        self._handle = handle_command
        self._tts_factory = tts_factory
        self._rate_factory = rate_factory or (lambda: 180)
        self._speech_state = speech_state
        self._queue: queue.Queue[tuple[str, str, int]] = queue.Queue(maxsize=capacity)
        self._generation = 0
        self._active_generation = -1
        self._generation_lock = threading.Lock()
        self._stop = threading.Event()
        self._cancel_speech = threading.Event()
        self._cancel_current = threading.Event()
        self._speaking = threading.Event()
        self._busy = threading.Event()
        self._thread: threading.Thread | None = None
        self._engine = None
        self._speech_epoch = 0
        self._speech_interrupt_epoch = 0
        self._epoch_lock = threading.Lock()
        # v12.6: Vosk a veces entrega dos veces la misma frase (o el dueño la repite al no oír respuesta):
        # una orden idéntica dentro de esta ventana no se vuelve a ejecutar.
        self.dedupe_window = 3.0
        self._last_command = ("", 0.0)
        self.duplicates = 0

    @property
    def speaking(self) -> bool:
        return self._speaking.is_set()

    @property
    def busy(self) -> bool:
        return self._busy.is_set()

    @property
    def speech_epoch(self) -> int:
        with self._epoch_lock:
            return self._speech_epoch

    @property
    def speech_interrupt_epoch(self) -> int:
        """Marcador monotónico de interrupciones explícitas del TTS."""
        with self._epoch_lock:
            return self._speech_interrupt_epoch

    @property
    def current_turn_cancelled(self) -> bool:
        with self._generation_lock:
            outdated = self._active_generation != self._generation
        return outdated or self._cancel_current.is_set() or self._stop.is_set()

    def _transition_speech(self, value: bool) -> None:
        if self._speaking.is_set() == value:
            return
        if value:
            self._speaking.set()
        else:
            self._speaking.clear()
        with self._epoch_lock:
            self._speech_epoch += 1
        if self._speech_state:
            try:
                self._speech_state(value)
            except Exception as exc:
                print('SKY: no se pudo actualizar estado TTS:', type(exc).__name__)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, name="sky-voice-worker", daemon=True)
        self._thread.start()

    def submit(self, command: str) -> bool:
        if not isinstance(command, str) or not command.strip() or self._stop.is_set():
            return False
        clave, ahora = _normalize(command), time.monotonic()
        with self._generation_lock:
            ultima, cuando = self._last_command
            if clave == ultima and ahora - cuando < self.dedupe_window:
                self.duplicates += 1
                return True   # ya está en curso: no duplicar la acción
            try:
                self._queue.put_nowait(("command", command, self._generation))
                self._last_command = (clave, ahora)
                return True
            except queue.Full:
                return False

    def announce(self, message: str) -> bool:
        if not message or self._stop.is_set():
            return False
        with self._generation_lock:
            try:
                self._queue.put_nowait(("speech", message, self._generation))
                return True
            except queue.Full:
                return False

    def cancel_pending(self) -> int:
        """Parada de emergencia: suprimir salida pendiente y vaciar órdenes futuras."""
        with self._generation_lock:
            self._generation += 1  # invalida incluso el turno actualmente ejecutado
            self._cancel_current.set()
            self._cancel_speech.set()
            discarded = 0
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
                else:
                    discarded += 1
                    self._queue.task_done()
            return discarded

    def interrupt_speech(self) -> bool:
        """Solicita detener TTS. Nunca intenta llamar COM/pyttsx3 desde el hilo del micrófono."""
        if not self.speaking:
            return False
        with self._epoch_lock:
            self._speech_interrupt_epoch += 1
        self._cancel_speech.set()
        return True

    def _init_tts(self):
        if self._tts_factory is None:
            try:
                import pyttsx3
                factory = pyttsx3.init
            except ImportError:
                return None
        else:
            factory = self._tts_factory
        try:
            engine = factory()
            # pyttsx3 dispara callbacks desde su propio loop del hilo trabajador.
            # Es seguro solicitar stop() desde ese callback, nunca desde Vosk.
            def on_word(name, location, length):
                if self._cancel_speech.is_set():
                    engine.stop()
            engine.connect("started-word", on_word)
            return engine
        except Exception as exc:
            print("SKY: TTS local no disponible:", type(exc).__name__)
            return None

    def say(self, message: str) -> None:
        """Solo debe invocarse desde el trabajador; texto no se encola como orden."""
        message = str(message or "")
        with self._generation_lock:
            vigente = self._active_generation == self._generation
        if not message or self._stop.is_set() or self._cancel_current.is_set() or not vigente:
            return
        # v12.6: con salida a registros (inicio con Windows) no se guardan las respuestas completas.
        print("SKY-IA:", message if _interactivo() else f"(respuesta de {len(message)} caracteres)")
        if self._engine is None:
            return
        self._cancel_speech.clear()
        self._transition_speech(True)
        try:
            try:
                self._engine.setProperty("rate", int(self._rate_factory()))
            except (TypeError, ValueError, RuntimeError):
                pass
            # Frases breves permiten interrupción aun si un backend no entrega
            # eventos por palabra. La voz nunca se ejecuta en el hilo de Vosk.
            words = message[:1000].split()
            chunk = []
            for word in words:
                if self._cancel_speech.is_set() or self._stop.is_set():
                    break
                chunk.append(word)
                if len(" ".join(chunk)) >= 100 or word.endswith((".", "!", "?", ":", ";")):
                    self._engine.say(" ".join(chunk))
                    self._engine.runAndWait()
                    chunk.clear()
            if chunk and not self._cancel_speech.is_set() and not self._stop.is_set():
                self._engine.say(" ".join(chunk))
                self._engine.runAndWait()
        except Exception as exc:
            print("SKY: error de reproducción local:", type(exc).__name__)
        finally:
            self._transition_speech(False)
            self._cancel_speech.clear()

    def _worker(self) -> None:
        self._engine = self._init_tts()
        while not self._stop.is_set():
            try:
                kind, value, generation = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            with self._generation_lock:
                vigente = generation == self._generation
                if vigente:
                    self._active_generation = generation
                    self._cancel_current.clear()
            if not vigente:
                self._queue.task_done()
                continue
            self._busy.set()
            try:
                if kind == "command":
                    self._handle(value)
                elif kind == "speech":
                    self.say(value)
            except Exception as exc:
                print("SKY: error procesando turno de voz:", type(exc).__name__, str(exc)[:200])
            finally:
                self._busy.clear()
                self._queue.task_done()

    def stop(self) -> None:
        self._stop.set()
        self._cancel_current.set()
        self._cancel_speech.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
