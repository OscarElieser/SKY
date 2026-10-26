"""Verify SKY runtime audit never upgrades mere endpoint presence to certification."""
from __future__ import annotations

import unittest

from scripts.sky_runtime_full_audit import (
    assess, capabilities, classify_endpoint, EXPECTED_FILES,
)


class RuntimeAuditSafetyTests(unittest.TestCase):
    def test_endpoint_presence_is_not_functionality_certification(self):
        self.assertEqual(classify_endpoint(True), "API_RESPONDE_SIN_CERTIFICACION")
        self.assertEqual(classify_endpoint(False), "NO_VERIFICADO")

    def test_word_report_requires_file_and_typing_permissions(self):
        values = capabilities({"enabled": ["launch_app", "apps_extra", "tasks"]})
        self.assertTrue(values["apps_extra"])
        self.assertFalse(values["files"])
        self.assertFalse(values["type_text"])

    def test_resource_and_voice_diagnostics_are_not_silent(self):
        report = {
            "resources": {"ram_used_pct": 94.8},
            "voice_processes": {"count": 4},
            "device_policy": {"word_report_permissions_complete": False},
            "services": {"agent_online": True, "api_online": True},
            "command_parser": {"word_report_sequence_recognized": False},
        }
        warnings = assess(report)
        self.assertGreaterEqual(len(warnings), 4)
        self.assertTrue(any("RAM" in warning for warning in warnings))
        self.assertTrue(any("Vosk" in warning for warning in warnings))

    def test_capability_inventory_covers_primary_sky_modes(self):
        for category in ("api", "agent", "voice", "hud", "office", "academic",
                         "research", "programming", "media", "phone", "security",
                         "workflow", "metaverse", "memory"):
            self.assertIn(category, EXPECTED_FILES)


if __name__ == "__main__":
    unittest.main()
