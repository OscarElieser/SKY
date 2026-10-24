"""Regresión SKY Subagent Manager: seguridad, persistencia y delegación supervisada."""
import pytest
from fastapi.testclient import TestClient

KEY = 'sky-subagent-owner-test-key-2026-strong'
HEADERS = {'X-SKY-KEY': KEY}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('SKY_API_KEY', KEY)
    monkeypatch.setenv('SKY_WORKFLOWS_ENABLED', '0')
    monkeypatch.setenv('SKY_SUBAGENTS_DB', str(tmp_path / 'subagents.sqlite3'))
    monkeypatch.setenv('SKY_WORKFLOWS_DB', str(tmp_path / 'workflows.sqlite3'))
    monkeypatch.setenv('SKY_WORKBENCH_DB', str(tmp_path / 'workbench.sqlite3'))
    from metaverse.api import app
    with TestClient(app) as api:
        yield api


def create(client, name='Investigador académico', mission='Organizar una investigación comprobable',
           role='planificador'):
    return client.post('/api/sky/subagents', headers=HEADERS,
                       json={'name': name, 'mission': mission, 'role': role})


def test_owner_is_required_on_all_subagent_operations(client):
    assert client.get('/api/sky/subagents').status_code == 401
    assert client.get('/api/sky/subagents/catalogue').status_code == 401
    assert client.post('/api/sky/subagents', json={'name': 'Analista', 'mission': 'Analizar proyectos', 'role': 'planificador'}).status_code == 401
    assert client.get('/api/sky/subagents/sub_' + 'a' * 24).status_code == 401


def test_create_enable_delegate_and_approve_with_existing_workflows(client):
    from neural_core import sky_workflows as wf
    response = create(client)
    assert response.status_code == 201, response.text
    agent = response.json()
    assert agent['enabled'] is False
    assert agent['action'] == 'plan'
    assert agent['can_create_subagents'] is False
    assert agent['requires_workflow_approval'] is True
    agent_id = agent['id']

    pending = client.post(f'/api/sky/subagents/{agent_id}/delegate', headers=HEADERS,
                          json={'task': 'Organizar plan para un curso técnico', 'params': {}})
    assert pending.status_code == 403
    assert client.post(f'/api/sky/subagents/{agent_id}/enable', headers=HEADERS).json()['enabled']
    created = client.post(f'/api/sky/subagents/{agent_id}/delegate', headers=HEADERS,
                          json={'task': 'Organizar plan para un curso técnico', 'params': {}})
    assert created.status_code == 201, created.text
    data = created.json()
    flow = wf.get(data['workflow_id'])
    assert flow['status'] == 'awaiting_approval' and flow['approved'] is False
    assert flow['steps'][0]['agent'] == 'planificador'
    assert flow['steps'][0]['action'] == 'plan'
    assert wf.run_once() is None
    assert client.get('/api/sky/subagents', headers=HEADERS).json()[0]['id'] == agent_id
    hist = client.get(f'/api/sky/subagents/{agent_id}/delegations', headers=HEADERS).json()
    assert hist[0]['workflow_id'] == data['workflow_id']
    # Activar y delegar no sustituye la aprobación explícita del flujo.
    assert client.post(f'/api/sky/workflows/{flow["id"]}/approve', headers=HEADERS,
                       json={'approve': False}).status_code == 403


def test_custom_name_never_grants_privileges_or_arbitrary_role(client):
    catalog = client.get('/api/sky/subagents/catalogue', headers=HEADERS).json()
    assert len(catalog['roles']) == 5
    assert not catalog['runs_without_owner_approval']
    assert not catalog['can_create_subagents_recursively']
    assert create(client, role='admin').status_code == 422
    assert create(client, role='shell').status_code == 422

    agent = create(client, name='Superadministrador de SKY').json()
    assert agent['action'] == 'plan'
    client.post(f'/api/sky/subagents/{agent["id"]}/enable', headers=HEADERS)
    denied = client.post(f'/api/sky/subagents/{agent["id"]}/delegate', headers=HEADERS,
                         json={'task': 'Ejecutar comandos en Windows y cambiar permisos',
                               'params': {'action': 'run_shell'}})
    # El parámetro no cambia el tipo de ejecutor: sigue siendo un plan, NO shell.
    if denied.status_code == 201:
        from neural_core import sky_workflows as wf
        step = wf.get(denied.json()['workflow_id'])['steps'][0]
        assert step['action'] == 'plan' and step['agent'] == 'planificador'


def test_document_agent_cannot_execute_without_real_content(client):
    agent = create(client, role='documentalista').json()
    client.post(f'/api/sky/subagents/{agent["id"]}/enable', headers=HEADERS)
    response = client.post(f'/api/sky/subagents/{agent["id"]}/delegate', headers=HEADERS,
                           json={'task': 'Crear informe real del curso', 'params': {}})
    assert response.status_code == 422


def test_disable_blocks_new_delegations_without_silently_mutating_old_flows(client):
    from neural_core import sky_workflows as wf
    agent = create(client).json()
    agent_id = agent['id']
    client.post(f'/api/sky/subagents/{agent_id}/enable', headers=HEADERS)
    created = client.post(f'/api/sky/subagents/{agent_id}/delegate', headers=HEADERS,
                          json={'task': 'Planificar actividades educativas', 'params': {}}).json()
    disabled = client.post(f'/api/sky/subagents/{agent_id}/disable', headers=HEADERS).json()
    assert disabled['enabled'] is False
    assert 'cancel' in disabled['notice'].lower()
    assert client.post(f'/api/sky/subagents/{agent_id}/delegate', headers=HEADERS,
                       json={'task': 'Nueva orden desde agente deshabilitado', 'params': {}}).status_code == 403
    # El flujo ya creado queda pendiente de aprobación y visible para cancelación.
    assert wf.get(created['workflow_id'])['status'] == 'awaiting_approval'


def test_subagents_survive_reopening_database(client):
    from neural_core import sky_subagents as sub
    first = create(client).json()
    with sub.connect() as connection:
        row = connection.execute('SELECT name, enabled FROM sky_subagents WHERE id=?',
                                 (first['id'],)).fetchone()
    assert row['name'] == first['name'] and row['enabled'] == 0
    assert sub.get(first['id'])['mission'] == first['mission']


def test_limit_pending_delegations(client):
    agent = create(client).json()
    client.post(f'/api/sky/subagents/{agent["id"]}/enable', headers=HEADERS)
    url = f'/api/sky/subagents/{agent["id"]}/delegate'
    for i in range(5):
        response = client.post(url, headers=HEADERS, json={'task': f'Planificar el módulo educativo {i + 1}', 'params': {}})
        assert response.status_code == 201, response.text
    assert client.post(url, headers=HEADERS,
                       json={'task': 'Planificar una sexta tarea adicional', 'params': {}}).status_code == 403
