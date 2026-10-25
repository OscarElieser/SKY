"""Pruebas sin internet ni acciones sobre dispositivos para OpenJarvis en SKY."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from neural_core import providers, sky_openjarvis


MESSAGES = [{"role": "system", "content": "Sos SKY."},
            {"role": "user", "content": "Hola SKY"}]


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.delenv("SKY_OPENJARVIS_ENABLED", raising=False)
    monkeypatch.delenv("SKY_OPENJARVIS_MODEL", raising=False)
    monkeypatch.delenv("SKY_LOCAL_ONLY", raising=False)
    monkeypatch.delenv("SKY_OPENJARVIS_PORT", raising=False)
    monkeypatch.setenv("SKY_METRICAS", "0")


def test_desactivado_por_defecto_y_sky_sigue_autonomo():
    assert not providers.provider_ready("openjarvis")
    assert sky_openjarvis.status()["enabled"] is False
    assert "openjarvis" not in providers.AUTO_ORDER
    assert providers.choose_provider("auto")[0] != "openjarvis"
    with pytest.raises(providers.ProviderError, match="SKY_OPENJARVIS_ENABLED"):
        providers.reply(MESSAGES, "openjarvis")


def test_no_basta_activar_sin_modelo(monkeypatch):
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    assert not providers.provider_ready("openjarvis")
    assert "Falta" in sky_openjarvis.status()["detail"]


def test_activado_por_seleccion_explicita_sin_cambiar_auto(monkeypatch):
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_MODEL", "qwen3:0.6b")
    assert providers.provider_ready("openjarvis")
    assert providers.choose_provider("openjarvis") == ("openjarvis", "qwen3:0.6b")
    assert providers.choose_provider("auto")[0] != "openjarvis"


def test_conversacion_real_por_endpoint_mock_sin_enviar_herramientas(monkeypatch):
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_MODEL", "qwen3:0.6b")
    called = []
    def fake_request(path, payload=None, timeout=3):
        called.append((path, payload, timeout))
        return {"choices": [{"message": {"role": "assistant", "content": "Hola desde SKY."}}],
                "usage": {"total_tokens": 31}}
    monkeypatch.setattr(sky_openjarvis, "_request_json", fake_request)
    assert providers.reply(MESSAGES, "openjarvis") == "Hola desde SKY."
    path, payload, timeout = called[0]
    assert path == "/v1/chat/completions"
    assert payload["model"] == "qwen3:0.6b"
    assert payload["stream"] is False
    assert payload["messages"] == MESSAGES
    assert "tools" not in payload
    assert timeout == 120


def test_forzar_host_local_y_port_validado(monkeypatch):
    monkeypatch.setenv("SKY_OPENJARVIS_PORT", "9100")
    assert sky_openjarvis._base_url() == "http://127.0.0.1:9100"
    for bad in ("0", "65536", "8o00", "-1", "", "https://servidor"):
        monkeypatch.setenv("SKY_OPENJARVIS_PORT", bad)
        with pytest.raises(ValueError):
            sky_openjarvis._base_url()


def test_diagnostico_verifica_servicio_y_modelo(monkeypatch):
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_MODEL", "qwen3:0.6b")
    def fake(path, payload=None, timeout=3):
        if path == "/health":
            return {"status": "ok"}
        if path == "/v1/models":
            return {"data": [{"id": "qwen3:0.6b"}]}
        raise AssertionError(path)
    monkeypatch.setattr(sky_openjarvis, "_request_json", fake)
    info = sky_openjarvis.status()
    assert info["healthy"] and info["model_available"]


def test_fallo_no_produce_respuesta_ficticia_ni_cambio_de_motor(monkeypatch):
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_MODEL", "qwen3:0.6b")
    def offline(*args, **kwargs):
        raise ConnectionError("Secretos de la conexión que no deben mostrarse")
    monkeypatch.setattr(sky_openjarvis, "_request_json", offline)
    with pytest.raises(providers.ProviderError, match="Error en OpenJarvis") as exc:
        providers.reply(MESSAGES, "openjarvis")
    assert "Secretos" not in str(exc.value)


def test_sky_local_only_sigue_respetando_politica_preexistente(monkeypatch):
    monkeypatch.setenv("SKY_LOCAL_ONLY", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_MODEL", "qwen3:0.6b")
    assert providers.choose_provider("auto")[0] == "ollama"
    with pytest.raises(providers.ProviderError, match="100 % local"):
        providers.choose_provider("openjarvis")


def test_no_acepta_mensajes_de_herramientas_ni_respuestas_vacias(monkeypatch):
    monkeypatch.setenv("SKY_OPENJARVIS_ENABLED", "1")
    monkeypatch.setenv("SKY_OPENJARVIS_MODEL", "qwen3:0.6b")
    with pytest.raises(ValueError, match="Rol"):
        sky_openjarvis.chat([{"role": "tool", "content": "exec"}], "qwen3:0.6b")
    monkeypatch.setattr(sky_openjarvis, "_request_json", lambda *a, **kw:
                        {"choices": [{"message": {"content": None}}]})
    with pytest.raises(ValueError, match="texto"):
        sky_openjarvis.chat(MESSAGES, "qwen3:0.6b")
