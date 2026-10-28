"""Pruebas de subasta sin credenciales ni peticiones reales."""
import os
import unittest
from unittest.mock import patch

from neural_core import sky_ai_auction, sky_cerebro


class TestSkyAuction(unittest.TestCase):
    def tearDown(self):
        sky_cerebro.preferir(None)
        with sky_ai_auction._FALLOS_LOCK:
            sky_ai_auction._FALLOS.clear()

    def test_auto_historico_sigue_siend_local(self):
        with patch.dict(os.environ, {"SKY_CEREBRO": "auto", "SKY_LOCAL_ONLY": "0",
                                     "GROQ_API_KEY": "simulada"}, clear=False):
            sky_cerebro.preferir(None)
            self.assertEqual(sky_cerebro.motor("investiga"), "ollama")

    def test_subasta_por_tarea_y_claves_configuradas(self):
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "0"}, clear=False), \
             patch("neural_core.providers.provider_ready", side_effect=lambda p: p in ("gemini", "openai")), \
             patch("neural_core.sky_ai_auction._ollama_disponible", return_value=False), \
             patch("neural_core.sky_ai_auction._telemetria", return_value={}):
            ofertas = sky_ai_auction.ofertas("investiga artículos académicos")
            self.assertEqual([o["proveedor"] for o in ofertas], ["gemini", "openai"])
            self.assertEqual(ofertas[0]["motivo"], "preferencia inicial; rendimiento no verificado")

    def test_local_only_invalida_todas_las_nubes(self):
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "1"}, clear=False), \
             patch("neural_core.sky_ai_auction._ollama_disponible", return_value=True), \
             patch("neural_core.sky_ai_auction._telemetria", return_value={}):
            self.assertEqual([o["proveedor"] for o in sky_ai_auction.ofertas("redacta un documento")], ["ollama"])

    def test_secretos_no_van_a_la_nube_y_sin_local_no_hay_oferta(self):
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "0"}, clear=False), \
             patch("neural_core.sky_ai_auction._ollama_disponible", return_value=False), \
             patch("neural_core.sky_ai_auction._telemetria", return_value={}):
            self.assertEqual(sky_ai_auction.ofertas("Mi PIN es 1234"), [])

    def test_penaliza_fallos_reales(self):
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "0"}, clear=False), \
             patch("neural_core.providers.provider_ready", side_effect=lambda p: p in ("gemini", "openai")), \
             patch("neural_core.sky_ai_auction._ollama_disponible", return_value=False), \
             patch("neural_core.sky_ai_auction._telemetria",
                   return_value={"gemini": [(False, 1400)] * 10, "openai": [(True, 900)] * 10}):
            self.assertEqual(sky_ai_auction.seleccionar("investiga el clima"), "openai")

    def test_limita_intentos(self):
        with patch.dict(os.environ, {"SKY_AUCTION_MAX_ATTEMPTS": "99"}, clear=False):
            self.assertEqual(sky_ai_auction.max_intentos(), 7)
        with patch.dict(os.environ, {"SKY_AUCTION_MAX_ATTEMPTS": "6"}, clear=False):
            self.assertEqual(sky_ai_auction.max_intentos(), 6)
        with patch.dict(os.environ, {"SKY_AUCTION_MAX_ATTEMPTS": "cualquier cosa"}, clear=False):
            self.assertEqual(sky_ai_auction.max_intentos(), 2)

    def test_preferencia_manual_no_activa_subasta(self):
        with patch.dict(os.environ, {"SKY_CEREBRO": "subasta", "SKY_LOCAL_ONLY": "0",
                                     "GROQ_API_KEY": "simulada"}, clear=False):
            sky_cerebro.preferir("groq")
            self.assertEqual(sky_cerebro.motor("investiga"), "groq")
            sky_cerebro.preferir("ollama")
            self.assertEqual(sky_cerebro.motor("investiga"), "ollama")

    def test_fallback_secuencial_y_telemetria_real(self):
        candidatos = [{"proveedor": "groq"}, {"proveedor": "gemini"}]
        def falso(proveedor, texto, historial, modo, info):
            if proveedor == "groq":
                yield "error", "cuota agotada"
            else:
                yield "delta", "Respuesta"
                yield "fin", "Respuesta"

        with patch.dict(os.environ, {"SKY_CEREBRO": "subasta", "SKY_LOCAL_ONLY": "0"}, clear=False), \
             patch("neural_core.sky_ai_auction.ofertas", return_value=candidatos), \
             patch("neural_core.sky_cerebro._eventos_nube", side_effect=falso), \
             patch("neural_core.sky_metricas.registrar") as registrar:
            sky_cerebro.preferir("auto")
            eventos = list(sky_cerebro.decidir_eventos("explica un concepto"))
            self.assertEqual(eventos, [("delta", "Respuesta"), ("fin", "Respuesta")])
            self.assertEqual(sky_cerebro.ultimo_proveedor(), "gemini")
            self.assertEqual(registrar.call_count, 2)
            self.assertFalse(registrar.call_args_list[0].args[2])
            self.assertTrue(registrar.call_args_list[1].args[2])

    def test_no_mezcla_respuestas_parciales_de_varias_api(self):
        def falso(proveedor, texto, historial, modo, info):
            yield "delta", "mitad"
            yield "error", "corte"

        with patch.dict(os.environ, {"SKY_CEREBRO": "subasta", "SKY_LOCAL_ONLY": "0"}, clear=False), \
             patch("neural_core.sky_ai_auction.ofertas",
                   return_value=[{"proveedor": "groq"}, {"proveedor": "gemini"}]), \
             patch("neural_core.sky_cerebro._eventos_nube", side_effect=falso) as llamada, \
             patch("neural_core.sky_metricas.registrar"):
            sky_cerebro.preferir(None)
            eventos = list(sky_cerebro.decidir_eventos("explica"))
            self.assertEqual([e for e, _ in eventos], ["delta", "error"])
            self.assertEqual(llamada.call_count, 1)

    def test_circuit_breaker_excludes_failed_gemini_but_keeps_others(self):
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "0"}, clear=False), \
             patch("neural_core.providers.provider_ready", side_effect=lambda p: p in ("gemini", "openai", "anthropic")), \
             patch("neural_core.sky_ai_auction._ollama_disponible", return_value=False), \
             patch("neural_core.sky_ai_auction._telemetria", return_value={}):
            sky_ai_auction.registrar_fallo("gemini", "GEMINI HTTP 503 (UNAVAILABLE): servicio sobrecargado")
            self.assertIn("gemini", sky_ai_auction.en_espera())
            nombres = [x["proveedor"] for x in sky_ai_auction.ofertas("investiga un estudio")]
            self.assertEqual(nombres, ["openai", "anthropic"])
            sky_ai_auction.registrar_exito("gemini")
            self.assertEqual(sky_ai_auction.seleccionar("investiga un estudio"), "gemini")

    def test_cooldown_distingue_429_temporal_de_saldo_agotado(self):
        self.assertEqual(sky_ai_auction._segundos_espera("OPENAI HTTP 429: rate limit"), 90)
        self.assertEqual(sky_ai_auction._segundos_espera(
            "OPENAI HTTP 429 (credit_balance_exhausted): saldo"), 600)
        self.assertEqual(sky_ai_auction._segundos_espera("GEMINI HTTP 503"), 45)
        self.assertEqual(sky_ai_auction._segundos_espera("OPENAI HTTP 401"), 600)

    def test_cooldown_caduca_sin_persistir_claves_o_conversaciones(self):
        with patch("neural_core.sky_ai_auction.time.monotonic", side_effect=[100.0, 146.0]):
            sky_ai_auction.registrar_fallo("gemini", "GEMINI HTTP 503")
            self.assertEqual(sky_ai_auction.en_espera(), {})


if __name__ == "__main__":
    unittest.main()
