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


@pytest.mark.parametrize("user_command", [
    "Borra todos los archivos", "Envía un mensaje", "Compra una suscripción",
])
def test_sensitive_plans_require_confirmation(user_command):
    result = brain.plan(user_command, device="windows")
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


def test_research_requires_explicit_network_permission(monkeypatch):
    from neural_core import sky_scholarly
    monkeypatch.setattr(sky_scholarly, "search_papers", lambda *a, **kw: (
        _ for _ in ()).throw(AssertionError("No consultar red sin permiso"))
    )
    offline = brain.academic_research("educación técnica", external_search=False)
    assert offline["live_lookup"] is False
    monkeypatch.setenv("SKY_WEB_LEARNING", "0")
    blocked = brain.academic_research("educación técnica", external_search=True)
    assert blocked["reason"] == "internet_disabled"


def test_research_never_sends_obvious_secrets():
    with pytest.raises(ValueError, match="datos privados"):
        brain.academic_research("mi correo personal en investigación", external_search=True)


def test_primary_assistant_metadata_does_not_modify_actions():
    # La app registra sus routers antes de importarse el submódulo del asistente.
    # Importar primero el submódulo produce un ciclo api -> asistente -> api.
    from metaverse.api import app
    assert app is not None
    from metaverse.asistente_api import _decorate_cognition
    raw = {"tipo": "respuesta", "mensaje": "**Hola**, qué gusto."}
    result = _decorate_cognition(raw, "Qué alegría, funcionó")
    assert raw.get("sky_cognition") is None
    assert result["sky_cognition"]["persona"]["animation"] == "alegre"
    assert result["sky_cognition"]["emotion_is_simulated"]
    assert "**" not in result["sky_cognition"]["speech_text"]
    action = {"tipo": "accion", "mensaje": "Ejecutar", "propuesta": {"action": "open_url"}}
    assert _decorate_cognition(action, "Abrí YouTube") is action


def test_hud_additive_integration_keeps_existing_controls():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "metaverse" / "static" / "hud.js").read_text(encoding="utf-8")
    assert src.count("cognitive: true") == 2
    assert "data.sky_cognition?.speech_text" in src
    assert "document.body.dataset.skyMood = selected" in src
    assert "soltarFrases(false)" in src
    assert "confirmar(card, titulo" in src


def test_authenticated_endpoints(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("SKY_REFLECTIVE_DB", str(tmp_path / "reflection.sqlite3"))
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
        assert response.json()["reflective_learning"]["automatic_install"] is False
        reflection_denied = client.get("/api/sky/cognition/reflective-metrics")
        assert reflection_denied.status_code in (401, 403)
        reflection_ok = client.get("/api/sky/cognition/reflective-metrics", headers=headers)
        assert reflection_ok.status_code == 200
        assert reflection_ok.json()["metrics"]["total_observations"] == 0
        assert reflection_ok.json()["capabilities"]["automatic_install"] is False
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
        native_denied = client.get("/api/sky/cognition/native-evolution")
        assert native_denied.status_code in (401, 403)
        native_ok = client.get("/api/sky/cognition/native-evolution", headers=headers)
        assert native_ok.status_code == 200
        assert native_ok.json()["external_inference_required"] is False
        advice = client.post("/api/sky/cognition/adaptive-plan", headers=headers,
                             json={"query": "elimina mis archivos", "device": "android"})
        assert advice.status_code == 200
        assert advice.json()["review_required"] is True
        assert advice.json()["permission_granted"] is False
        assert advice.json()["action_executed"] is False
