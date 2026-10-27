"""Regression: SKY opens its HUD chat from punctuation-bearing voice commands.

Only pure parsing and the local inbox are tested here. Device actions and
microphone access are never invoked in these tests.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from neural_core.sky_hud_intents import panel_chat


ROOT = Path(__file__).resolve().parents[1]


class ChatIntentTests(unittest.TestCase):
    def test_voice_transcript_with_period_is_hud_action(self):
        for phrase in (
            'Abrir panel de conversación.',
            'Abrí el panel de conversación.',
            'Abrí panel de chat de SKY',
            'Mostrame el chat',
            'Abre cuadro de texto',
            'SKY, abre panel de conversación.',
        ):
            with self.subTest(phrase=phrase):
                intent = panel_chat(phrase)
                self.assertIsNotNone(intent)
                self.assertEqual(intent['action'], 'holographic_window')
                self.assertEqual(intent['params']['subaction'], 'open_chat')

    def test_safe_scope_does_not_match_unrelated_commands(self):
        for phrase in ('hola', 'abrí Word', 'cerrá la conversación',
                       'borrá la conversación', 'publica el chat',
                       'abre un navegador', 'qué es un panel de conversación'):
            with self.subTest(phrase=phrase):
                self.assertIsNone(panel_chat(phrase))

    def test_sky_core_returns_an_action_not_a_conversational_reply(self):
        from neural_core.sky_asistente_personal import interpretar, reglas
        intent = interpretar('Abrir panel de conversación.')
        self.assertEqual(intent['params']['subaction'], 'open_chat')
        result = reglas('Abrir panel de conversación.')
        self.assertEqual(result['tipo'], 'accion')
        self.assertEqual(result['propuesta']['params']['subaction'], 'open_chat')

    def test_vosk_inbox_can_relay_open_chat_without_device_permissions(self):
        from neural_core import voz_inbox
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(voz_inbox, 'INBOX', Path(tmp) / 'voice_inbox.json'):
                event = voz_inbox.add_inbox(
                    'Abrir panel de conversación.', panel_chat('Abrir panel de conversación.'))
                self.assertEqual(voz_inbox.read_inbox()[0]['id'], event['id'])
                self.assertEqual(voz_inbox.read_inbox()[0]['params']['subaction'], 'open_chat')
                voz_inbox.dismiss_inbox(event['id'])
                self.assertEqual(voz_inbox.read_inbox(), [])

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to verify HUD JS parser')
    def test_actual_browser_hud_parser_accepts_period_and_accents(self):
        js = r'''
const fs = require("node:fs"), vm = require("node:vm");
const file = fs.readFileSync("metaverse/static/hud.js", "utf8");
const start = file.indexOf("  function ordenVentanaLocal(sentence) {");
const end = file.indexOf("  function abrirCuadroTexto() {", start);
if (start < 0 || end < start) process.exit(2);
const parser = vm.runInNewContext("(function(){" + file.slice(start, end) +
                                   "\nreturn ordenVentanaLocal;})()");
for (const phrase of [
  "Abrir panel de conversación.", "Abrí el panel de conversación.",
  "Abre chat", "Mostrar panel de SKY", "Abrí el panel de chat de SKY!"
]) {
    if (parser(phrase) !== "chat") throw Error("No match: " + phrase);
}
for (const phrase of ["Abrí Word.", "Cerrá el panel", "Borrá el chat"]) {
    if (parser(phrase) !== null) throw Error("Unexpected match: " + phrase);
}
if (!file.includes("subaction !== 'open_chat'")) throw Error("No safe inbox allowlist");
if (!file.includes("setInterval(atenderPanelSolicitadoPorVoz, 2500)"))
    throw Error("HUD Vosk inbox bridge is not enabled");
'''
        completed = subprocess.run(
            ['node', '-e', js], cwd=ROOT, capture_output=True, text=True, timeout=12)
        self.assertEqual(completed.returncode, 0,
                         (completed.stdout + completed.stderr)[-1000:])


if __name__ == '__main__':
    unittest.main()
