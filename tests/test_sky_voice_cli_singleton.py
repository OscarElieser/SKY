"""La lista de micrófonos no debe adquirir el candado Vosk.

Prueba el punto de entrada sin importar modelos Vosk ni abrir dispositivos.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from neural_core import sky_voice_single_instance


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "sky_manos_libres.py"


def entrypoint(argv, callback):
    script = ast.parse(ENTRY.read_text(encoding="utf-8"))
    function = next(node for node in script.body
                    if isinstance(node, ast.FunctionDef) and node.name == "_start_single_instance")
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {
        "sys": SimpleNamespace(argv=["sky_manos_libres.py", *argv], exit=sys.exit),
        "main": callback,
    }
    exec(compile(module, str(ENTRY), "exec"), namespace)
    return namespace["_start_single_instance"]


class TestVoiceCliSingleton(unittest.TestCase):
    def test_list_devices_no_lock_when_listener_is_active(self):
        actions = []
        def unexpected_lock():
            raise AssertionError("No debe tocar el mutex Vosk")
        with patch.object(sky_voice_single_instance, "single_voice_instance", unexpected_lock):
            entrypoint(["--list-input-devices"], lambda: actions.append("list"))()
        self.assertEqual(actions, ["list"])

    def test_listener_still_requires_exclusive_lock(self):
        actions = []
        @contextmanager
        def granted():
            actions.append("lock")
            yield True
            actions.append("unlock")
        with patch.object(sky_voice_single_instance, "single_voice_instance", granted):
            entrypoint([], lambda: actions.append("start"))()
        self.assertEqual(actions, ["lock", "start", "unlock"])

    def test_second_listener_does_not_start(self):
        started = []
        @contextmanager
        def denied():
            yield False
        with patch.object(sky_voice_single_instance, "single_voice_instance", denied):
            with self.assertRaises(SystemExit) as exc:
                entrypoint([], lambda: started.append("start"))()
        self.assertEqual(exc.exception.code, 42)
        self.assertEqual(started, [])


if __name__ == "__main__":
    unittest.main()
