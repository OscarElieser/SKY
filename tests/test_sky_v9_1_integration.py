"""SKY 9.1: Integration Center security, diagnostics and cross-module contract."""
from io import BytesIO
import pytest
from fastapi.testclient import TestClient

KEY = 'integration-test-key-must-be-long-enough-123456789'

@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv('SKY_API_KEY', KEY)
    for key, name in (
        ('SKY_METAVERSE_DB','worlds.sqlite3'),
        ('SKY_COMMUNITY_DB','community.sqlite3'),
        ('SKY_WORKBENCH_DB','workbench.sqlite3'),
        ('SKY_TELEMETRY_DB','telemetry.sqlite3')):
        monkeypatch.setenv(key, str(tmp_path / name))
    import neural_core.sky_workbench as wb
    monkeypatch.setattr(wb, 'STORE', tmp_path)
    from metaverse.api import app
    with TestClient(app) as client:
        yield client, tmp_path


def auth():
    return {'X-SKY-KEY': KEY}


def test_integration_center_auth_and_readonly(app_client):
    client, tmp_path = app_client
    assert client.get('/api/sky/integrations').status_code == 401
    report = client.get('/api/sky/integrations', headers=auth())
    assert report.status_code == 200
    data = report.json()
    assert data['version'] == '9.2.0'
    assert data['core_operational'] is True
    assert data['libraries']['api']['state'] == 'ready'
    assert data['databases']['metaverso']['state'] == 'ready'
    assert data['databases']['proyectos_y_memoria']['state'] == 'not_initialized'
    assert data['external_providers'] == 'not_checked'
    assert not (tmp_path/'workbench.sqlite3').exists(), 'Readiness never creates workbench DB'


def test_integration_detects_invalid_sqlite(app_client):
    client, root = app_client
    (root/'workbench.sqlite3').write_bytes(b'INVALID SQLITE BYTES')
    response = client.get('/api/sky/integrations', headers=auth()).json()
    assert response['core_operational'] is False
    assert response['state'] == 'attention_required'
    assert response['databases']['proyectos_y_memoria']['state'] == 'error'


def test_full_workflow_memory_world_design_and_powerpoint(app_client):
    client, root = app_client
    def job(task, action, params):
        response=client.post('/api/sky/tasks',headers=auth(),json={
            'task':task, 'action':action, 'params':params})
        assert response.status_code==201,response.text
        ident=response.json()['id']
        executed=client.post(f'/api/sky/tasks/{ident}/execute',headers=auth(),json={'approve':True})
        assert executed.status_code==200,executed.text
        return executed.json()

    memory=job('Guardar mi estilo personal para diseños', 'memory',
               {'label':'Estilo', 'content':'Azul cian y estilo futurista'} )
    world=job('Construir un espacio digital para una clase', 'world',
              {'name':'Aula virtual', 'prompt':'aula con jardines y edificios'})
    design=job('Diseñar un portal educativo inmersivo', 'experience',
               {'title':'SKY Academia','template':'classroom','palette':'sky'})
    slides=job('Crear la presentación para una clase digital', 'document',
               {'document':{'kind':'pptx','title':'Academia SKY','content':'# Temario\nEducación inmersiva\n# Propuesta\nEntornos 3D'}})
    assert memory['output']['kind']=='memory'
    assert client.get('/api/worlds/'+world['output']['world_id'],headers=auth()).status_code==200
    assert client.get('/api/sky/experiences/'+design['id'],headers=auth()).json()['title']=='SKY Academia'
    pdf_or_pptx=client.get('/api/sky/files/'+slides['id'],headers=auth())
    from pptx import Presentation
    assert len(Presentation(BytesIO(pdf_or_pptx.content)).slides)>0
    report=client.get('/api/sky/integrations',headers=auth()).json()
    assert report['databases']['proyectos_y_memoria']['state']=='ready'
    assert report['core_operational'] is True
    assert len(client.get('/api/sky/memory',headers=auth()).json())==1


def test_studio_ui_wires_integration_and_prevents_stale_preview(app_client):
    client,_=app_client
    page=client.get('/studio').text
    js=client.get('/static/studio.js').text
    assert 'id="check-integrations"' in page
    assert 'id="integration-summary"' in page
    assert 'previewSignature===designSignature()' in js
    assert "getActionParams(action)" in js
    assert "addEventListener('input',resetPreview)" in js
    assert "'/api/sky/integrations'" in js
