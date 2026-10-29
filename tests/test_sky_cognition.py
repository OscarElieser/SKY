"""Pruebas aisladas de la ampliación cognitiva sin acceso a dispositivos ni red."""
from __future__ import annotations

import pytest

from neural_core import sky_cognition as brain


def test_plans_never_execute_or_grant_permissions():
    result = brain.plan("Abre YouTube y reproduce música", device="android")
    assert result["intent"] == "accion_solicitada"
    assert result["requires_confirmation"]
    assert result["executed_steps"] == 0
    assert result["status"] == "proposed"
    assert result["delegation"] == "not_sent"
    assert all(step["state"] == "proposed" for step in result["steps"])


@pytest.mark.parametrize("request", [
    "Borra todos los archivos", "Envía un mensaje", "Compra una suscripción",
])
def test_sensitive_plans_require_confirmation(request):
    result = brain.plan(request, device="windows")
    assert result["risk"] == "alto"
    assert result["requires_confirmation"]
    assert not result["execution_performed"]


def test_personal_memory_never_flows_to_cloud():
    with pytest.raises(ValueError, match="motor local"):
        brain.context("¿Qué recuerdo?", execution="cloud", include_personal=True)


def test_cloud_context_does_not_read_private_memory(monkeypatch):
    from neural_core import sky_neural_memory
    monkeypatch.setattr(sky_neural_memory, "facts", lambda *a, **kw: (
        _ for _ in ()).throw(AssertionError("No leer memoria personal"))
    )
    result = brain.context("Ayudame con un documento", execution="cloud", include_public=False)
    assert result["personal"] == []
    assert result["personal_included"] is False


def test_local_personal_memory_requires_existing_encryption(monkeypatch):
    from neural_core import sky_neural_memory
    monkeypatch.setattr(sky_neural_memory, "facts",
                        lambda *args: (_ for _ in ()).throw(RuntimeError("sin clave")))
    result = brain.context("proyecto educativo", execution="local",
                           include_personal=True, include_public=False)
    assert result["personal"] == []
    assert result["warnings"]


def test_public_research_is_cached_only(monkeypatch):
    from neural_core import sky_web_learning
    from neural_core import sky_programming_learning
    monkeypatch.setattr(sky_web_learning, "related",
                        lambda query, limit: [{
                            "headline": "Novedades Flutter",
                            "source": "Fuente", "source_url": "https://news.google.com/a",
                            "published": "2026-10-28T00:00:00Z",
                        }])
    monkeypatch.setattr(sky_programming_learning, "latest",
                        lambda topic, limit: [{
                            "title": "Flutter", "project": "Flutter",
                            "url": "https://github.com/flutter/flutter/releases/tag/v1",
                            "published": "2026-10-28T00:00:00Z",
                        }])
    data = brain.context("novedades Flutter", execution="cloud")
    assert len(data["references"]) == 2
    assert all(not ref["verified_full_text"] for ref in data["references"])
    assert not data["live_search_performed"]
    assert not data["action_executed"]


def test_personality_is_presentational_only():
    obj = brain.emotion_style("Estoy feliz con los resultados")
    assert obj["animation"] == "alegre"
    assert obj["address"] == "tú"
    assert obj["emotion_is_simulated"]
    assert not obj["sentience_claim"]


def test_tts_preserves_meaning_without_markdown():
    original = "**Hola**, visita [la guía](https://example.com/guia)."
    spoken = brain.spoken_text(original)
    assert "Hola" in spoken and "la guía" in spoken
    assert "https://" not in spoken and "**" not in spoken
    assert original.startswith("**Hola**")


def test_no_automatic_learning_or_cross_device_sync():
    status = brain.capabilities()
    assert status["features"]["planning"] == "consultative_no_execution"
    assert status["independent_model_training"] is False
    assert status["automatic_device_action"] is False
    assert status["cross_device_memory_sync"] is False


def test_authenticated_endpoints(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("SKY_API_KEY", "sky-owner-cognition-tests-key-2026")
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED", "0")
    monkeypatch.setenv("SKY_WEB_LEARNING", "0")
    from metaverse.api import app
    with TestClient(app) as client:
        denied = client.get("/api/sky/cognition/capabilities")
        assert denied.status_code in (401, 403)
        headers = {"X-SKY-KEY": "sky-owner-cognition-tests-key-2026"}
        response = client.get("/api/sky/cognition/capabilities", headers=headers)
        assert response.status_code == 200
        assert response.json()["integration"] == "additive"
        plan = client.post("/api/sky/cognition/plan",
                           headers=headers,
                           json={"query": "Abrí YouTube", "device": "android"})
        assert plan.status_code == 200
        assert plan.json()["executed_steps"] == 0
        forbidden = client.post("/api/sky/cognition/context",
                                headers=headers,
                                json={"query": "mis preferencias", "include_personal": True,
                                      "execution": "cloud"})
        assert forbidden.status_code == 422
