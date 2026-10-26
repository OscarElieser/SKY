"""Locking must be cross-process; no real Vosk model or microphone is used."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

from neural_core.sky_voice_single_instance import single_voice_instance


class VoiceSingletonTests(unittest.TestCase):
    def test_second_acquisition_refused_while_first_is_alive(self):
        with single_voice_instance() as first:
            self.assertTrue(first)
            with single_voice_instance() as second:
                self.assertFalse(second)
        with single_voice_instance() as next_session:
            self.assertTrue(next_session)

    def test_second_process_cannot_obtain_microphone_lock(self):
        script = ('from neural_core.sky_voice_single_instance import single_voice_instance\n'
                  'with single_voice_instance() as acquired: print(int(acquired))\n')
        with single_voice_instance() as current:
            self.assertTrue(current)
            proc = subprocess.run(
                [sys.executable, '-c', script], cwd=os.getcwd(),
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), '0')
        proc = subprocess.run(
            [sys.executable, '-c', script], cwd=os.getcwd(),
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), '1')


if __name__ == '__main__':
    unittest.main()
