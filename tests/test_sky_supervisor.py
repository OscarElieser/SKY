"""E2E de SKY Agent Supervisor con SKY Workflows real y pruebas de seguridad."""
import json
import pytest
from fastapi.testclient import TestClient

KEY = "sky-supervisor-test-key-2026-strong"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_API_KEY", KEY)
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED", "0")
    for key, file in (
        ("SKY_SUPERVISOR_DB", "supervisor.sqlite3"),
        ("SKY_WORKFLOWS_DB", "flows.sqlite3"),
        ("SKY_WORKBENCH_DB", "workbench.sqlite3"),
        ("SKY_PROJECTS_DB", "projects.sqlite3"),
        ("SKY_METAVERSE_DB", "metaverse.sqlite3"),
        ("SKY_COMMUNITY_DB", "community.sqlite3"),
        ("SKY_TELEMETRY_DB", "telemetry.sqlite3"),
    ):
        monkeypatch.setenv(key, str(tmp_path / file))
    from neural_core import sky_workbench
    monkeypatch.setattr(sky_workbench, "STORE", tmp_path)
    from metaverse.api import app
    with TestClient(app) as api:
        yield api


def body(**override):
    value = {"request": "SKY, creá una presentación profesional usando el material de estudio",
             "source_text": "# Introducción\nMaterial de estudio proporcionado para una presentación.",
             "document_format": "auto"}
    value.update(override)
    return value


def test_supervisor_api_requires_owner(client):
    assert client.get("/api/sky/supervisor/catalogue").status_code == 401
    assert client.post("/api/sky/supervisor/prepare", json=body()).status_code == 401
    assert client.get("/api/sky/supervisor/jobs/flow_foo").status_code == 401


def test_auto_plan_routes_to_existing_roles_not_new_privileges(client):
    result = client.post("/api/sky/supervisor/analyze", headers={"X-SKY-KEY": KEY},
                         json=body(request="Creá una presentación y diseñá una interfaz web",
                                   document_format="pptx")).json()
    assert result["central_agent"] == "SKY"
    assert result["assigned_roles"] == ["planificador", "documentalista", "diseñador"]
    assert [s["action"] for s in result["steps"]] == ["plan", "document", "experience"]
    assert result["steps"][1]["params"]["document"]["kind"] == "pptx"
    assert result["ready_to_prepare"]
    assert not result["executes_now"]
    from neural_core import sky_workflows as wf
    assert wf.list_all() == []


def test_no_research_hallucination_or_fake_document(client):
    headers = {"X-SKY-KEY": KEY}
    request = {"request": "Investiga fuentes confiables, redacta un informe y prepara una presentación"}
    preview = client.post("/api/sky/supervisor/analyze", headers=headers, json=request).json()
    assert not preview["ready_to_prepare"]
    assert preview["verified_research_performed"] is False
    assert {x["capability"] for x in preview["blockers"]} == {"research", "document"}
    prepared = client.post("/api/sky/supervisor/prepare", headers=headers, json=request).json()
    assert prepared["status"] == "needs_input"
    assert prepared["workflow_id"] is None
    from neural_core import sky_workflows as wf
    assert wf.list_all() == []


def test_prepare_requires_approval_and_aggregates_actual_outputs(client):
    from neural_core import sky_workflows as wf
    headers = {"X-SKY-KEY": KEY}
    created = client.post("/api/sky/supervisor/prepare", headers=headers,
                          json=body(request="Creá un documento Word con este material",
                                    document_format="md")).json()
    assert created["status"] == "awaiting_approval"
    ident = created["workflow_id"]
    assert created["assigned_roles"] == ["planificador", "documentalista"]
    assert wf.run_once() is None
    waiting = client.get(f"/api/sky/supervisor/jobs/{ident}", headers=headers).json()
    assert waiting["completed_steps"] == 0
    assert waiting["verified_complete"] is False
    assert waiting["awaits_owner_approval"]
    review = client.get(f"/api/sky/workflows/{ident}/preview", headers=headers).json()
    assert review["fingerprint"]
    assert client.post(f"/api/sky/workflows/{ident}/approve", headers=headers,
                       json={"approve": False, "expected_fingerprint": review["fingerprint"]}).status_code == 403
    accepted = client.post(f"/api/sky/workflows/{ident}/approve", headers=headers,
                           json={"approve": True, "expected_fingerprint": review["fingerprint"]})
    assert accepted.status_code == 200, accepted.text
    first = wf.run_once()
    assert first["current_step"] == 1
    partial = client.get(f"/api/sky/supervisor/jobs/{ident}", headers=headers).json()
    assert partial["completed_steps"] == 1
    assert partial["verified_complete"] is False
    completed = wf.run_once()
    assert completed["status"] == "completed", completed
    outcome = client.get(f"/api/sky/supervisor/jobs/{ident}", headers=headers).json()
    assert outcome["verified_complete"]
    assert outcome["completed_steps"] == 2
    assert outcome["percent_complete"] == 100
    assert [x["role"] for x in outcome["results"]] == ["planificador", "documentalista"]
    assert all(x["verified"] for x in outcome["results"])
    doc = outcome["results"][-1]
    assert doc["result"]["kind"] == "file"
    assert doc["result"]["sha256"]
    real_file = client.get(doc["result"]["download"], headers=headers)
    assert real_file.status_code == 200
    assert "Material de estudio" in real_file.text


