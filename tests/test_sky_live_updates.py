"""SKY must fetch a dated source before answering a current public question."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import os
import unittest
from unittest.mock import patch

from neural_core import sky_live_updates as live


QUESTION = "Se serio estamos en 2026 como van las votaciones del balon de oro hoy"


class LiveNewsRoutingTests(unittest.TestCase):
    def test_ballondor_is_time_sensitive_without_explicit_search_verb(self):
        self.assertTrue(live.is_current_public_question(QUESTION))
        self.assertTrue(live.is_current_public_question("¿Cómo van los resultados de hoy?"))
        self.assertFalse(live.is_current_public_question("Abrí Word."))
        self.assertFalse(live.is_current_public_question("¿Qué es el Balón de Oro?"))
        self.assertFalse(live.is_current_public_question("¿Cómo van hoy mis correos de mi cuenta?"))

    def test_fetches_public_headlines_and_does_not_invent_vote_counts(self):
        now = datetime.now(timezone.utc)
        rows = [{
            "titular": "Ceremonia del Balón de Oro 2026 en Londres",
            "fuente": "UEFA",
            "fecha": format_datetime(now - timedelta(hours=1)),
            "enlace": "https://news.google.com/rss/articles/test",
        }]
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "0", "SKY_INTERNET": "1"}):
            with patch("neural_core.actualidad.noticias", return_value=rows) as fetch:
                result = live.maybe_answer(QUESTION)
        fetch.assert_called_once()
        self.assertEqual(result["proveedor"], "sky-actualidad-rss")
        self.assertTrue(result["consulta_externa"])
        self.assertIn("UEFA", result["mensaje"])
        self.assertIn("no voy a inventar", result["mensaje"])
        self.assertNotIn("votos en tiempo real: 70", result["mensaje"])
        self.assertTrue(result["fuentes"])

    def test_local_mode_forbids_network_and_discloses_limit(self):
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "1"}):
            with patch("neural_core.actualidad.noticias") as fetch:
                answer = live.maybe_answer(QUESTION)
        fetch.assert_not_called()
        self.assertFalse(answer["consulta_externa"])
        self.assertIn("No consulté", answer["mensaje"])

    def test_internet_disabled_forbids_network(self):
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "0", "SKY_INTERNET": "0"}):
            with patch("neural_core.actualidad.noticias") as fetch:
                answer = live.maybe_answer(QUESTION)
        fetch.assert_not_called()
        self.assertIn("SKY_INTERNET=0", answer["mensaje"])

    def test_no_network_does_not_fall_back_to_stale_model(self):
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "0", "SKY_INTERNET": "1"}):
            with patch("neural_core.actualidad.noticias", side_effect=OSError("offline")):
                answer = live.maybe_answer(QUESTION)
        self.assertIn("no respondió", answer["mensaje"])
        self.assertFalse(answer["consulta_externa"])

    def test_old_news_filtered(self):
        old = datetime.now(timezone.utc) - timedelta(days=35)
        item = {"titular": "Información antigua", "fuente": "Archivo",
                "fecha": format_datetime(old),
                "enlace": "https://news.google.com/rss/articles/old"}
        with patch.dict(os.environ, {"SKY_LOCAL_ONLY": "0", "SKY_INTERNET": "1"}):
            with patch("neural_core.actualidad.noticias", return_value=[item]):
                answer = live.maybe_answer(QUESTION)
        self.assertNotIn("Información antigua", answer["mensaje"])
        self.assertEqual(answer["fuentes"], [])

    def test_chat_router_handles_live_before_cerebro(self):
        from neural_core import sky_asistente_personal as assistant
        expected = {"tipo": "respuesta", "mensaje": "Fuente actual encontrada",
                    "proveedor": "sky-actualidad-rss"}
        with patch("neural_core.sky_live_updates.maybe_answer", return_value=expected):
            answer = assistant.reglas(QUESTION)
        self.assertEqual(answer, expected)

    def test_voice_assistant_routes_live_without_llm(self):
        from neural_core import assistant
        with patch("neural_core.sky_live_updates.maybe_answer", return_value={
            "tipo": "respuesta", "mensaje": "Dato reciente verificado"}):
            reply, docs = assistant.responder(QUESTION, "Asistente SKY personal")
        self.assertEqual(reply, "Dato reciente verificado")
        self.assertEqual(docs, [])


if __name__ == "__main__":
    unittest.main()
