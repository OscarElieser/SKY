"""Voz progresiva: pruebas sin micrófono, nube, escritorio ni pyttsx3."""
import os
import unittest
from unittest.mock import patch

from neural_core import sky_cerebro
from neural_core import sky_voice_stream_local as voz

PREGUNTA = "Explica en dos oraciones que es la fotosintesis."


class TestVozProgresivaLocal(unittest.TestCase):
    def test_opt_in_y_privacidad(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1",
                                     "SKY_VOICE_STREAM_LOCAL": "0", "SKY_VOICE_PROVIDER": "auto"}, clear=False):
            self.assertFalse(voz.eligible(PREGUNTA))
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1",
                                     "SKY_VOICE_STREAM_LOCAL": "1", "SKY_VOICE_PROVIDER": "auto"}, clear=False):
            self.assertTrue(voz.eligible(PREGUNTA))
            self.assertFalse(voz.eligible("Explica mi proyecto de SKY"))
            self.assertFalse(voz.eligible("Abre Word y crea un documento"))
            self.assertFalse(voz.eligible(PREGUNTA, [
                {"role": "user", "content": "Contexto anterior"}
            ]))

    def test_proveedor_cloud_explicito_no_se_sustituye_por_ollama(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1",
                                     "SKY_VOICE_STREAM_LOCAL": "1",
                                     "SKY_VOICE_PROVIDER": "anthropic"}, clear=False):
            self.assertFalse(voz.eligible(PREGUNTA))

    def test_emite_primera_frase_antes_de_fin(self):
        secuencia = []
        def eventos():
            yield ("delta", "La fotosintesis convierte luz en energia. ")
            secuencia.append("modelo-continuo")
            yield ("delta", "Tambien produce oxigeno.")
            yield ("fin", "La fotosintesis convierte luz en energia. Tambien produce oxigeno.")

        def hablar(texto):
            secuencia.append(("tts", texto))

        tiempos = iter([10.0, 10.2])
        resultado = voz.speak_stream(
            PREGUNTA, hablar, cancelled=lambda: False,
            events=eventos(), clock=lambda: next(tiempos, 10.2))
        self.assertTrue(resultado.ok)
        self.assertTrue(resultado.spoken)
        self.assertEqual(resultado.text, "La fotosintesis convierte luz en energia. Tambien produce oxigeno.")
        self.assertEqual(secuencia[0], ("tts", "La fotosintesis convierte luz en energia."))
        self.assertEqual(secuencia[1], "modelo-continuo")
        self.assertEqual(secuencia[2], ("tts", "Tambien produce oxigeno."))
        self.assertAlmostEqual(resultado.first_tts_s, 0.2)

    def test_error_despues_de_hablar_no_reintenta_ni_repite(self):
        frases = []
        eventos = iter([
            ("delta", "La respuesta parcial se ha iniciado. "),
            ("error", "Error de Ollama"),
            ("fin", "No debe llegar aqui"),
        ])
        resultado = voz.speak_stream(PREGUNTA, frases.append, cancelled=lambda: False, events=eventos)
        self.assertFalse(resultado.ok)
        self.assertTrue(resultado.spoken)
        self.assertEqual(resultado.error, "inference_error")
        self.assertEqual(frases, ["La respuesta parcial se ha iniciado."])

    def test_no_ejecuta_ninguna_herramienta(self):
        recibidas = []
        resultado = voz.speak_stream(
            PREGUNTA, recibidas.append, cancelled=lambda: False,
            events=iter([("herramienta", {"action": "launch_app", "params": {"app": "word"}})]))
        self.assertFalse(resultado.ok)
        self.assertEqual(resultado.error, "tool_not_permitted")
        self.assertEqual(recibidas, [])

    def test_cancelacion_no_pronuncia_mas_texto(self):
        estado = {"cancelled": False}
        frases = []
        def decir(t):
            frases.append(t)
            estado["cancelled"] = True
        resultado = voz.speak_stream(
            PREGUNTA, decir, cancelled=lambda: estado["cancelled"],
            events=iter([
                ("delta", "La primera frase termina aqui. "),
                ("delta", "Segunda frase sin permiso."),
                ("fin", "La primera frase termina aqui. Segunda frase sin permiso."),
            ]))
        self.assertFalse(resultado.ok)
        self.assertEqual(resultado.error, "cancelled")
        self.assertEqual(frases, ["La primera frase termina aqui."])

    def test_ollama_fijado_solo_este_turno(self):
        usado = []
        previo = sky_cerebro._PREFERIDO.get()
        def eventos_fake(text, historial=None, modo='voz'):
            usado.append(sky_cerebro._PREFERIDO.get())
            yield ("delta", "Respuesta local inmediata.")
            yield ("fin", "Respuesta local inmediata.")
        try:
            with patch.object(sky_cerebro, "decidir_eventos", side_effect=eventos_fake):
                resultado = voz.speak_stream(PREGUNTA, lambda _: None, cancelled=lambda: False)
            self.assertTrue(resultado.ok)
            self.assertEqual(usado, ["ollama"])
            self.assertEqual(sky_cerebro._PREFERIDO.get(), "")
        finally:
            sky_cerebro.preferir(previo)

    def test_no_habla_si_cancelado_antes_del_modelo(self):
        frases = []
        resultado = voz.speak_stream(
            PREGUNTA, frases.append, cancelled=lambda: True,
            events=iter([("delta", "La frase no debe hablarse.")]))
        self.assertFalse(resultado.ok)
        self.assertFalse(frases)


if __name__ == "__main__":
    unittest.main()
