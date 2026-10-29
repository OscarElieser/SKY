"""SKY academic writer tests with controlled provider responses."""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_writer_uses_actual_provider_and_marks_unverified(monkeypatch):
    sys.path.insert(0, str(ROOT))
    from neural_core import sky_academic_writer as writer
    from neural_core import providers
    monkeypatch.setattr(providers, "choose_provider", lambda name, area: ("ollama", "local-test"))
    seen = {}
    def fake_reply(messages, engine, model, **kwargs):
        seen["messages"] = messages
        return "## Metodología\nEnfoque cualitativo propuesto; requiere validación."
    monkeypatch.setattr(providers, "reply", fake_reply)
    result = writer.draft_section(
        "Turismo sostenible en Nicaragua",
        "Crear una tesis con metodología verificable y citas reales.",
        "metodologia")
    assert result["status"] == "draft"
    assert result["verified_sources"] is False
    assert "Metodología" in result["content"]
    assert seen["messages"][0]["role"] == "system"


def test_unknown_section_fails_before_provider():
    sys.path.insert(0, str(ROOT))
    from neural_core.sky_academic_writer import draft_section
    with pytest.raises(ValueError, match="Sección"):
        draft_section("Turismo sostenible en Nicaragua",
                      "Redactar un estudio científico verificable.",
                      "seccion_inexistente")
