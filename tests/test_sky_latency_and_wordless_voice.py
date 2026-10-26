"""Focused regression tests for non-blocking metrics and opt-in natural voice.

No audio devices, external AI providers, or physical desktop actions are used.
"""
from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from neural_core import sky_http_metrics_queue as metrics


class HTTPMetricsTests(unittest.TestCase):
    def test_slow_sqlite_does_not_block_the_api_response(self):
        self.assertTrue(metrics.flush(3))
        started = threading.Event()
        release = threading.Event()
        saved = []

        def slow_record(path, ms, status):
            started.set()
            release.wait(timeout=2)
            saved.append(('telemetry', path, status))

        def save_kpi(*args, **kwargs):
            saved.append(('kpi', args, kwargs))

        try:
            with patch('neural_core.sky_telemetry.record', side_effect=slow_record), \
                 patch('neural_core.sky_metricas.registrar', side_effect=save_kpi):
                start = time.perf_counter()
                accepted = metrics.enqueue('/api/health', 'GET', '/api/health', 12, 200)
                elapsed = time.perf_counter() - start
                self.assertTrue(accepted)
                self.assertLess(elapsed, 0.2, 'enqueue must never wait on slow SQLite')
                self.assertTrue(started.wait(timeout=2))
                release.set()
                self.assertTrue(metrics.flush(3))
            self.assertEqual(saved[0], ('telemetry', '/api/health', 200))
            self.assertEqual(saved[1][1][0:3], ('api', 'GET /api/health', True))
        finally:
            release.set()
            metrics.flush(3)

    def test_static_assets_skip_kpi_but_keep_telemetry_filter(self):
        self.assertTrue(metrics.flush(3))
        with patch('neural_core.sky_telemetry.record') as record, \
             patch('neural_core.sky_metricas.registrar') as kpi:
            self.assertTrue(metrics.enqueue('/static/hud.js', 'GET', '', 5, 200))
            self.assertTrue(metrics.flush(3))
            record.assert_called_once()
            kpi.assert_not_called()

    def test_status_exposes_bounded_queue_and_drop_count(self):
        status = metrics.queue_status()
        self.assertEqual(status['capacity'], 256)
        self.assertGreaterEqual(status['dropped'], 0)


class WordlessVoiceTests(unittest.TestCase):
    def test_only_direct_speech_starts_new_turn(self):
        from sky_manos_libres import is_directed_speech
        self.assertTrue(is_directed_speech('abri word'))
        self.assertTrue(is_directed_speech('redacta un informe'))
        self.assertTrue(is_directed_speech('muestra el chat'))
        self.assertFalse(is_directed_speech('en el programa de anoche'))
        self.assertFalse(is_directed_speech('el vecino esta hablando'))

    def test_existing_wake_recognition_still_works(self):
        from sky_manos_libres import text_after_wake
        self.assertEqual(text_after_wake('sky abre word'), 'abre word')
        self.assertIsNone(text_after_wake('abre word'))


if __name__ == '__main__':
    unittest.main()
