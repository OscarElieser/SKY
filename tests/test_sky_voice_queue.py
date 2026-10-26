"""Regresión: Vosk puede seguir capturando mientras Ollama/TTS trabaja.

Sin micrófono, solicitudes externas ni acciones de Windows.
"""
import threading
import time
from neural_core.sky_voice_queue import (
    VoiceWorkQueue, interrupt_during_speech, wake_during_speech,
    parada_emergencia_voz
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


def test_parada_emergencia_tiene_prioridad_sobre_trabajador():
    assert parada_emergencia_voz("SKY, para todo", exigir_activacion=True)
    assert parada_emergencia_voz("oye sky parada de emergencia", exigir_activacion=True)
    assert parada_emergencia_voz("para todo", exigir_activacion=False)
    assert not parada_emergencia_voz("para todo", exigir_activacion=True)
    assert not parada_emergencia_voz("sky abre word", exigir_activacion=True)


def test_emergencia_descarta_pendientes_y_no_lee_respuesta_vieja():
    running, release = threading.Event(), threading.Event()
    finished = []
    worker = None

    def handle(command):
        if command == "consulta larga":
            running.set()
            assert release.wait(2)
            worker.say("Mensaje obsoleto")
        finished.append(command)

    worker = VoiceWorkQueue(handle, tts_factory=lambda: None)
    worker.start()
    assert worker.submit("consulta larga")
    assert running.wait(2)
    assert worker.submit("abre word")
    assert worker.submit("reproduce musica")
    assert worker.cancel_pending() == 2
    release.set()
    worker._queue.join()
    # El cálculo que ya estaba en progreso puede terminar; las órdenes
    # pendientes no se ejecutan, y su respuesta no debe pronunciarse.
    assert finished == ["consulta larga"]
    worker.stop()


def test_cancelacion_durante_tts_por_callback_en_mismo_hilo():
    class InterruptibleTTS(FakeTTS):
        def __init__(self):
            super().__init__()
            self.playing = threading.Event()

        def runAndWait(self):
            self.playing.set()
            for _ in range(100):
                if self.callback:
                    self.callback("utterance", 0, 1)
                if self.stopped:
                    return
                time.sleep(0.01)
            raise AssertionError("TTS no recibió cancelación")

    engine = InterruptibleTTS()
    worker = VoiceWorkQueue(lambda _: None, tts_factory=lambda: engine)
    worker.start()
    assert worker.announce("Hola, estoy hablando con el usuario de SKY.")
    assert engine.playing.wait(2)
    assert worker.speaking
    assert worker.interrupt_speech()
    worker._queue.join()
    assert engine.stopped
    assert not worker.speaking
    worker.stop()
