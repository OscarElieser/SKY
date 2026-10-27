"""SKY must never kill an existing API/agent during another startup."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import iniciar_sky_autonomo as launcher


class ExistingSKYProcessSafetyTests(unittest.TestCase):
    def test_existing_api_skips_new_supervisor_without_killing(self):
        supervisor = launcher.SkySupervisor(
            with_voice=False, open_browser=False, with_ui=False)
        with patch.object(launcher, 'is_port_in_use', side_effect=lambda p: p == 8765), \
             patch.object(launcher, 'es_servicio_sky', return_value=True), \
             patch.object(launcher, 'kill_process_by_pid') as killer, \
             patch.object(supervisor, '_iniciar') as spawn:
            self.assertIs(supervisor.start_all(), False)
            self.assertFalse(supervisor.running)
            killer.assert_not_called()
            spawn.assert_not_called()

    def test_foreign_service_also_stays_untouched(self):
        supervisor = launcher.SkySupervisor(with_voice=False, open_browser=False)
        with patch.object(launcher, 'is_port_in_use', side_effect=lambda p: p == 8766), \
             patch.object(launcher, 'es_servicio_sky', return_value=False), \
             patch.object(launcher, 'kill_process_by_pid') as killer, \
             patch.object(supervisor, '_iniciar') as spawn:
            self.assertIs(supervisor.start_all(), False)
            killer.assert_not_called()
            spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
