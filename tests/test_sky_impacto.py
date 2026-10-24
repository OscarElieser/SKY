"""Pruebas deterministas de SKY Impacto: nunca dependen de internet ni de modelos de IA."""
from __future__ import annotations

import pytest

from neural_core.sky_impacto import (
    SOURCES, _SafeRedirect, classify, consult_source, impact_instructions,
    innovation_project, judge_project, lesson_plan, lesson_step, list_sources,
    research_plan, verify_references,
)


def test_sources_are_explicit_and_unconnected():
    sources = list_sources()
    assert len(sources) >= 15
    assert all(s["connection"] == "catalogued_not_connected" for s in sources)
    assert all(s["url"].startswith("https://") for s in sources)
    assert {"mined", "inatec", "marena", "intur", "unesco", "worldbank", "europarl"}.issubset(SOURCES)
    assert {s["id"] for s in list_sources("educacion")} == {"mined", "inatec", "unesco", "uis"}
    with pytest.raises(ValueError):
        list_sources("http://localhost")


def test_classify_without_accents_and_plan_requires_evidence():
    assert classify("contaminación ambiental en Managua") == "ambiente"
    plan = research_plan("transporte urbano en Managua", "tesis")
    assert plan["status"] == "plan_only"
    assert plan["verified_research_completed"] is False
    assert "Marco teórico y conceptual" in plan["sections"]
    assert any(s["id"] == "worldbank" for s in plan["sources_to_consult"])
    with pytest.raises(ValueError):
        research_plan("x", "documento_inexistente")


def test_lesson_is_staged_and_voice_ready_without_fake_assessment():
    lesson = lesson_plan("los números naturales hasta 20", "inicial", 35)
    assert lesson["level"] == "inicial"
    assert len(lesson["steps"]) == 6
    assert sum(s["duration_minutes"] for s in lesson["steps"]) == 35
    assert "Juego" in lesson["methodology"]
    step = lesson_step(lesson, 2, "No entiendo todavía")
    assert step["needs_assessment"] is True
    assert step["next_step"] == 3
    assert "Revisá" in step["instruction"]
    with pytest.raises(ValueError):
        lesson_plan("suma", "doctorado-falso")
    with pytest.raises(ValueError):
        lesson_step(lesson, 7)


def test_innovation_is_draft_and_has_deliverables():
    project = innovation_project("solución ambiental para reducir residuos", "Hackathon Nicaragua", "municipios")
    assert project["status"] == "draft_requires_validation"
    assert len(project["deliverables"]) >= 10
    assert project["proposal_canvas"]["value_proposition"].startswith("Pendiente")
    assert "sin garantizarlo" in project["competition_result"]
    assert project["source_recommendations"][0]["id"] == "marena"


def test_competition_score_only_with_user_supplied_rubric():
    report = judge_project({"Innovación": 8, "Impacto": 9}, {"Innovación": 40, "Impacto": 60})
    assert report["score_out_of_10"] == 8.6
    assert report["status"] == "user_supplied_scores_not_verified"
    with pytest.raises(ValueError):
        judge_project({"Innovación": 8}, {"Innovación": 70})
    with pytest.raises(ValueError):
        judge_project({"Innovación": 11}, {"Innovación": 100})
    with pytest.raises(ValueError):
        judge_project({"Innovación": True}, {"Innovación": 100})


def test_reference_audit_is_not_remote_fact_check():
    result = verify_references([
        {"title": "Un informe", "author": "Autor", "year": 2025, "url": "https://example.org/report"},
        {"title": "", "author": "", "year": "2025", "url": "http://example.org"}
    ])
    assert result["metadata_complete"] == 1
    assert result["online_verification_performed"] is False
    assert all(not x["existence_verified"] for x in result["references"])
    with pytest.raises(ValueError):
        verify_references([{"title": "x"}] * 51)


def test_no_unauthorized_external_source_or_redirect():
    with pytest.raises(ValueError):
        consult_source("http://127.0.0.1:80/")
    handler = _SafeRedirect()
    class Req:
        def get_method(self):
            return "GET"
        headers = {}
        origin_req_host = "www.mined.gob.ni"
        unverifiable = False
    with pytest.raises(ValueError):
        handler.redirect_request(Req(), None, 302, "redirection", {}, "http://127.0.0.1/private")
    with pytest.raises(ValueError):
        handler.redirect_request(Req(), None, 302, "redirection", {}, "https://evil.example/private")


def test_consult_source_explicit_mocks_network(monkeypatch):
    from email.message import Message
    from io import BytesIO

    class Response:
        def __init__(self):
            self.headers = Message()
            self.headers["Content-Type"] = "text/html; charset=utf-8"
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, n): return b"<html><script>bad</script><body><h1>Informe</h1> texto publico</body></html>"
        def geturl(self): return SOURCES["mined"][3]

    class Opener:
        def open(self, req, timeout): return Response()

    monkeypatch.setattr("neural_core.sky_impacto.request.build_opener", lambda *a: Opener())
    result = consult_source("mined")
    assert result["ok"] is True
    assert "Informe" in result["content"]
    assert "bad" not in result["content"]
    assert result["truncated"] is False


def test_impact_instructions_do_not_claim_verified_sources():
    directive = impact_instructions("General", "quiero participar en Rally con un pitch y modelo canvas")
    assert "primer lugar" in directive
    assert "NO consultadas" in directive
    assert impact_instructions("General", "hola, qué hora es") == ""


def test_api_routes_with_minimal_fastapi():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from metaverse.impacto_api import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.post("/api/impacto/lesson/plan", json={
        "topic": "lectura inicial", "level": "inicial", "minutes": 25
    })
    assert response.status_code == 200
    assert response.json()["result"]["minutes"] == 25
    assert client.get("/api/impacto/sources").status_code == 200
    assert client.post("/api/impacto/sources/bad-host/consult").status_code == 422
    assert client.post("/api/impacto/competition/review", json={
        "scores": {"Impacto": 7}, "rubric": {"Impacto": 100}
    }).json()["result"]["score_out_of_10"] == 7


def test_actual_api_mount_requires_existing_owner_auth():
    # Validación estática adicional del wiring para no requerir todo el stack gráfico en esta suite.
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "metaverse" / "api.py").read_text(encoding="utf-8")
    assert "app.include_router(sky_impacto_router, dependencies=[Depends(require_key)])" in source
