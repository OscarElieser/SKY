"""AST-based installer tests: preserve custom interpreter without executing Win32."""
from __future__ import annotations

import unittest

from scripts.sky_pr52_ctrl_f4_ast_install import assistant_ast_patch


CUSTOM = '''from __future__ import annotations
def interpretar(texto: str):
    """A custom owner interpreter with additional modules."""
    extra = "preservar mi integración"
    if texto == "saludos":
        return "respuesta"
    return None

def reglas(texto):
    """Owner's customized conversation rules."""
    from .sky_aprendizaje import _norm
    stop = parada(_norm(texto))
    if stop:
        return stop
    extra = "respuestas personalizadas"
    return None
'''


class CustomAssistantAstTests(unittest.TestCase):
    def test_custom_functions_preserved_and_ctrl_f4_added_after_stop(self):
        changed, status = assistant_ast_patch(CUSTOM.encode("utf-8"))
        self.assertIn("INSERCIÓN AST", status)
        self.assertIsNotNone(changed)
        text = changed.decode("utf-8")
        compile(text, "custom_sky.py", "exec")
        self.assertIn('extra = "preservar mi integración"', text)
        self.assertIn('extra = "respuestas personalizadas"', text)
        self.assertLess(text.index("if stop:"), text.index("from .sky_keyboard_shortcuts import solicitud"))
        self.assertIn("propuesta as atajo_escritorio", text)
        self.assertIn("return atajo_seguro", text)

    def test_idempotent_when_already_updated(self):
        first, _ = assistant_ast_patch(CUSTOM.encode())
        second, status = assistant_ast_patch(first)
        self.assertIsNone(second)
        self.assertIn("YA INSTALADO", status)

    def test_rejects_unknown_emergency_stop_guard(self):
        corrupt = CUSTOM.replace("if stop:\n        return stop",
                                  "if stop_error:\n        return stop")
        with self.assertRaises(RuntimeError):
            assistant_ast_patch(corrupt.encode())

    def test_no_change_when_syntax_invalid(self):
        with self.assertRaises(SyntaxError):
            assistant_ast_patch(b"def interpretar(: pass")

    def test_preserves_crlf_windows(self):
        data = CUSTOM.replace("\n", "\r\n").encode("utf-8")
        changed, _ = assistant_ast_patch(data)
        self.assertIn(b"\r\n", changed)
        self.assertNotIn(b"\n", changed.replace(b"\r\n", b""))


if __name__ == "__main__":
    unittest.main()
