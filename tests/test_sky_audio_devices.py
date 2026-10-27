"""No sound recording; test only microphone ordering and owner selection."""
from __future__ import annotations

import unittest
from neural_core.sky_audio_devices import candidate_inputs


DEVICES = [
    {"name": "Microsoft Sound Mapper - Input", "max_input_channels": 2},
    {"name": "Microfono Logitech USB Headset", "max_input_channels": 1},
    {"name": "Altavoces", "max_input_channels": 0},
    {"name": "Microfono Realtek", "max_input_channels": 2},
]


class AudioDeviceSelectionTests(unittest.TestCase):
    def test_prefers_concrete_device_over_sound_mapper(self):
        self.assertEqual(candidate_inputs(DEVICES)[0][0], 1)

    def test_respects_default_microphone(self):
        self.assertEqual(candidate_inputs(DEVICES, default_index=3)[0][0], 3)

    def test_explicit_logitech_selection(self):
        self.assertEqual(candidate_inputs(DEVICES, choice="LOGITECH"), [
            (1, "Microfono Logitech USB Headset")])

    def test_explicit_device_number(self):
        self.assertEqual(candidate_inputs(DEVICES, choice="1")[0][0], 1)

    def test_bad_device_fails_closed(self):
        with self.assertRaises(ValueError):
            candidate_inputs(DEVICES, choice="99")
        with self.assertRaises(ValueError):
            candidate_inputs(DEVICES, choice="no_such_microphone")


if __name__ == "__main__":
    unittest.main()
