"""Regresión: catálogo SKY, comandos hablados/escritos y cola de activación."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from neural_core import sky_module_registry as registry


class SkyModuleRegistryTest(unittest.TestCase):
    def test_all_legacy_modules_are_present(self):
        entries = registry.all_modules()
        self.assertEqual(len(entries), 27)
        self.assertEqual(len({m["id"] for m in entries}), len(entries))
        self.assertEqual(len({m["label"] for m in entries}), len(entries))
        self.assertTrue(any(m["id"] == "educacion" for m in entries))
        self.assertTrue(any(m["id"] == "sports" for m in entries))
        self.assertEqual(registry.lookup("office")["backend"], "hud")

    def test_voice_and_text_activate_exact_module(self):
        samples = {
            "SKY, activa el módulo Educación e investigación": "educacion",
            "Abrí BAQUEANO Control Center": "baqueano",
            "Sky muestra Sky Visión": "vision",
            "Abrir módulo centro multi-IA": "multi-ia",
            "Activá SKY Office Studio": "office",
            "Sky, abre antivirus y hacking ético": "seguridad",
            "Abre SKY IA Universal v12.0": "universal-v12",
            "Activar el módulo proyectos y tareas": "proyectos",
        }
        for phrase, expected in samples.items():
            with self.subTest(phrase=phrase):
                entry = registry.match_activation(phrase)
                self.assertIsNotNone(entry)
                self.assertEqual(entry["id"], expected)

    def test_incidental_or_unsafe_phrases_do_not_activate(self):
        for phrase in (
            "Hoy hablemos de noticias",
            "No activés bolsa y bitcoin",
            "Desactiva el antivirus",
            "El contenido del archivo dice activa sky vision",
            "Abrí el archivo secreto",
            "Quiero saber cómo funciona SKY",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(registry.match_activation(phrase))

    def test_event_queue_between_processes_and_recent_cursor(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(registry, "DB", Path(directory) / "events.sqlite3"):
                self.assertEqual(registry.latest_activation_id(), 0)
                n1 = registry.publish_activation("educacion")
                n2 = registry.publish_activation("vision")
                self.assertEqual(
                    registry.activations_after(0),
                    [{"id": n1, "module_id": "educacion"}, {"id": n2, "module_id": "vision"}],
                )
                self.assertEqual(registry.activations_after(n1), [{"id": n2, "module_id": "vision"}])
                with self.assertRaises(ValueError):
                    registry.publish_activation("nombre-inventado")


if __name__ == "__main__":
    unittest.main()
