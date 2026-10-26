"""Pruebas de selección dinámica: no se pierden herramientas ni políticas."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from neural_core.sky_tool_selector import select_tool_names, select_tools
from neural_core import sky_cerebro as cerebro


class ToolSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool_catalog = cerebro.herramientas()
        cls.names = [t["function"]["name"] for t in cls.tool_catalog]

    def test_catalogue_remains_available(self):
        self.assertGreaterEqual(len(self.names), 22)
        self.assertEqual(len(set(self.names)), len(self.names))
        self.assertIn("reproducir", self.names)
        self.assertIn("bloquear_equipo", self.names)

    def test_chat_is_tool_free(self):
        for message in (
            "Hola SKY, explicame qué podés hacer.",
            "¿Qué es YouTube y para qué sirve?",
            "Explicame las diferencias entre Word y Excel.",
            "Gracias por tu ayuda",
        ):
            with self.subTest(message=message):
                self.assertEqual(select_tool_names(message, self.names), [])

    def test_targeted_intents(self):
        cases = [
            ("SKY, abrí Word", "abrir_app"),
            ("Poneme algo tranquilo", "reproducir"),
            ("Subí el volumen", "volumen"),
            ("Me está dejando sordo", "volumen"),
            ("Necesito escribir un informe", "abrir_app"),
            ("Buscá recetas en Google", "buscar_web"),
            ("Abrí mi carpeta de Documentos", "abrir_carpeta_o_documento"),
            ("Creá una nota para mañana", "nota"),
            ("Prepará una presentación sobre Nicaragua", "tarea"),
            ("SKY, recordá que me gusta investigar", "recordar_dato"),
            ("Bloqueá la computadora", "bloquear_equipo"),
            ("Minimizá la ventana de Word", "ventanas"),
        ]
        for message, expected in cases:
            with self.subTest(message=message):
                names = select_tool_names(message, self.names)
                self.assertIn(expected, names)
                self.assertLess(len(names), len(self.names))

    def test_ambiguous_command_keeps_all(self):
        for message in ("SKY, hacelo", "Ejecutá la acción que acordamos"):
            with self.subTest(message=message):
                self.assertEqual(select_tool_names(message, self.names), self.names)

    def test_no_unknown_names_or_new_capabilities(self):
        selected = select_tools("Abrí Word", self.tool_catalog)
        self.assertTrue(selected)
        self.assertEqual([t["function"]["name"] for t in selected], ["abrir_app"])
        self.assertEqual(self.names, [t["function"]["name"] for t in self.tool_catalog])

    def test_local_payload_has_no_tools_in_chat(self):
        with patch.object(cerebro, "herramientas", return_value=self.tool_catalog):
            with patch.object(cerebro.urllib.request, "urlopen") as mock_url:
                cerebro._llamar(
                    [{"role": "system", "content": "Sos SKY"},
                     {"role": "user", "content": "Hola, ¿qué podés hacer?"}],
                    stream=False
                )
                payload = json.loads(mock_url.call_args.args[0].data)
                self.assertNotIn("tools", payload)
                self.assertEqual(payload["stream"], False)

    def test_local_payload_only_music_tools(self):
        with patch.object(cerebro, "herramientas", return_value=self.tool_catalog):
            with patch.object(cerebro.urllib.request, "urlopen") as mock_url:
                cerebro._llamar([{"role":"user", "content":"Poneme algo tranquilo"}], stream=True)
                payload = json.loads(mock_url.call_args.args[0].data)
                names = [t["function"]["name"] for t in payload["tools"]]
                self.assertIn("reproducir", names)
                self.assertNotIn("nota", names)
                self.assertTrue(payload["stream"])

    def test_cloud_payload_omits_empty_schema_collections(self):
        cases = [
            ("openai", {"choices":[{"message":{"content":"Hola"}}]}),
            ("anthropic", {"content":[{"type":"text","text":"Hola"}]}),
            ("gemini", {"candidates":[{"content":{"parts":[{"text":"Hola"}]}}]}),
        ]
        for provider, response in cases:
            with self.subTest(provider=provider):
                with patch.object(cerebro, "herramientas", return_value=self.tool_catalog):
                    with patch.object(cerebro, "_clave", return_value="testing"):
                        with patch.object(cerebro, "_modelo_nube", return_value="testing-model"):
                            with patch.object(cerebro, "_post", return_value=response) as mock_post:
                                name, args, text, _ = cerebro._llamada_nube(
                                    provider,
                                    [{"role":"system","content":"Sos SKY"},
                                     {"role":"user","content":"Hola, ¿qué podés hacer?"}]
                                )
                                payload = mock_post.call_args.args[1]
                                self.assertNotIn("tools", payload)
                                self.assertNotIn("tool_choice", payload)
                                self.assertIsNone(name)
                                self.assertEqual(text, "Hola")


if __name__ == "__main__":
    unittest.main()
