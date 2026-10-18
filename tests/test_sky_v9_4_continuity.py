"""Pruebas v9.4: continuidad entre entregables reales, aprobación, pausas, permisos."""
import io, sqlite3, time
import pytest
from fastapi.testclient import TestClient
from docx import Document

KEY='sky-owner-test-key-94-with-adequate-length'
HEAD={'X-SKY-KEY':KEY}

@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_API_KEY',KEY)
    monkeypatch.setenv('SKY_WORKFLOWS_ENABLED','0')
    for key,name in [('SKY_WORKFLOWS_DB','workflow.sqlite'),('SKY_PROJECTS_DB','project.sqlite'),
                     ('SKY_WORKBENCH_DB','workbench.sqlite'),('SKY_METAVERSE_DB','worlds.sqlite'),
                     ('SKY_COMMUNITY_DB','community.sqlite'),('SKY_TELEMETRY_DB','telemetry.sqlite')]:
        monkeypatch.setenv(key,str(tmp_path/name))
    from neural_core import sky_workbench
    monkeypatch.setattr(sky_workbench,'STORE',tmp_path)
    from metaverse.api import app
    with TestClient(app) as client:yield client,tmp_path


def workflow(pid):
    return {'name':'Creación integrada de museo virtual','project_id':pid,'steps':[
        {'agent':'creador_3d','action':'world','task':'Construir mundo educativo inmersivo',
         'params':{'name':'{{project.title}}','prompt':'Museo educativo con salones interactivos'}},
        {'agent':'documentalista','action':'document','task':'Documentar el museo {{step.1.name}}',
         'params':{'document':{'kind':'docx','title':'Guía del museo',
             'content':'# Guía de {{project.title}}\nMundo: {{step.1.name}}\nIdentificador: {{step.1.world_id}}'}}}
    ]}


def test_project_world_and_document_real_continuity(setup):
    c,_=setup
    prj=c.post('/api/sky/projects',headers=HEAD,json={'title':'Museo SKY','description':'Experiencia interactiva'}).json()['id']
    f=c.post('/api/sky/workflows',headers=HEAD,json=workflow(prj))
    assert f.status_code==201,f.text
    fid=f.json()['id']
    preview=c.get('/api/sky/workflows/'+fid+'/preview',headers=HEAD)
    assert preview.status_code==200
    fingerprint=preview.json()['fingerprint']
    assert preview.json()['steps'][1]['references']==['step.1.name','project.title','step.1.name','step.1.world_id']
    assert c.post('/api/sky/workflows/'+fid+'/approve',headers=HEAD,json={'approve':True,'expected_fingerprint':'mismatch'}).status_code==409
    assert c.post('/api/sky/workflows/'+fid+'/approve',headers=HEAD,json={'approve':True,'expected_fingerprint':fingerprint}).status_code==200
    from neural_core.sky_workflows import run_once
    first=run_once();assert first['status']=='scheduled',first
    assert first['results'][0]['result']['kind']=='world'
    world_id=first['results'][0]['result']['world_id']
    paused=c.post('/api/sky/workflows/'+fid+'/pause',headers=HEAD)
    assert paused.status_code==200 and paused.json()['status']=='paused'
    assert run_once() is None
    # Reiniciar la conexión para simular un proceso independiente.
    from neural_core import sky_workflows as wf
    assert wf.get(fid)['status']=='paused'
    assert c.post('/api/sky/workflows/'+fid+'/resume',headers=HEAD).status_code==200
    done=run_once();assert done['status']=='completed',done
    assert len(done['results'])==2
    file_id=done['results'][1]['item_id']
    data=c.get('/api/sky/files/'+file_id,headers=HEAD)
    assert data.status_code==200
    text='\n'.join(x.text for x in Document(io.BytesIO(data.content)).paragraphs)
    assert world_id in text and 'Museo SKY' in text
    report=c.get('/api/sky/projects/'+prj+'/continuity',headers=HEAD)
    assert report.status_code==200,report.text
    r=report.json();assert any(x['kind']=='world' for x in r['deliverables'])
    assert any(x['kind']=='task' for x in r['deliverables'])
    assert r['workflows'][0]['status']=='completed'
    assert c.get('/api/sky/projects/'+prj+'/continuity').status_code==401
    assert c.get('/api/sky/workflows/'+fid+'/preview',headers={'Authorization':'Bearer fake'}).status_code==401


def test_reject_forward_and_unknown_references(setup):
    c,_=setup
    no_project=workflow(None)
    assert c.post('/api/sky/workflows',headers=HEAD,json=no_project).status_code==422
    first=no_project['steps'][0]
    for invalid in ('{{step.2.name}}','{{step.1.secret}}','{{token.private_key}}'):
        copy={'name':'No se debe ejecutar','steps':[
            {'agent':'planificador','action':'plan','task':'Planificar actividad '+invalid,'params':{}}]}
        r=c.post('/api/sky/workflows',headers=HEAD,json=copy)
        assert r.status_code==422,(invalid,r.text)
    prj=c.post('/api/sky/projects',headers=HEAD,json={'title':'Control'}).json()['id']
    good=workflow(prj)
    good['steps'][1]['params']['document']['content']='Contenido: {{step.1.message}}'
    # Campo permitido sintácticamente, pero ausente en respuesta de mundo: falla sin crear documento.
    fid=c.post('/api/sky/workflows',headers=HEAD,json=good).json()['id']
    c.post('/api/sky/workflows/'+fid+'/approve',headers=HEAD,json={'approve':True})
    from neural_core.sky_workflows import run_once
    assert run_once()['current_step']==1
    failed=run_once();assert failed['status']=='failed',failed
    assert len(failed['results'])==1


