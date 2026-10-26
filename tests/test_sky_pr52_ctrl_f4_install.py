"""Keep local custom code intact; reject conflicts in Win32 shortcut repair."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import sky_pr52_ctrl_f4_install as installer


class InstallerTests(unittest.TestCase):
    def test_only_explicitly_listed_files_touched(self):
        expected = {"neural_core/sky_asistente_personal.py",
                    "neural_core/sky_capacidades.py", "agente_dispositivo.py",
                    "neural_core/sky_keyboard_shortcuts.py",
                    "tests/test_sky_keyboard_shortcuts.py"}
        self.assertEqual(set(installer.EDITS) | set(installer.NEW), expected)
        self.assertNotIn("sky_manos_libres.py", expected)
        self.assertNotIn("metaverse/api.py", expected)

    def test_preserves_custom_lines_before_anchor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, patches in installer.EDITS.items():
                dst = root / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                # Mimic a valid file while retaining custom comments.
                content = "# custom owner lines\n" + "\n".join(a for a,b in patches)
                dst.write_text(content + "\n", encoding="utf-8")
            with patch.object(installer, "download", side_effect=lambda p: b"# new file\n"):
                updates, changes, issues = installer.plan(root)
            self.assertFalse(issues)
            self.assertEqual(len(updates), 5)
            for name in installer.EDITS:
                self.assertIn(b"# custom owner lines", updates[name])
                self.assertNotIn("CONFLICTO", dict(changes)[name])

    def test_rejects_modified_source_without_overwriting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in installer.EDITS:
                f = root / name
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("# source changed significantly\n", encoding="utf-8")
            with patch.object(installer, "download", return_value=b"# new file\n"):
                _, _, issues = installer.plan(root)
            self.assertGreaterEqual(len(issues), 3)
            for name in installer.EDITS:
                self.assertEqual((root / name).read_text(),
                                 "# source changed significantly\n")


if __name__ == "__main__":
    unittest.main()
