"""Installer preserves customized voice, HUD and API; rejects changed anchors."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import sky_pr52_live_news_install as updater


class InstallerTests(unittest.TestCase):
    def test_only_two_targeted_insertions_and_two_new_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ("sky_manos_libres.py", "metaverse/api.py", "metaverse/static/hud.js"):
                dst = root / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text("NO TOCAR", encoding="utf-8")
            for name, (before, _) in updater.CHANGES.items():
                dst = root / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text("# conservar personalizado\ndef test():\n" + before + "\n", encoding="utf-8")
            def test_download(path):
                return ("# nueva utilidad: " + path + "\n").encode("utf-8")
            with patch.object(updater, "download", side_effect=test_download):
                plan, rows, errors = updater.prepare(root)
            self.assertFalse(errors)
            self.assertEqual(len(plan), 4)
            self.assertEqual(set(plan), set(updater.NEW) | set(updater.CHANGES))
            for name in ("sky_manos_libres.py", "metaverse/api.py", "metaverse/static/hud.js"):
                self.assertEqual((root / name).read_text(encoding="utf-8"), "NO TOCAR")
                self.assertNotIn(name, plan)
            for name in updater.CHANGES:
                self.assertIn(b"# conservar personalizado", plan[name])

    def test_crlf_inputs_preserve_newlines_and_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, (before, _) in updater.CHANGES.items():
                dst = root / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                data = ("# conservar propietario\n" + "def test():\n" + before + "\n")
                dst.write_bytes(data.replace("\n", "\r\n").encode("utf-8"))
            with patch.object(updater, "download",
                              side_effect=lambda p: ("# nueva utilidad: " + p + "\n").encode("utf-8")):
                plan, _, errors = updater.prepare(root)
                self.assertFalse(errors)
                self.assertEqual(len(plan), 4)
                for name in updater.CHANGES:
                    self.assertIn(b"\r\n", plan[name])
                    self.assertNotIn(b"\n", plan[name].replace(b"\r\n", b""))
                for name, contents in plan.items():
                    file = root / name
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(contents)
                again, _, second_errors = updater.prepare(root)
                self.assertFalse(second_errors)
                self.assertEqual(again, {})

    def test_unrecognized_chat_version_blocks_every_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in updater.CHANGES:
                f = root / name
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("codigo cambiado sin punto de insercion", encoding="utf-8")
            with patch.object(updater, "download", return_value=b"# new module\n"):
                plan, rows, errors = updater.prepare(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("CONFLICTO" in status for _, status in rows))
            # No disk edits occur in prepare, even if the plan has new files.
            for name in updater.CHANGES:
                self.assertIn("codigo cambiado", (root / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
