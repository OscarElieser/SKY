"""Select a real audio input deterministically without touching the microphone.

The system input is preferred, then viable concrete devices; Windows Sound
Mapper aliases are fallback only. Explicit owner choice never falls back to an
unrelated microphone silently.
"""
from __future__ import annotations


def candidate_inputs(devices, default_index=None, choice=""):
    """Return (index, name) pairs for candidate input devices.

    choice accepts a device index or a case-insensitive part of its name.
    """
    inputs = [(i, str(device.get("name") or "Dispositivo " + str(i)))
              for i, device in enumerate(devices)
              if int(device.get("max_input_channels") or 0) > 0]
    selected = str(choice or "").strip()
    if selected:
        if selected.isdigit():
            matches = [x for x in inputs if x[0] == int(selected)]
        else:
            matches = [x for x in inputs if selected.lower() in x[1].lower()]
        if not matches:
            raise ValueError("El micrófono seleccionado no figura entre las entradas.")
        return matches
    preferred = []
    if isinstance(default_index, int) and default_index >= 0:
        preferred = [x for x in inputs if x[0] == default_index]
    # Prefer physical devices to wrappers, e.g. Microsoft Sound Mapper.
    remaining = [x for x in inputs if x not in preferred]
    remaining.sort(key=lambda x: (
        1 if any(name in x[1].lower() for name in
                 ("sound mapper", "controlador primario", "primary sound capture")) else 0,
        x[0],
    ))
    return preferred + remaining


def input_summary(devices) -> list[dict]:
    return [{"index": i, "name": name} for i, name in
            candidate_inputs(devices)]