def test_db_migration_from_v93(setup):
    c,tmp=setup
    from neural_core import sky_workflows as wf
    path=tmp/'workflow.sqlite'
    path.unlink(missing_ok=True)
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE workflows(id TEXT PRIMARY KEY,name TEXT,project_id TEXT,steps TEXT,status TEXT,approved INTEGER,next_run REAL,interval_minutes INTEGER,current_step INTEGER,current_item TEXT,results TEXT,attempt INTEGER,max_attempts INTEGER,run_number INTEGER,lease_until REAL,last_error TEXT,created_at TEXT,updated_at TEXT)')
    with wf.connect() as con:
        cols=[x['name'] for x in con.execute('PRAGMA table_info(workflows)')]
        assert 'pause_requested' in cols and 'project_snapshot' in cols
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_pause_only_between_steps_and_state_unchanged(setup):
    c,_=setup
    data={'name':'Plan simple recurrente','steps':[{'agent':'planificador','action':'plan',
          'task':'Preparar agenda de innovación semanal','params':{}}], 'run_at':'2099-01-01T00:00:00Z'}
    fid=c.post('/api/sky/workflows',headers=HEAD,json=data).json()['id']
    assert c.post('/api/sky/workflows/'+fid+'/pause',headers=HEAD).status_code==409
    assert c.post('/api/sky/workflows/'+fid+'/resume',headers=HEAD).status_code==409
    c.post('/api/sky/workflows/'+fid+'/approve',headers=HEAD,json={'approve':True})
    assert c.post('/api/sky/workflows/'+fid+'/pause',headers=HEAD).status_code==200
    assert c.post('/api/sky/workflows/'+fid+'/pause',headers=HEAD).status_code==409
    assert c.post('/api/sky/workflows/'+fid+'/resume',headers=HEAD).json()['status']=='scheduled'
    assert c.post('/api/sky/workflows/'+fid+'/resume',headers=HEAD).status_code==409
    assert c.post('/api/sky/workflows/'+fid+'/cancel',headers=HEAD).json()['status']=='cancelled'


def test_plan_summary_is_included_in_real_document(setup):
    c,_=setup
    data={'name':'Plan docente y documento integrado','steps':[
      {'agent':'planificador','action':'plan','task':'Diseñar un plan didáctico de innovación y robótica','params':{}},
      {'agent':'documentalista','action':'document','task':'Documentar plan didáctico de innovación',
       'params':{'document':{'kind':'docx','title':'Plan integrado',
                  'content':'# Plan integrado\n{{step.1.plan_summary}}'}}}
    ]}
    ident=c.post('/api/sky/workflows',headers=HEAD,json=data).json()['id']
    c.post('/api/sky/workflows/'+ident+'/approve',headers=HEAD,json={'approve':True})
    from neural_core import sky_workflows as wf
    first=wf.run_once()
    assert first['results'][0]['result']['plan_summary'].startswith('Objetivo:')
    last=wf.run_once()
    file=c.get('/api/sky/files/'+last['results'][1]['item_id'],headers=HEAD)
    assert file.status_code==200
    lines='\n'.join(x.text for x in Document(io.BytesIO(file.content)).paragraphs)
    assert 'Diseñar un plan didáctico' in lines and 'Etapas recomendadas' in lines


def test_approved_project_context_is_frozen_and_auditable(setup):
    c,_=setup
    project=c.post('/api/sky/projects',headers=HEAD,json={'title':'Nombre aprobado',
                'description':'Descripción inicial'}).json()
    pid=project['id']
    data={'name':'Documento con contexto aprobado','project_id':pid,'steps':[
         {'agent':'documentalista','action':'document','task':'Preparar acta {{project.title}}',
          'params':{'document':{'kind':'docx','title':'Acta de proyecto',
                    'content':'Documento aprobado para {{project.title}}.'}}}] }
    create=c.post('/api/sky/workflows',headers=HEAD,json=data).json()
    assert create['project_snapshot']['title']=='Nombre aprobado'
    fid=create['id']
    f=c.get('/api/sky/workflows/'+fid+'/preview',headers=HEAD).json()
    update=c.put('/api/sky/projects/'+pid,headers=HEAD,json={'title':'Nombre actualizado',
                       'description':'Descripción distinta', 'expected_version':project['version']})
    assert update.status_code==200,update.text
    # Approved context remains what the user previewed when creating the workflow.
    ok=c.post('/api/sky/workflows/'+fid+'/approve',headers=HEAD,json={'approve':True,
           'expected_fingerprint':f['fingerprint']})
    assert ok.status_code==200,ok.text
    from neural_core import sky_workflows as wf
    finished=wf.run_once()
    downloaded=c.get('/api/sky/files/'+finished['results'][0]['item_id'],headers=HEAD)
    words='\n'.join(x.text for x in Document(io.BytesIO(downloaded.content)).paragraphs)
    assert 'Nombre aprobado' in words and 'Nombre actualizado' not in words
