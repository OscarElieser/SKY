"""Regression for SKY Verification Lab; no network, microphone or device actions."""
from __future__ import annotations

import hashlib
import io
import json

import pytest
from fastapi.testclient import TestClient

from neural_core import sky_verification_lab as lab


KEY = "sky-private-owner-test-key-verification-2026"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("SKY_API_KEY", KEY)
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED", "0")
    monkeypatch.setenv("SKY_KNOWLEDGE_DB", str(tmp_path / "private_knowledge.sqlite3"))
    from metaverse.api import app
    with TestClient(app) as cl:
        yield cl


def auth():
    return {"X-SKY-KEY": KEY}


@pytest.mark.parametrize("path", [
    "/api/sky/verification/capabilities",
    "/api/sky/verification/runtime",
    "/api/sky/verification/connectors",
    "/api/sky/verification/authorization",
    "/api/sky/verification/kpis",
])
def test_verification_get_endpoints_require_owner(client, path):
    assert client.get(path).status_code in (401, 403)
    assert client.get(path, headers=auth()).status_code == 200


def test_registry_honest_about_mcp_and_subagents(client):
    response = client.get("/api/sky/verification/capabilities", headers=auth())
    assert response.status_code == 200
    data = response.json()
    assert data["single_existing_api"] is True
    assert data["mcp_general_client_implemented"] is False
    assert data["subagents"]["runs_without_owner_approval"] is False
    assert data["real_windows_hardware_tested_here"] is False


def test_runtime_readiness_does_not_probe_network_by_default(monkeypatch):
    def fail():
        raise AssertionError("network was accessed")
    monkeypatch.setattr(lab, "build_opener", fail)
    result = lab.runtime_readiness()
    assert result["ollama"]["attempted"] is False
    assert result["microphone_recording_tested"] is False
    assert result["agent_authenticated_action_tested"] is False


def test_ollama_probe_blocks_remote_and_unknown_port(monkeypatch):
    monkeypatch.setenv("SKY_OLLAMA_URL", "https://example.org")
    result = lab.runtime_readiness(probe_ollama=True)
    assert result["ollama"]["attempted"] is False
    assert result["ollama"]["status"].startswith("blocked")
    monkeypatch.setenv("SKY_OLLAMA_URL", "http://127.0.0.1:8080")
    assert lab.runtime_readiness(probe_ollama=True)["ollama"]["attempted"] is False


def test_connectors_only_declare_presence_never_echo_secret(client, monkeypatch):
    token = "VERY-PRIVATE-STRING-DO-NOT-ECHO-TO-USERS"
    monkeypatch.setenv("GITHUB_TOKEN", token)
    data = client.get("/api/sky/verification/connectors", headers=auth()).json()
    assert token not in json.dumps(data)
    github = next(x for x in data["connectors"] if x["name"] == "github")
    assert github["credentials_declared"] is True
    assert github["connection_verified"] is False
    assert data["mcp_protocol_active"] is False


def test_text_document_and_sha_provenance(client):
    raw = b"Primera fuente. Un estudio describe un aumento de visitas."
    res = client.post("/api/sky/verification/documents/extract", headers=auth(),
                      files={"file": ("informe.txt", raw, "text/plain")})
    assert res.status_code == 200, res.text
    result = res.json()
    assert result["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["pages"][0]["page"] is None
    assert result["pages"][0]["location"] == "texto_sin_paginacion"
    assert result["claims_verified"] is False
    assert result["no_persistent_copy"] is True


def test_pdf_with_page_number_not_invented(client):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    pdf.drawString(70, 750, "Primera pagina comprobable")
    pdf.showPage()
    pdf.drawString(70, 750, "Segunda pagina comprobable")
    pdf.save()
    res = client.post("/api/sky/verification/documents/extract", headers=auth(),
                      files={"file": ("fuente.pdf", buf.getvalue(), "application/pdf")})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["page_count_extracted"] == 2
    assert [p["page"] for p in data["pages"]] == [1, 2]
    assert "Segunda pagina" in data["pages"][1]["text"]


def test_unsafe_or_oversize_upload_rejected(client):
    result = client.post("/api/sky/verification/documents/extract", headers=auth(),
                         files={"file": ("payload.py", b"print('no')", "text/plain")})
    assert result.status_code == 422
    large = client.post("/api/sky/verification/documents/extract", headers=auth(),
                        files={"file": ("large.txt", b"x" * 5_000_001, "text/plain")})
    assert large.status_code == 413


def test_quote_matching_is_not_fact_verification(client):
    source = b"Una encuesta escolar declarada por el autor contiene 30 encuestados"
    data = lab.extract_document("fuente.txt", source)
    page = data["pages"][0]
    base = {"source_sha256": data["source_sha256"], "page": None,
            "quote": "encuesta escolar declarada por el autor",
            "source_text": page["text"]}
    res = client.post("/api/sky/verification/evidence/crosscheck", headers=auth(), json={
        "claim": "La muestra demuestra que el sistema es efectivo",
        "sources": [base, {**base, "quote": "un resultado inventado"}],
    })
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["located_quotes"] == 1
    assert out["distinct_source_ids_with_quotes"] == 1
    assert out["claim_verified"] is False
    assert out["cross_source_agreement_verified"] is False
    assert out["evidence"][1]["quote"] is None


def test_formative_feedback_no_grade_no_student_data(client):
    answer = "Soy Ana Pérez de la escuela X y mi respuesta es 3."
    res = client.post("/api/sky/verification/education/formative-review",
                      headers=auth(), json={"objective": "Resolver sumas sencillas",
                      "criteria": ["Explica cómo llegó a la respuesta"],
                      "student_response": answer})
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["grade"] is None and not out["correctness_graded"]
    assert not out["student_response_persisted"]
    assert "Ana Pérez" not in json.dumps(out, ensure_ascii=False)
    assert out["teacher_review_required"] is True


def test_kpi_reuses_existing_measurements_without_guessing(monkeypatch):
    from neural_core import sky_metricas
    sample = {"eventos": 0, "acciones": {"total": 0, "tasa_exito": None},
              "voz": {}, "api": {"peticiones": 0}, "modelo": {},
              "servicio": {}, "slo": []}
    monkeypatch.setattr(sky_metricas, "resumen", lambda period: sample)
    result = lab.kpi_snapshot("hoy")
    assert result["sample_event_count"] == 0
    assert result["actions"]["tasa_exito"] is None
    assert result["cost_usd"] is None
    assert result["cost_verified"] is False
    with pytest.raises(ValueError):
        lab.kpi_snapshot("año")


def test_subagent_preview_never_executes_or_grants_new_permissions(client):
    res = client.post("/api/sky/verification/orchestration/preview",
                      headers=auth(), json={"task": "Diseñar una web profesional"})
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["subagents_executed"] == 0
    assert out["actions_executed"] == 0
    assert out["owner_approval_required"] is True


def test_write_endpoints_also_require_owner(client):
    res = client.post("/api/sky/verification/education/formative-review", json={
        "objective": "Resolver sumas sencillas",
        "criteria": ["Explica el resultado"],
        "student_response": "Tres",
    })
    assert res.status_code in (401, 403)
