"""Validación sin red: el contexto abreviado jamás elimina datos relevantes."""
from __future__ import annotations

import io
import os
import unittest
from unittest.mock import patch

from neural_core import sky_cerebro


PREGUNTA = "Explica en dos oraciones que es la fotosintesis."


class TestSkyLocalFastContext(unittest.TestCase):
    def test_default_disabled_even_for_public_question(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "0"}, clear=False), \
             patch.object(sky_cerebro, "contexto_aprendido", return_value="MEMORIA_PRIVADA_FICTICIA"), \
             patch("neural_core.sky_impacto.impact_instructions", return_value="IMPACTO"), \
             patch("neural_core.sky_pro_skills.skill_instructions", return_value="SKILLS"):
            mensajes = sky_cerebro._mensajes(PREGUNTA, [], "chat", local=True)
        self.assertIn("MEMORIA_PRIVADA_FICTICIA", mensajes[0]["content"])
        self.assertIn("IMPACTO", mensajes[0]["content"])
        self.assertIn("SKILLS", mensajes[0]["content"])

    def test_public_isolated_question_omits_personal_context_only_when_opted_in(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False), \
             patch.object(sky_cerebro, "contexto_aprendido",
                          side_effect=AssertionError("No debe cargar datos personales")), \
             patch("neural_core.sky_impacto.impact_instructions",
                   side_effect=AssertionError("No debe cargar instrucciones extensas")), \
             patch("neural_core.sky_pro_skills.skill_instructions",
                   side_effect=AssertionError("No debe cargar habilidades extensas")):
            mensajes = sky_cerebro._mensajes(PREGUNTA, [], "chat", local=True)
        self.assertEqual(len(mensajes), 2)
        self.assertLess(len(mensajes[0]["content"]), 450)
        self.assertIn("SKY", mensajes[0]["content"])
        self.assertEqual(mensajes[1]["content"], PREGUNTA)

    def test_private_context_and_action_requests_never_use_fast_path(self):
        bloqueadas = (
            "Explica que es mi PIN de acceso",
            "Define mi proyecto de SKY",
            "Explica lo que dijiste antes sobre la fotosintesis",
            "Explica que es un correo y abre Word",
            "Que es mi documento de trabajo",
            "Explica como funciona mi cuenta",
            "Explica el tema y guarda un archivo",
            "Investiga la fotosintesis para mi trabajo",
            "Abre Excel y explica el error",
            "Como puedo enviar un correo",
            "Explica mi chat anterior",
        )
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False):
            self.assertTrue(sky_cerebro.contexto_local_breve(PREGUNTA))
            for texto in bloqueadas:
                with self.subTest(texto=texto):
                    self.assertFalse(sky_cerebro.contexto_local_breve(texto))
            self.assertFalse(sky_cerebro.contexto_local_breve(PREGUNTA, [
                {"role": "user", "content": "Referente anterior"}
            ]))

    def test_full_memory_preserved_with_conversation_history(self):
        historial = [{"role": "user", "content": "Mi trabajo es docencia."}]
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False), \
             patch.object(sky_cerebro, "contexto_aprendido", return_value="MEMORIA_FICTICIA"), \
             patch("neural_core.sky_impacto.impact_instructions", return_value=""), \
             patch("neural_core.sky_pro_skills.skill_instructions", return_value=""):
            mensajes = sky_cerebro._mensajes(PREGUNTA, historial, "chat", local=True)
        self.assertIn("MEMORIA_FICTICIA", mensajes[0]["content"])
        self.assertEqual(mensajes[1]["content"], "Mi trabajo es docencia.")

    def test_cloud_never_receives_compact_context(self):
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False), \
             patch.object(sky_cerebro, "contexto_aprendido", return_value="MEMORIA_FICTICIA"), \
             patch("neural_core.sky_impacto.impact_instructions", return_value=""), \
             patch("neural_core.sky_pro_skills.skill_instructions", return_value=""):
            mensajes = sky_cerebro._mensajes(PREGUNTA, [], "chat")
        self.assertIn("MEMORIA_FICTICIA", mensajes[0]["content"])

    def test_real_local_stream_uses_compact_messages_without_changing_actions(self):
        dato = b'{"message":{"content":"Las plantas usan la luz."},"done":true,"eval_count":6,"prompt_eval_count":23}\n'
        info = {"tokens": None}
        capturados = []
        def falsa_llamada(msgs, stream):
            capturados.extend(msgs)
            return io.BytesIO(dato)
        with patch.dict(os.environ, {"SKY_LOCAL_FAST_CONTEXT": "1"}, clear=False), \
             patch.object(sky_cerebro, "contexto_aprendido",
                          side_effect=AssertionError("No leer memoria")), \
             patch.object(sky_cerebro, "_llamar", side_effect=falsa_llamada):
            eventos = list(sky_cerebro._eventos(PREGUNTA, [], "chat", info))
        self.assertEqual(eventos[-1], ("fin", "Las plantas usan la luz."))
        self.assertEqual(info["tokens"], 29)
        self.assertEqual(len(capturados), 2)
        self.assertLess(len(capturados[0]["content"]), 450)


if __name__ == "__main__":
    unittest.main()
