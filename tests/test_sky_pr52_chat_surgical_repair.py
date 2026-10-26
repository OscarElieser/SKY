"""Surgical installer preserves local edits and avoids duplicate chat bridges."""
from __future__ import annotations

import unittest

from scripts.sky_pr52_chat_surgical_repair import surgically_prepare_voice


def local_voice_fixture() -> bytes:
    return ("""from neural_core.sky_asistente_personal import interpretar as interpret_command
from neural_core.voz_inbox import add_inbox

def say(message): pass

class Coordinator:
    def record_turn(self, command, message): pass

coordinador_voz=Coordinator()

def voice_loop():
    while True:
        if True:
            command = "abrí el panel de conversación"
            if command:
                intent=interpret_command(command)
                if intent:
                    say("otra tarea")
                else:
                    say("charlar")
""")


class SurgicalChatTests(unittest.TestCase):
    def test_minimal_insert_keeps_other_voice_code(self):
        local = local_voice_fixture().encode("utf-8")
        result, state = surgically_prepare_voice(local)
        self.assertIsNotNone(result)
        self.assertIn("INSERCIÓN MÍNIMA", state)
        updated = result.decode("utf-8")
        self.assertIn('say("otra tarea")', updated)
        self.assertIn('say("charlar")', updated)
        self.assertIn("SKY-HUD-CHAT-BRIDGE", updated)
        compile(updated, "sky_manos_libres.py", "exec")

    def test_idempotent_no_duplicate_insertion(self):
        updated, _ = surgically_prepare_voice(local_voice_fixture().encode("utf-8"))
        second, state = surgically_prepare_voice(updated)
        self.assertIsNone(second)
        self.assertIn("YA EXISTENTE", state)

    def test_conflicting_interpreter_layout_is_rejected(self):
        local = local_voice_fixture().replace(
            "                if intent:\n", "                if intent and other_condition:\n")
        with self.assertRaises(RuntimeError):
            surgically_prepare_voice(local.encode("utf-8"))

    def test_crlf_retained_on_windows(self):
        data = local_voice_fixture().replace("\n", "\r\n").encode("utf-8")
        result, _ = surgically_prepare_voice(data)
        self.assertIn(b"\r\n", result)
        self.assertNotIn(b"\n", result.replace(b"\r\n", b""))

    def test_only_one_voice_anchor_accepted(self):
        body = local_voice_fixture()
        body = body.replace(
            "                intent=interpret_command(command)\n",
            "                intent=interpret_command(command)\n"
            "                intent=interpret_command(command)\n",
        )
        with self.assertRaises(RuntimeError):
            surgically_prepare_voice(body.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
