"""Safe Word COM editing: parser, target selection, readback and permissions."""
from __future__ import annotations

import unittest

from neural_core.sky_word_editor import (
    propuesta, solicitud, validar_parametros, escribir_documento_abierto,
)
from neural_core import sky_capacidades as caps


class FakeRange:
    def __init__(self, document, index):
        self.doc = document
        self.index = index

    def InsertAfter(self, text):
        current = self.doc.Content.Text
        self.doc.Content.Text = current[:self.index] + text + current[self.index:]


class FakeContent:
    def __init__(self, text="\r"):
        self.Text = text

    @property
    def End(self):
        return len(self.Text)


class FakeDocument:
    def __init__(self, text="\r", name="Documento1", readonly=False, protection=-1):
        self.Name = name
        self.ReadOnly = readonly
        self.ProtectionType = protection
        self.Content = FakeContent(text)

    def Range(self, start, end):
        if start != end:
            raise AssertionError("Append-only should not select/delete content")
        return FakeRange(self, start)


class FakeApp:
    def __init__(self, document=None, count=1, visible=True):
        self.Visible = visible
        self.Documents = type("Documents", (), {"Count": count})()
        self.ActiveDocument = document or FakeDocument()
        self.activated = False

    def Activate(self):
        self.activated = True


class ParserTests(unittest.TestCase):
    def test_explicit_word_writing_nicaraguan_accent(self):
        for query in [
            "SKY, escribí en Word: Hola Nicaragua",
            "Escribe en Microsoft Word el texto: Hola Nicaragua",
            "Redactá en Word: Hola Nicaragua",
            "Agregá en Word: Hola Nicaragua",
        ]:
            with self.subTest(query=query):
                p = propuesta(query)
                self.assertIsNotNone(p)
                self.assertEqual(p["action"], "word_write")
                self.assertEqual(p["params"], {"text": "Hola Nicaragua", "mode": "append"})
                self.assertEqual(solicitud(query)["tipo"], "accion")

    def test_not_falsely_interpreting_research_request_or_explanation(self):
        for query in [
            "Investigá inteligencia artificial y redactá un informe en Word",
            "¿Qué significa escribir en Word?",
            "Redactá en Word una investigación sobre los volcanes",
            "Escribí sobre ciencias",
        ]:
            with self.subTest(query=query):
                self.assertIsNone(propuesta(query))

    def test_rejects_unknown_params_and_oversized_content(self):
        good = {"text": "Hola", "mode": "append"}
        self.assertEqual(validar_parametros(good), "Hola")
        for bad in [
            {"text": "Hola", "mode": "replace"},
            {"text": "Hola", "mode": "append", "path": "C:\\otro.docx"},
            {"text": "", "mode": "append"},
            {"text": "A" * 6001, "mode": "append"},
        ]:
            with self.subTest(bad=str(bad)[:60]):
                with self.assertRaises(ValueError):
                    validar_parametros(bad)

    def test_word_edits_require_confirm_even_full(self):
        p = propuesta("Escribí en Word: Prueba")["params"]
        for profile in ("basico", "multimedia", "completo"):
            policy = {"enabled": caps.PERFILES[profile],
                      "auto_confirm": caps.AUTO_POR_PERFIL[profile]}
            self.assertTrue(caps.requiere_confirmacion("word_write", p, policy))
        self.assertEqual(caps.capacidad_para("word_write", p), "type_text")


class DocumentTests(unittest.TestCase):
    def test_append_and_verify_word_not_clipboard(self):
        doc = FakeDocument()
        app = FakeApp(document=doc)
        r = escribir_documento_abierto(app, "Hola\nMundo")
        self.assertTrue(app.activated)
        self.assertEqual(doc.Content.Text, "Hola\rMundo\r")
        self.assertEqual(r["status"], "VERIFIED")
        self.assertFalse(r["save_requested"])

    def test_second_append_keeps_existing_content(self):
        doc = FakeDocument("Anterior\r")
        r = escribir_documento_abierto(FakeApp(doc), "Nuevo")
        self.assertIn("Anterior", doc.Content.Text)
        self.assertIn("Nuevo", doc.Content.Text)
        self.assertTrue(r["ok"])

    def test_refuse_ambiguous_hidden_protected_or_readonly(self):
        for app in [
            FakeApp(count=0), FakeApp(count=2),
            FakeApp(visible=False),
            FakeApp(FakeDocument(readonly=True)),
            FakeApp(FakeDocument(protection=1)),
        ]:
            with self.subTest(app=app.__dict__):
                original = app.ActiveDocument.Content.Text
                with self.assertRaises(RuntimeError):
                    escribir_documento_abierto(app, "No escribir")
                self.assertEqual(app.ActiveDocument.Content.Text, original)

    def test_main_sky_assistant_routes_before_llm(self):
        from neural_core.sky_asistente_personal import interpretar, reglas
        p = interpretar("SKY, escribí en Word: prueba")
        self.assertEqual(p["action"], "word_write")
        r = reglas("SKY, escribí en Word: prueba")
        self.assertEqual(r["tipo"], "accion")
        self.assertEqual(r["propuesta"]["action"], "word_write")

    def test_agent_parameter_validation_and_permission(self):
        from agente_dispositivo import _validar
        from unittest.mock import patch
        with patch.object(caps, "parada_activa", return_value=None):
            _validar("word_write", {"text": "Hola", "mode": "append"},
                     {"enabled": ["type_text"], "auto_confirm": []})
            with self.assertRaises(ValueError):
                _validar("word_write", {"text": "Hola", "mode": "replace"},
                         {"enabled": ["type_text"], "auto_confirm": []})
            with self.assertRaises(ValueError):
                _validar("word_write", {"text": "Hola", "mode": "append"},
                         {"enabled": ["windows"], "auto_confirm": []})


if __name__ == "__main__":
    unittest.main()
