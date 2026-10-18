"""SKY v9.5: solicitud única -> vista previa -> aprobación -> entregables locales."""
import io
import zipfile
import pytest
from docx import Document
from fastapi.testclient import TestClient

KEY='sky-v95-test-owner-key-that-is-long-enough'
HEAD={'X-SKY-KEY':KEY}

@pytest.fixture
def fx(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_API_KEY',KEY)
    monkeypatch.setenv('SKY_WORKFLOWS_ENABLED','0')
    for key,name in [('SKY_INTELLIGENT_DB','intelligent.sqlite'),('SKY_WORKFLOWS_DB','workflows.sqlite'),
                     ('SKY_PROJECTS_DB','projects.sqlite'),('SKY_WORKBENCH_DB','workbench.sqlite'),
                     ('SKY_METAVERSE_DB','worlds.sqlite'),('SKY_COMMUNITY_DB','community.sqlite'),
                     ('SKY_TELEMETRY_DB','telemetry.sqlite')]:
        monkeypatch.setenv(key,str(tmp_path/name))
    from neural_core import sky_workbench
    monkeypatch.setattr(sky_workbench,'STORE',tmp_path)
    from metaverse.api import app
    with TestClient(app) as client:
        yield client,tmp_path


def request(c,message='SKY, crea mi proyecto completo de academia de turismo con mundo virtual'):
    return c.post('/api/sky/intelligent/message',headers=HEAD,json={'message':message})


def test_private_only_and_minimal_home(fx):
    c,_=fx
    assert c.post('/api/sky/intelligent/message',json={'message':'crea un proyecto completo de educación'}).status_code==401
    assert c.get('/api/sky/intelligent/requests').status_code==401
    assert c.get('/api/sky/intelligent/requests',headers={'Authorization':'Bearer user'}).status_code==401
    html=c.get('/sky').text
    assert 'id="chat-form"' in html
    assert 'BAQUEANO' not in html
    assert 'id="workspace-activity"' in html
    js=c.get('/static/sky-home.js').text
    assert '/api/sky/intelligent/message' in js
    assert 'textContent' in js


def test_draft_without_side_effects_and_explicit_approval(fx):
    c,_=fx
    x=request(c)
    assert x.status_code==200,x.text
    proposal=x.json()['request']
    assert x.json()['type']=='proposal'
    assert proposal['requires_approval'] is True
    assert len(proposal['stages'])==4
    assert proposal['completed_percent']==0
    assert c.get('/api/sky/projects',headers=HEAD).json()==[]
    from neural_core import sky_workflows as wf
    assert wf.run_once() is None
    ident=proposal['id']
    assert c.post(f'/api/sky/intelligent/requests/{ident}/approve',headers=HEAD,json={'approve':False,'expected_fingerprint':proposal['fingerprint']}).status_code==403
    assert c.post(f'/api/sky/intelligent/requests/{ident}/approve',headers=HEAD,json={'approve':True,'expected_fingerprint':'0'*64}).status_code==409
    assert c.get('/api/sky/projects',headers=HEAD).json()==[]


def test_workflow_real_4_stages_and_zip(fx):
    c,_=fx
    original=request(c).json()['request']
    ident=original['id']
    approve=c.post(f'/api/sky/intelligent/requests/{ident}/approve',headers=HEAD,json={'approve':True,'expected_fingerprint':original['fingerprint']})
    assert approve.status_code==200,approve.text
    from neural_core.sky_workflows import run_once
    for index in range(4):
        run_once()
    response=c.get(f'/api/sky/intelligent/requests/{ident}',headers=HEAD)
    result=response.json()
    assert result['status']=='completed',result
    assert result['completed_percent']==100
    assert len(result['deliverables'])==4
    assert {'plan','world','experience','file'}=={d['kind'] for d in result['deliverables']}
    world_id=next(d['world_id'] for d in result['deliverables'] if d['kind']=='world')
    doc=next(d for d in result['deliverables'] if d['kind']=='file')
    r=c.get(doc['download'],headers=HEAD)
    assert r.status_code==200
    text='\n'.join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
    assert world_id in text
    assert 'PROPUESTA INICIAL EDITABLE' in text
    project=c.get('/api/sky/projects/'+result['project_id'],headers=HEAD).json()
    assert len(project['items'])==3
    z=c.get(result['project_export'],headers=HEAD)
    assert z.status_code==200
    with zipfile.ZipFile(io.BytesIO(z.content)) as archive:
        names=archive.namelist()
        assert any(x.endswith('.docx') for x in names)
        assert any(x.endswith('.html') for x in names)
        assert any(x.endswith('.glb') for x in names)
        assert not any('secret' in x or 'conversation' in x for x in names)
    msgs=c.get('/api/sky/intelligent/requests/'+ident+'/conversation',headers=HEAD).json()
    assert len(msgs)==2
    assert c.post(f'/api/sky/intelligent/requests/{ident}/approve',headers=HEAD,json={'approve':True,'expected_fingerprint':original['fingerprint']}).status_code==409
    assert c.get(result['project_export']).status_code==401


def test_continue_existing_project_without_duplicate_project(fx):
    c,_=fx
    old=c.post('/api/sky/projects',headers=HEAD,json={'title':'Museo educativo'}).json()
    prompt='Crea una presentación PowerPoint sobre educación patrimonial'
    r=c.post('/api/sky/intelligent/message',headers=HEAD,json={'message':prompt,'project_id':old['id']})
    assert r.status_code==200,r.text
    ident=r.json()['request']['id']
    approved=c.post(f'/api/sky/intelligent/requests/{ident}/approve',headers=HEAD,json={'approve':True,'expected_fingerprint':r.json()['request']['fingerprint']})
    assert approved.status_code==200,approved.text
    from neural_core.sky_workflows import run_once
    assert run_once()['status']=='scheduled'
    assert run_once()['status']=='completed'
    result=approved.json()
    assert result['project_id']==old['id']
    assert len(c.get('/api/sky/projects',headers=HEAD).json())==1
    final=c.get(f'/api/sky/intelligent/requests/{ident}',headers=HEAD).json()
    file=next(d for d in final['deliverables'] if d['kind']=='file')
    assert c.get(file['download'],headers=HEAD).content[:2]==b'PK'  # PPTX


def test_noncoding_chat_routes_to_assistant(fx):
    c,_=fx
    r=c.post('/api/sky/intelligent/message',headers=HEAD,json={'message':'¿Cuáles son las ventajas de la memoria por proyectos?'})
    assert r.status_code==200,r.text
    assert r.json()['type']=='answer'
    assert r.json()['provider']=='sky-local'
    assert c.get('/api/sky/intelligent/requests',headers=HEAD).json()==[]


def test_invalid_excel_data_and_injection_rejected(fx):
    c,_=fx
    r=request(c,'Crea un Excel de ganancias del próximo año')
    assert r.status_code==422
    assert c.get('/api/sky/intelligent/requests',headers=HEAD).json()==[]
    r=request(c,'Crea mi proyecto completo {{unknown.token}}')
    assert r.status_code==422
    assert c.get('/api/sky/projects',headers=HEAD).json()==[]


def test_status_survives_reopening_and_cannot_double_authorize(fx):
    c,_=fx
    proposal=request(c,'Crea un mundo 3d educativo interactivo para niños').json()['request']
    assert len(proposal['stages'])==2
    from neural_core import sky_intelligent as swi
    reopened=swi.get(proposal['id'])
    assert reopened['id']==proposal['id']
    approved=c.post(f'/api/sky/intelligent/requests/{proposal["id"]}/approve',headers=HEAD,json={'approve':True,'expected_fingerprint':proposal['fingerprint']})
    assert approved.status_code==200
    assert approved.json()['status']=='scheduled'
    recent=c.get('/api/sky/intelligent/requests',headers=HEAD).json()
    assert recent[0]['id']==proposal['id']
    assert c.post(f'/api/sky/intelligent/requests/{proposal["id"]}/approve',headers=HEAD,json={'approve':True,'expected_fingerprint':proposal['fingerprint']}).status_code==409


def test_integration_center_and_backup_contains_intelligent_db(fx):
    c,tmp=fx
    r=request(c,'Crea un diseño web para enseñar astronomía')
    assert r.status_code==200,r.text
    report=c.get('/api/sky/integrations',headers=HEAD).json()
    assert report['platform_version']=='9.7.0'  # Versión real de SKY; contrato del diagnóstico heredado permanece
    assert report['databases']['workspace_inteligente']['state']=='ready'
    from sky_backup import backup
    files=backup(tmp/'private-backup',include_extended=True)
    assert any('workspace_inteligente' in path for path in files)
