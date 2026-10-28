"""SKY Windows: preferencia local de baja latencia SOLO para preguntas aisladas."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from neural_core import sky_cerebro

QUESTION = "Explica en dos oraciones que es la fotosintesis."


class TestWindowsFastLocalTurn(unittest.TestCase):
    def tearDown(self):
        sky_cerebro.preferir(None)

    def _run(self, question=QUESTION, history=None):
        order = []
        def local(text, turns, mode, info):
            order.append("ollama")
            yield "delta", "La fotosintesis transforma luz en energia."
            yield "fin", "La fotosintesis transforma luz en energia."
        def cloud(provider, text, turns, mode, info):
            order.append(provider)
            yield "delta", "Respuesta cloud."
            yield "fin", "Respuesta cloud."
        offers = [{"proveedor": "gemini"}, {"proveedor": "ollama"}]
        with patch("neural_core.sky_ai_auction.candidatos_con_respaldo", return_value=offers), \
             patch.object(sky_cerebro, "_eventos", side_effect=local), \
             patch.object(sky_cerebro, "_eventos_nube", side_effect=cloud), \
             patch("neural_core.sky_metricas.registrar"):
            events = list(sky_cerebro._decidir_subasta(question, history, "chat"))
        return order, events

    def test_opt_in_simple_public_goes_local_first(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False):
            order, events = self._run()
        self.assertEqual(order, ["ollama"])
        self.assertEqual(events[-1], ("fin", "La fotosintesis transforma luz en energia."))

    def test_disabled_keeps_cloud_ranking(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "0"}, clear=False):
            order, events = self._run()
        self.assertEqual(order, ["gemini"])
        self.assertEqual(events[-1], ("fin", "Respuesta cloud."))

    def test_prior_history_preserves_full_routing(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False):
            order, _ = self._run(history=[{"role": "user", "content": "Estoy preparando una clase."}])
        self.assertEqual(order, ["gemini"])

    def test_private_question_keeps_full_routing(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False):
            order, _ = self._run(question="Explica que es mi documento de trabajo")
        self.assertEqual(order, ["gemini"])

    def test_local_unavailable_preserves_other_offers(self):
        order = []
        def fake_cloud(provider, *args):
            order.append(provider)
            yield "fin", "Respuesta de nube."
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False), \
             patch("neural_core.sky_ai_auction.candidatos_con_respaldo",
                   return_value=[{"proveedor": "gemini"}]), \
             patch.object(sky_cerebro, "_eventos_nube", side_effect=fake_cloud), \
             patch("neural_core.sky_metricas.registrar"):
            events = list(sky_cerebro._decidir_subasta(QUESTION, None, "chat"))
        self.assertEqual(order, ["gemini"])
        self.assertEqual(events[-1], ("fin", "Respuesta de nube."))

    def test_failed_local_uses_same_cloud_fallback(self):
        order = []
        def fail_local(*args):
            order.append("ollama")
            yield "error", "Ollama sin respuesta"
        def cloud(provider, *args):
            order.append(provider)
            yield "fin", "Respuesta de nube."
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False), \
             patch("neural_core.sky_ai_auction.candidatos_con_respaldo",
                   return_value=[{"proveedor": "gemini"}, {"proveedor": "ollama"}]), \
             patch.object(sky_cerebro, "_eventos", side_effect=fail_local), \
             patch.object(sky_cerebro, "_eventos_nube", side_effect=cloud), \
             patch("neural_core.sky_metricas.registrar"):
            events = list(sky_cerebro._decidir_subasta(QUESTION, None, "chat"))
        self.assertEqual(order, ["ollama", "gemini"])
        self.assertEqual(events[-1], ("fin", "Respuesta de nube."))


if __name__ == "__main__":
    unittest.main()
