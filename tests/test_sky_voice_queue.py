"""Regresión: Vosk puede seguir capturando mientras Ollama/TTS trabaja.

Sin micrófono, solicitudes externas ni acciones de Windows.
"""
import threading
from neural_core.sky_voice_queue import (
    VoiceWorkQueue, interrupt_during_speech, wake_during_speech
)


def test_interrupcion_exige_palabra_de_activacion():
    assert interrupt_during_speech("SKY, cállate")
    assert interrupt_during_speech("oye sky deja de hablar")
    assert wake_during_speech("SKY, abrí Word")
    assert not interrupt_during_speech("deja de hablar")
    assert not wake_during_speech("abrí Word")
    assert not interrupt_during_speech("SKY, borrá todos los archivos")


def test_cola_no_ejecuta_en_paralelo_y_limita_pendientes():
    started, release = threading.Event(), threading.Event()
    done = []
    def handle(cmd):
        if cmd == "uno":
            started.set()
            assert release.wait(2)
        done.append(cmd)

    executor = VoiceWorkQueue(handle, tts_factory=lambda: None)
    executor.start()
    assert executor.submit("uno")
    assert started.wait(2)
    assert executor.submit("dos")
    assert executor.submit("tres")
    assert not executor.submit("cuatro")
    release.set()
    executor._queue.join()
    assert done == ["uno", "dos", "tres"]
    executor.stop()


class FakeTTS:
    def __init__(self):
        self.callback = None
        self.stopped = False
        self.words = []
    def connect(self, event, callback):
        assert event == "started-word"
        self.callback = callback
    def setProperty(self, name, value):
        assert name == "rate"
    def say(self, phrase):
        self.words.append(phrase)
    def runAndWait(self):
        if self.callback:
            self.callback("utterance", 0, 1)
    def stop(self):
        self.stopped = True


def test_audio_solo_en_hilo_trabajador_y_cancelacion():
    tts = FakeTTS()
    driver = VoiceWorkQueue(lambda _: None, tts_factory=lambda: tts)
    driver.start()
    assert driver.announce("Hola, te escucho.")
    driver._queue.join()
    assert "Hola, te escucho." in tts.words
    assert not driver.speaking
    driver.stop()


def test_normalizacion_de_frases():
    assert interrupt_during_speech("¡Hey SKY! ¡Silencio!")
    assert not wake_during_speech("Ya le dije a SKY que abriera Word")
