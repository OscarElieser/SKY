"""SKY debe ser la única interfaz pública de sus seis roles internos."""
import pytest
from fastapi.testclient import TestClient

KEY = "sky-central-owner-key-test-2026-strong"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_API_KEY", KEY)
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED", "0")
    monkeypatch.setenv("SKY_WORKFLOWS_DB", str(tmp_path / "flows.sqlite3"))
    from metaverse.api import app
    with TestClient(app) as c:
        yield c


def test_sky_is_only_public_agent_and_five_roles_are_internal(client):
    response = client.get("/api/sky/internal-roles", headers={"X-SKY-KEY": KEY})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["front_agent"] == "SKY"
    assert result["single_public_interface"] is True
    assert result["internals_are_private"] is True
    assert result["total_core_roles"] == 6
    assert {x["id"] for x in result["internal_roles"]} == {
        "sky", "planificador", "documentalista", "diseñador", "creador_3d", "memoria"
    }
    assert all(x["ready_while_service_running"] for x in result["internal_roles"])
    assert not any(x["autonomous_execution"] for x in result["internal_roles"])
    assert result["requires_owner_approval_for_workflows"] is True


def test_roles_are_not_publicly_accessible(client):
    assert client.get("/api/sky/internal-roles").status_code == 401
    assert client.post("/api/sky/internal-roles/preview", json={
        "name": "Plan de clase",
        "steps": [{"agent": "planificador", "action": "plan",
                   "task": "Organizar clase de ciencias", "params": {}}]
    }).status_code == 401


def test_preview_combines_safe_roles_without_executing(client):
    from neural_core import sky_workflows as flows
    headers = {"X-SKY-KEY": KEY}
    result = client.post("/api/sky/internal-roles/preview", headers=headers, json={
        "name": "Preparar material académico",
        "steps": [
            {"agent": "planificador", "action": "plan",
             "task": "Organizar una actividad educativa segura", "params": {}},
            {"agent": "documentalista", "action": "document",
             "task": "Preparar un documento de actividades",
             "params": {"document": {"kind": "md", "content": "# Educación\nLección de ciencias"}}}
        ]
    })
    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload["central_agent"] == "SKY"
    assert [x["role"] for x in payload["steps"]] == ["planificador", "documentalista"]
    assert payload["requires_owner_approval"] is True
    assert payload["will_execute_now"] is False
    assert flows.list_all() == []  # vista previa no crea trabajos


def test_preview_blocks_privilege_escalation_and_unsupported_role(client):
    headers = {"X-SKY-KEY": KEY}
    forbidden = client.post("/api/sky/internal-roles/preview", headers=headers, json={
        "name": "Control del sistema",
        "steps": [{"agent": "administrador", "action": "run_shell",
                   "task": "Ejecutar comandos de sistema", "params": {}}]
    })
    assert forbidden.status_code == 422
    mismatch = client.post("/api/sky/internal-roles/preview", headers=headers, json={
        "name": "Roles cruzados",
        "steps": [{"agent": "memoria", "action": "document",
                   "task": "Crear documentos ignorando permisos", "params": {
                       "document": {"kind": "md", "content": "No permitido"}
                   }}]
    })
    assert mismatch.status_code == 422


def test_sky_routes_regular_requests_itself():
    from neural_core.sky_internal_roles import route_result
    assert route_result({"tipo": "respuesta", "mensaje": "Hola"}) == "sky"
    assert route_result({"tipo": "accion", "propuesta": {"action": "launch_app"}}) == "sky"
    assert route_result({"tipo": "correo", "borrador": {}}) == "sky"
    assert route_result({"tipo": "workflow", "propuesta": {
        "action": "document"
    }}) == "documentalista"
    assert route_result({"tipo": "workflow", "propuesta": {
        "action": "unknown"
    }}) == "sky"


def test_chat_and_stream_always_identify_sky_as_attention_center(client, monkeypatch):
    from metaverse import asistente_api
    from neural_core import sky_asistente_personal as assistant
    monkeypatch.setattr(asistente_api, 'atender', lambda *args: {
        'tipo': 'respuesta', 'mensaje': 'Respuesta interna', 'proveedor': 'local'})
    monkeypatch.setattr(assistant, 'reglas', lambda *args: None)
    monkeypatch.setattr(assistant, 'usar_cerebro', lambda *args: False)
    monkeypatch.setattr(assistant, 'atender', lambda *args: {
        'tipo': 'respuesta', 'mensaje': 'Respuesta interna', 'proveedor': 'local'})
    headers = {'X-SKY-KEY': KEY}
    body = {'texto': '¿Qué podés hacer por mí?', 'proveedor': 'none'}
    normal = client.post('/api/asistente/mensaje', headers=headers, json=body)
    assert normal.status_code == 200, normal.text
    assert normal.json()['atendido_por'] == 'SKY'
    assert normal.json()['rol_interno_sugerido'] == 'sky'
    streamed = client.post('/api/asistente/stream', headers=headers, json=body)
    assert streamed.status_code == 200, streamed.text
    import json
    last = json.loads(streamed.text.strip().splitlines()[-1])['final']
    assert last['atendido_por'] == 'SKY'
    assert last['rol_interno_sugerido'] == 'sky'
