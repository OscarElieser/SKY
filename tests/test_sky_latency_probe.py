"""Pruebas offline: la medicion no consulta nubes ni expone prompts."""
import io
import json
import unittest
from unittest.mock import patch

from neural_core import sky_latency_probe


class TestSkyLatencyProbe(unittest.TestCase):
    def test_modelos_disponibles(self):
        nombres = {"llama3.2:latest", "qwen2.5:3b"}
        self.assertTrue(sky_latency_probe.instalado("llama3.2", nombres))
        self.assertTrue(sky_latency_probe.instalado("qwen2.5:3b", nombres))
        self.assertFalse(sky_latency_probe.instalado("qwen3.5:4b", nombres))
        self.assertFalse(sky_latency_probe.instalado("qwen2.5:7b", nombres))

    def test_conversion_de_duraciones(self):
        self.assertEqual(sky_latency_probe._segundos(2500000000), 2.5)
        self.assertEqual(sky_latency_probe._segundos(None), 0.0)

    def test_consulta_local_sin_credenciales_ni_telemetria_externa(self):
        respuesta = {
            "message": {"role": "assistant", "content": "La fotosintesis transforma luz en energia."},
            "load_duration": 1000000000,
            "prompt_eval_duration": 500000000,
            "eval_duration": 2000000000,
            "prompt_eval_count": 16,
            "eval_count": 20,
        }
        with patch("neural_core.sky_latency_probe.urllib.request.urlopen",
                   return_value=io.BytesIO(json.dumps(respuesta).encode())) as llamada:
            datos = sky_latency_probe.prueba_ollama(
                "http://127.0.0.1:11434", "llama3.2", "Pregunta publica")
        request = llamada.call_args.args[0]
        enviados = json.loads(request.data)
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(enviados["model"], "llama3.2")
        self.assertEqual(enviados["stream"], False)
        self.assertEqual(enviados["options"]["num_predict"], 128)
        self.assertEqual(datos["tokens_segundo"], 10.0)
        self.assertEqual(datos["prompt_s"], 0.5)
        self.assertNotIn("Respuesta", str(datos))

    def test_cerebro_extrae_tiempos_locales_del_stream(self):
        from neural_core import sky_cerebro
        linea1 = {
            "message": {"content": "Managua."},
            "done": False,
        }
        linea2 = {
            "message": {"content": ""},
            "done": True,
            "eval_count": 20,
            "prompt_eval_count": 38,
            "load_duration": 10000000,
            "prompt_eval_duration": 800000000,
            "eval_duration": 2000000000,
        }
        contenido = ("\n".join(json.dumps(x) for x in (linea1, linea2)) + "\n").encode("utf-8")
        info = {"tokens": None}
        with patch.object(sky_cerebro, "_mensajes",
                          return_value=[{"role": "user", "content": "Pregunta publica"} ]), \
             patch.object(sky_cerebro, "_llamar", return_value=io.BytesIO(contenido)):
            eventos = list(sky_cerebro._eventos("Pregunta publica", [], "chat", info))
        self.assertEqual(eventos, [("delta", "Managua."), ("fin", "Managua.")])
        self.assertEqual(info["tokens"], 58)
        self.assertEqual(info["prompt_tokens"], 38)
        self.assertEqual(info["generated_tokens"], 20)
        self.assertEqual(info["load_s"], 0.01)
        self.assertEqual(info["prompt_s"], 0.8)
        self.assertEqual(info["generation_s"], 2.0)

    def test_timing_asistente_preserva_etapas_y_resultado(self):
        from neural_core import sky_asistente_personal, sky_unified_agents, sky_cerebro
        def fake_atender(*args, **kwargs):
            sky_asistente_personal.preparar("texto")
            sky_asistente_personal.reglas("texto")
            sky_unified_agents.maybe_answer("texto")
            sky_cerebro.decidir("texto")
            return {"tipo": "respuesta", "proveedor": "ollama", "mensaje": "Bien."}
        with patch.object(sky_asistente_personal, "atender", side_effect=fake_atender), \
             patch.object(sky_asistente_personal, "preparar", return_value="texto"), \
             patch.object(sky_asistente_personal, "reglas", return_value=None), \
             patch.object(sky_unified_agents, "maybe_answer", return_value=None), \
             patch.object(sky_cerebro, "decidir", return_value={"tipo": "texto", "mensaje": "Bien."}):
            resultado = sky_latency_probe.prueba_asistente("llama3.2")
        self.assertEqual(resultado["proveedor"], "ollama")
        self.assertTrue(resultado["texto"])
        self.assertTrue(set(["preparacion_s", "reglas_s", "agentes_s", "cerebro_s"])
                        <= set(resultado["etapas"]))


if __name__ == "__main__":
    unittest.main()
