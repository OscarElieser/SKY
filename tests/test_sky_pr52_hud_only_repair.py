"""The HUD-only installer must never read/write customized Vosk source."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import sky_pr52_hud_only_repair as hudfix


class HudOnlyInstallerTests(unittest.TestCase):
    def test_voice_file_cannot_be_planned_or_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sky_manos_libres.py").write_text(
                "codigo_personal_de_voz = 'no tocar'\n", encoding="utf-8")
            expected_voice = (root / "sky_manos_libres.py").read_bytes()
            for name in hudfix.EDITED:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(("base-" + name).encode("utf-8"))
            def fake_download(ref, relative):
                if relative == "sky_manos_libres.py":
                    raise AssertionError("Listener must not be downloaded")
                tag = "updated" if ref == hudfix.TARGET else "base"
                return (tag + "-" + relative).encode("utf-8")
            with patch.object(hudfix, "download", side_effect=fake_download):
                changes, plan, problems = hudfix.build_plan(root, root / "scratch")
            self.assertEqual(problems, [])
            self.assertNotIn("sky_manos_libres.py", plan)
            self.assertEqual((root / "sky_manos_libres.py").read_bytes(), expected_voice)
            self.assertEqual(len(plan), 4)
            self.assertTrue(any(name == "sky_manos_libres.py"
                                and "NO SE TOCA" in status
                                for name, status in changes))

    def test_scope_contains_only_hud_and_core(self):
        self.assertEqual(set(hudfix.EDITED), {
            "metaverse/static/hud.js", "neural_core/sky_asistente_personal.py"})
        self.assertEqual(set(hudfix.NEW), {
            "neural_core/sky_hud_intents.py", "tests/test_sky_hud_chat_voice_bridge.py"})
        self.assertFalse(any("sky_manos_libres" in rel for rel in
                             hudfix.EDITED + hudfix.NEW))


if __name__ == "__main__":
    unittest.main()
