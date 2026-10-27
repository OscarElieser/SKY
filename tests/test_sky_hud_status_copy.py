"""Regresión visual: los estados de espera de SKY no exponen motores internos."""
from pathlib import Path

HUD = Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js"


def test_waiting_state_uses_natural_language():
    js = HUD.read_text(encoding="utf-8")
    assert "thinking: 'UN MOMENTO'" in js
    assert "setState('thinking', 'Estoy preparando tu respuesta…')" in js
    assert "setState('thinking', 'La respuesta está tardando más de lo normal…')" in js
    assert "Ollama sigue procesando la respuesta" not in js
    assert "thinking: 'PROCESANDO'" not in js


def test_stream_timeout_keeps_real_error_and_limit():
    js = HUD.read_text(encoding="utf-8")
    assert "setTimeout(() => control.abort(), 90000)" in js
    assert "La respuesta tardó demasiado. Probá otra vez" in js
    assert "if (ev.final)" in js
    assert "setState('error', 'No se completó la respuesta')" in js
