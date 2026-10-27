"""Local diagnosis must not call remote providers or treat history as current state."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import sky_pr52_api_brain_diagnostics as diagnostics


class DiagnosticTests(unittest.TestCase):
    def test_safe_local_timeout_does_not_crash(self):
        with patch.object(diagnostics, 'urlopen', side_effect=OSError('offline')):
            status, result = diagnostics._local_json('http://127.0.0.1:8765/api/health')
        self.assertIsNone(status)
        self.assertEqual(result, {})

    def test_empty_ollama_ps_means_not_loaded_not_offline(self):
        def fake(url, timeout=1.5):
            if url.endswith('/api/tags'):
                return 200, {'models': [{'name':'qwen2.5:3b'}]}
            return 200, {'models': []}
        with patch.object(diagnostics, '_local_json', side_effect=fake):
            response = diagnostics._ollama()
        self.assertTrue(response['service_responding'])
        self.assertEqual(response['installed_models'], ['qwen2.5:3b'])
        self.assertEqual(response['models_loaded_now'], [])

    def test_no_sensitive_command_line_emission(self):
        # Inspection avoids serializing process.commandline or env values.
        from pathlib import Path
        file = Path(diagnostics.__file__).read_text(encoding='utf-8')
        self.assertNotIn('row["command_line"]', file)
        self.assertNotIn('row["env"]', file)


if __name__ == '__main__':
    unittest.main()
