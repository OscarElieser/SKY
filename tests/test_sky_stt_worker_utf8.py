"""Regression tests for isolated STT stdout encoding on Windows cp1252.

No model downloads, audio hardware, network, or private tokens required.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from neural_core import sky_stt_worker_v106 as worker
from neural_core import sky_stt_isolated_v106 as isolated


class WorkerEncodingTests(unittest.TestCase):
    def test_worker_emits_utf8_json_even_when_console_is_cp1252(self):
        with tempfile.TemporaryDirectory(prefix='sky_stt_worker_test_') as folder:
            audio = Path(folder) / 'audio.wav'
            with wave.open(str(audio), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b'\x00\x00' * 1600)

            expected = {'text': 'Sí, SKY escuchó: canción y corazón',
                        'segments': [], 'engine': 'faster-whisper'}
            raw = io.BytesIO()
            cp1252_stdout = io.TextIOWrapper(raw, encoding='cp1252',
                                              write_through=True)
            with patch.object(worker.base, 'transcribe', return_value=expected):
                with patch.object(worker.sys, 'stdout', cp1252_stdout):
                    self.assertEqual(worker.main(['--file', str(audio), '--language', 'es']), 0)
                    cp1252_stdout.flush()
            self.assertEqual(json.loads(raw.getvalue()), expected)
            cp1252_stdout.detach()

    def test_parent_explicitly_uses_utf8_and_does_not_pass_secrets(self):
        payload = {'text': 'Puedo oír la música', 'segments': []}
        result = subprocess.CompletedProcess(args=['worker'], returncode=0,
                                             stdout=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                             stderr=b'')
        with patch.object(isolated.base, 'capabilities', return_value={'available': True}), \
             patch.object(isolated.base, '_pcm_mono_16khz', return_value=b'dummy-pcm'), \
             patch.object(isolated.base, 'model_directory', return_value=Path('modelos')), \
             patch.object(isolated.subprocess, 'run', return_value=result) as run, \
             patch.dict(os.environ, {'SKY_KEY': 'sensitive-test-value'}):
            result = isolated.isolated_transcribe(b'dummy', filename='voz.wav', language='es')
        env = run.call_args.kwargs['env']
        self.assertEqual(env['PYTHONIOENCODING'], 'utf-8')
        self.assertNotIn('SKY_KEY', env)
        self.assertEqual(result['text'], payload['text'])
        self.assertTrue(result['process_isolated'])


if __name__ == '__main__':
    unittest.main()
