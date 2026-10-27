"""Regression tests for Chrome MediaRecorder-style WebM without duration metadata."""
from __future__ import annotations

import io
import shutil
import subprocess
import unittest
import wave

from neural_core.sky_stt_local import MAX_SECONDS, _pcm_mono_16khz


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                     'Local FFmpeg and FFprobe are required')
class TestWebmDurationWithoutMetadata(unittest.TestCase):
    @staticmethod
    def streaming_webm(seconds: float) -> bytes:
        # The WebM muxer cannot write duration metadata to a streaming pipe.
        args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
                '-i', 'anullsrc=r=16000:cl=mono', '-t', str(seconds),
                '-c:a', 'libopus', '-f', 'webm', 'pipe:1']
        try:
            result = subprocess.run(args, capture_output=True, check=False, timeout=25)
        except subprocess.TimeoutExpired as exc:
            raise AssertionError('Synthetic WebM generation timed out') from exc
        if result.returncode:
            raise unittest.SkipTest('FFmpeg in this environment lacks the libopus encoder')
        if not result.stdout:
            raise AssertionError('FFmpeg generated empty WebM')
        return result.stdout

    def test_accepts_short_webm_without_metadata_duration(self):
        webm = self.streaming_webm(1.2)
        wav_bytes = _pcm_mono_16khz(webm, filename='browser.webm')
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
            seconds = wav.getnframes() / wav.getframerate()
            self.assertEqual(wav.getframerate(), 16000)
            self.assertGreater(seconds, 0.5)
            self.assertLess(seconds, 2.5)

    def test_rejects_overlong_webm_even_without_duration_metadata(self):
        webm = self.streaming_webm(MAX_SECONDS + 1.5)
        with self.assertRaisesRegex(ValueError, '60 segundos'):
            _pcm_mono_16khz(webm, filename='browser.webm')


if __name__ == '__main__':
    unittest.main()
