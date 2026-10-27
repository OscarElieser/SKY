"""No-clobber hotfix for Nicaraguan 'Enviá Ctrl+F4' voice/text grammar."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.sky_pr52_ctrl_f4_accent_repair import OLD, NEW, plan


class AccentFixTests(unittest.TestCase):
    def test_exact_one_replacement_and_missing_test_created(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            parser = root / "neural_core" / "sky_keyboard_shortcuts.py"
            parser.parent.mkdir(parents=True)
            source = b"IMPERATIVE = r'"+OLD+b"'\n" + b"CUSTOM_USER_SETTING = True\n"
            parser.write_bytes(source)
            with patch("scripts.sky_pr52_ctrl_f4_accent_repair.get_test",
                       return_value=b"import unittest\n"):
                updates, details, errors = plan(root)
            self.assertEqual(errors, [])
            self.assertEqual(len(updates), 2)
            self.assertIn(NEW, updates["neural_core/sky_keyboard_shortcuts.py"])
            self.assertIn(b"CUSTOM_USER_SETTING = True",
                          updates["neural_core/sky_keyboard_shortcuts.py"])
            self.assertEqual(parser.read_bytes(), source)
            self.assertFalse((root/"tests"/"test_sky_pr52_ctrl_f4_ast_install.py").exists())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            parser = root / "neural_core" / "sky_keyboard_shortcuts.py"
            parser.parent.mkdir(parents=True)
            parser.write_bytes(b"IMPERATIVE = r'"+NEW+b"'\n")
            test = root / "tests" / "test_sky_pr52_ctrl_f4_ast_install.py"
            test.parent.mkdir(parents=True)
            test.write_text("import unittest\n", encoding="utf-8")
            updates, _, errors = plan(root)
            self.assertEqual(errors, [])
            self.assertEqual(updates, {})

    def test_unknown_local_pattern_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            parser = root / "neural_core" / "sky_keyboard_shortcuts.py"
            parser.parent.mkdir(parents=True)
            parser.write_text("CUSTOM_PATTERN = 'enviar'\n", encoding="utf-8")
            test = root / "tests" / "test_sky_pr52_ctrl_f4_ast_install.py"
            test.parent.mkdir(parents=True)
            test.write_text("import unittest\n", encoding="utf-8")
            updates, _, errors = plan(root)
            self.assertTrue(errors)
            self.assertEqual(updates, {})


if __name__ == "__main__":
    unittest.main()
