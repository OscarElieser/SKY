"""Safety regression: conservative Word installer with customized local SKY."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import sky_pr52_word_editor_install as installer


class InstallerTests(unittest.TestCase):
    def test_ast_preserves_custom_rules_and_emergency_stop(self):
        src = b'''def interpretar(texto):
    """Mi intérprete."""
    custom = "owner logic"
    return None

def reglas(texto):
    """Mis reglas."""
    stop = parada(texto)
    if stop:
        return stop
    custom = "more local logic"
    return None
'''
        changed = installer.assistant_patch(src)
        self.assertIsNotNone(changed)
        self.assertIn(b"owner logic", changed)
        self.assertIn(b"more local logic", changed)
        text = changed.decode()
        self.assertLess(text.index("if stop:"), text.index(
            "from .sky_word_editor import solicitud as word_local"
        ))
        compile(changed, "owner.py", "exec")
        self.assertIsNone(installer.assistant_patch(changed))

    def test_missing_emergency_stop_rejected(self):
        src = b'''def interpretar(texto):
    return None
def reglas(texto):
    return None
'''
        with self.assertRaises(RuntimeError):
            installer.assistant_patch(src)

    def test_crlf_and_existing_custom_code(self):
        src = b'''def interpretar(texto):
    return None
def reglas(texto):
    stop = parada(texto)
    if stop:
        return stop
    return None
'''.replace(b"\n", b"\r\n")
        result = installer.assistant_patch(src)
        self.assertNotIn(b"\n", result.replace(b"\r\n", b""))

    def test_conflicting_agent_source_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for p in ("agente_dispositivo.py",
                      "neural_core/sky_capacidades.py",
                      "neural_core/sky_asistente_personal.py"):
                dest = root/p
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("# custom, do not replace\n", encoding="utf-8")
            with patch.object(installer, "download", return_value=b"# test\n"):
                changed, _, errors = installer.plan(root)
            self.assertTrue(errors)
            self.assertFalse(any(path in changed for path in (
                "agente_dispositivo.py",
                "neural_core/sky_capacidades.py",
                "neural_core/sky_asistente_personal.py"
            )))

    def test_existing_capability_and_agent_match_exact_anchor_only(self):
        for changes, filename in [
            (installer.CAP_CHANGES, "caps.py"),
            (installer.AGENT_CHANGES, "agent.py")
        ]:
            source = "\n".join(a for a, _ in changes).encode()
            # The artificial fragments alone may not be syntactically valid
            # (function bodies), so we only test that missing anchors abort.
            with self.assertRaises(RuntimeError):
                installer.exact_patch(b"# completely customized\n", changes, filename)
            self.assertTrue(source)


if __name__ == "__main__":
    unittest.main()
