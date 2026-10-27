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


    def test_voice_mismatched_pid_does_not_kill_a_healthy_other_listener(self):
        """A live SKY Vosk listener must not be killed for another PID's state."""
        import time
        from types import SimpleNamespace

        supervisor = launcher.SkySupervisor(with_voice=False, open_browser=False)
        supervisor.intervalo_sonda = 0
        voz = launcher.Servicio(
            "voice", [], sonda=lambda: (False, "todavía no informó su estado"),
            colgado_tras=90,
        )
        voz.proc = SimpleNamespace(pid=1111, poll=lambda: None)
        voz.estado = "activo"
        voz.primera_falla = time.time() - 120
        supervisor.servicios["voice"] = voz
        with patch.object(launcher, "_pid_escucha_vivo", return_value=2222), \
             patch.object(launcher, "sonda_voz", return_value=(True, "escuchando")) as probe, \
             patch.object(supervisor, "_terminar") as terminate:
            supervisor.revisar()
            terminate.assert_not_called()
            probe.assert_called_once_with(2222)
        self.assertIsNotNone(voz.proc)
        self.assertEqual(voz.estado, "degradado")
        self.assertIn("otro PID (2222)", voz.causa)
        self.assertEqual(voz.primera_falla, 0.0)
        self.assertEqual(voz.fallas_sonda, 0)

    def test_voice_watchdog_still_recovers_when_other_pid_has_no_heartbeat(self):
        """A dead or stale alternate voice state must not disable recovery."""
        import time
        from types import SimpleNamespace

        supervisor = launcher.SkySupervisor(with_voice=False, open_browser=False)
        supervisor.intervalo_sonda = 0
        voz = launcher.Servicio(
            "voice", [], sonda=lambda: (False, "todavía no informó su estado"),
            colgado_tras=90,
        )
        voz.proc = SimpleNamespace(pid=1111, poll=lambda: None)
        voz.estado = "activo"
        voz.primera_falla = time.time() - 120
        supervisor.servicios["voice"] = voz
        with patch.object(launcher, "_pid_escucha_vivo", return_value=2222), \
             patch.object(launcher, "sonda_voz", return_value=(False, "sin latido")), \
             patch.object(launcher, "_registrar_reinicio"), \
             patch.object(supervisor, "_terminar") as terminate:
            supervisor.revisar()
            terminate.assert_called_once_with(voz)
        self.assertIsNone(voz.proc)
        self.assertEqual(voz.estado, "error")
        self.assertIn("colgado", voz.causa)
        self.assertGreater(voz.proximo_intento, time.time())


if __name__ == '__main__':
    unittest.main()