def test_idempotency_and_nonreplay_after_restart(client):
    headers = {"X-SKY-KEY": KEY}
    req = body(request="Generá un informe con este texto", request_id="same-request-1234")
    first = client.post("/api/sky/supervisor/prepare", headers=headers, json=req)
    second = client.post("/api/sky/supervisor/prepare", headers=headers, json=req)
    assert first.status_code == 201 and second.status_code == 201
    a, b = first.json(), second.json()
    assert a["workflow_id"] == b["workflow_id"]
    assert b["duplicate_prevented"] is True
    from neural_core import sky_workflows as wf
    assert len(wf.list_all()) == 1
    mismatch = client.post("/api/sky/supervisor/prepare", headers=headers,
        json={**req, "request": "Prepará otro documento desde otros datos"})
    assert mismatch.status_code == 409


def test_validation_blockers_and_no_shell(client):
    headers = {"X-SKY-KEY": KEY}
    result = client.post("/api/sky/supervisor/prepare", headers=headers,
        json=body(request="Ejecutá comandos de shell y comprá productos en mi nombre",
                  source_text="")).json()
    assert result["ready_to_prepare"] is False
    assert result["status"] == "needs_input"
    assert result["workflow_id"] is None
    assert any(item["capability"] == "system_external_effects" for item in result["blockers"])
    from neural_core import sky_workflows as wf
    assert wf.list_all() == []
    assert client.post("/api/sky/supervisor/analyze", headers=headers,
                       json=body(document_format="exe")).status_code == 422
    assert client.post("/api/sky/supervisor/prepare", headers=headers,
                       json=body(request_id="../unsafe!!")).status_code == 422


def test_voice_and_chat_route_into_same_supervisor(client):
    headers = {"X-SKY-KEY": KEY}
    payload = {"texto": "SKY, coordiná diseñar una interfaz web educativa",
               "modo": "chat", "proveedor": "none"}
    chat = client.post("/api/asistente/mensaje", headers=headers, json=payload)
    assert chat.status_code == 200, chat.text
    data = chat.json()
    assert data["atendido_por"] == "SKY"
    assert data["proveedor"] == "sky-supervisor"
    assert data["supervisor"]["status"] == "awaiting_approval"
    flow_id = data["supervisor"]["workflow_id"]
    streamed = client.post("/api/asistente/stream", headers=headers, json={
        **payload, "texto": "SKY, coordina diseñar una interfaz visual para un proyecto", "modo": "voz"})
    assert streamed.status_code == 200, streamed.text
    last = json.loads(streamed.text.strip().splitlines()[-1])["final"]
    assert last["atendido_por"] == "SKY"
    assert last["supervisor"]["status"] == "awaiting_approval"
    from neural_core import sky_workflows as wf
    assert wf.get(flow_id)["approved"] is False


def test_status_not_verified_on_failure_or_not_found(client):
    headers = {"X-SKY-KEY": KEY}
    assert client.get("/api/sky/supervisor/jobs/flow_missing", headers=headers).status_code == 404
    plan = client.post("/api/sky/supervisor/prepare", headers=headers,
                       json=body(request="Diseñá una interfaz educativa")).json()
    job = client.get(f"/api/sky/supervisor/jobs/{plan['workflow_id']}", headers=headers).json()
    assert job["verified_complete"] is False
    assert job["status"] == "awaiting_approval"
