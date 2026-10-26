"""Real Ctrl+F4 Word command: parsers, permissions and confirmations.

No keyboard events are ever sent by this test suite.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from neural_core.sky_keyboard_shortcuts import solicitud, propuesta
from neural_core import sky_capacidades as caps


class ShortcutTests(unittest.TestCase):
    def test_explicit_ctrl_f4_request_is_not_a_media_action(self):
        for sentence in (
            "haz el intento de poner ctrl+f4",
            "Presioná Ctrl+F4",
            "SKY, pulsa Control+F4 en Word",
            "Enviá la combinación Ctrl + F4",
        ):
            with self.subTest(sentence=sentence):
                result = solicitud(sentence)
                self.assertIsNotNone(result)
                self.assertEqual(result["tipo"], "accion")
                self.assertEqual(result["propuesta"]["action"], "keyboard_shortcut")
                self.assertEqual(result["propuesta"]["params"],
                                 {"shortcut": "ctrl+f4", "expected_app": "winword.exe"})

    def test_ordinary_explanations_do_not_execute(self):
        for sentence in (
            "¿Qué significa Ctrl+F4?",
            "Explicame la combinación Ctrl+F4",
            "Ctrl+F4",
            "Abrí Word",
            "mini reproductor",
        ):
            with self.subTest(sentence=sentence):
                self.assertIsNone(solicitud(sentence))

    def test_multiple_shortcuts_are_refused_not_silently_ignored(self):
        r = solicitud("Presioná Ctrl+F4 y Alt+F4")
        self.assertEqual(r["tipo"], "respuesta")
        self.assertNotIn("propuesta", r)

    def test_never_auto_confirm_even_in_full_profile(self):
        for profile in ("basico", "multimedia", "completo"):
            with self.subTest(profile=profile):
                policy = {"enabled": caps.PERFILES[profile],
                          "auto_confirm": caps.AUTO_POR_PERFIL[profile]}
                params = {"shortcut": "ctrl+f4", "expected_app": "winword.exe"}
                self.assertEqual(caps.nivel_riesgo("keyboard_shortcut", params), 3)
                self.assertTrue(caps.requiere_confirmacion("keyboard_shortcut",
                                                           params, policy))
                self.assertEqual(caps.capacidad_para("keyboard_shortcut", params),
                                 "windows")

    def test_parser_precedes_llm_and_player(self):
        from neural_core.sky_asistente_personal import interpretar, reglas
        self.assertEqual(interpretar("haz el intento de poner ctrl+f4")["action"],
                         "keyboard_shortcut")
        result = reglas("haz el intento de poner ctrl+f4")
        self.assertEqual(result["tipo"], "accion")
        self.assertEqual(result["propuesta"]["action"], "keyboard_shortcut")

    def test_agent_rejects_unknown_keyboard_sequences(self):
        from agente_dispositivo import _validar
        policy = {"enabled": ["windows"], "auto_confirm": []}
        with patch.object(caps, "parada_activa", return_value=None):
            with self.assertRaises(ValueError):
                _validar("keyboard_shortcut",
                         {"shortcut": "alt+f4", "expected_app": "winword.exe"}, policy)
            with self.assertRaises(ValueError):
                _validar("keyboard_shortcut",
                         {"shortcut": "ctrl+f4", "expected_app": "chrome.exe"}, policy)
            _validar("keyboard_shortcut",
                     {"shortcut": "ctrl+f4", "expected_app": "winword.exe"}, policy)


if __name__ == "__main__":
    unittest.main()
