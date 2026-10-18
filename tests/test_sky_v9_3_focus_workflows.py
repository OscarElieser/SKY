"""Regresión real SKY v9.3: roles, minimal UI, persistence, restart, workflow."""
import json,io,zipfile,time
import pytest
from fastapi.testclient import TestClient

KEY='sky-master-key-for-authorized-owner-tests-2026'
HEADERS={'X-SKY-KEY':KEY}

@pytest.fixture
def fx(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_API_KEY',KEY)
    monkeypatch.setenv('SKY_WORKFLOWS_ENABLED','0') # Deterministic worker execution
    for k,name in [('SKY_WORKFLOWS_DB','workflows.db'),('SKY_METAVERSE_DB','worlds.db'),
                   ('SKY_COMMUNITY_DB','users.db'),('SKY_PROJECTS_DB','projects.db'),
                   ('SKY_WORKBENCH_DB','workbench.db'),('SKY_TELEMETRY_DB','telemetry.db')]:
        monkeypatch.setenv(k,str(tmp_path/name))
    from neural_core import sky_workbench
    monkeypatch.setattr(sky_workbench,'STORE',tmp_path)
    from metaverse.api import app
    with TestClient(app) as client:
        yield client,tmp_path


def payload(**kw):
    p={'name':'Plan semanal de actividades SKY','steps':[
        {'agent':'planificador','action':'plan','task':'Preparar un plan completo para una clase de innovación','params':{}},
        {'agent':'documentalista','action':'document','task':'Crear documento de actividades para una clase tecnológica','params':{'document':{'kind':'docx','title':'Clase de innovación','content':'# Sesión de aprendizaje\nPensamiento creativo aplicado a prototipos.'}}},
    ]}
    p.update(kw);return p


def test_minimal_home_and_owner_only_navigation(fx):
    c,_=fx
    html=c.get('/').text
    assert c.get('/').status_code==200
    assert 'SKY' in html and 'id="chat-form"' in html
    assert 'BAQUEANO' not in html
    assert 'BAQUEANO' not in c.get('/static/sky-home.js').text or 'mode===\'owner\'' in c.get('/static/sky-home.js').text
    assert c.get('/world').status_code==200
    assert c.get('/studio').status_code==200
    assert c.get('/flows').status_code==200
    assert c.get('/api/sky/owner/baqueano').status_code==401
    assert c.get('/api/sky/owner/baqueano',headers={'Authorization':'Bearer normal-token'}).status_code==401
    assert c.get('/api/sky/owner/baqueano',headers=HEADERS).json()['visibility']=='creator_only'
    assert c.get('/api/sky/workflows',headers={'Authorization':'Bearer normal-token'}).status_code==401


def test_workflow_requires_approval_and_executes_real_artifact(fx):
    c,tmp=fx
    r=c.post('/api/sky/workflows',headers=HEADERS,json=payload())
    assert r.status_code==201,r.text
    f=r.json();fid=f['id'];assert f['status']=='awaiting_approval'
    from neural_core.sky_workflows import run_once,get
    assert run_once() is None
    assert c.post(f'/api/sky/workflows/{fid}/approve',headers=HEADERS,json={'approve':False}).status_code==403
    assert c.post(f'/api/sky/workflows/{fid}/approve',headers=HEADERS,json={'approve':True}).status_code==200
    assert run_once()['status']=='scheduled'
    done=run_once()
    assert done['status']=='completed',done
    assert len(done['results'])==2
    doc=done['results'][1]
    assert doc['result']['kind']=='file'
    r=c.get('/api/sky/files/'+doc['item_id'],headers=HEADERS)
    assert r.status_code==200
    from docx import Document
    assert 'Sesión de aprendizaje' in '\n'.join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
    assert run_once() is None
    assert c.post(f'/api/sky/workflows/{fid}/approve',headers=HEADERS,json={'approve':True}).status_code==409
    assert len(c.get(f'/api/sky/workflows/{fid}/events',headers=HEADERS).json())>=4


def test_workflow_is_persistent_and_due_later(fx):
    c,tmp=fx
    from neural_core import sky_workflows as wf
    delayed='2099-01-01T09:00:00+00:00'
    f=c.post('/api/sky/workflows',headers=HEADERS,json=payload(run_at=delayed)).json()
    c.post(f'/api/sky/workflows/{f["id"]}/approve',headers=HEADERS,json={'approve':True})
    assert wf.run_once() is None
    assert wf.get(f['id'])['next_run_at'].startswith('2099-01-01')
    assert len(wf.list_all())==1
    # Recreating DB connection simulates process restart (no in-memory scheduler state).
    with wf.connect() as db:
        db.execute('UPDATE workflows SET next_run=? WHERE id=?',(time.time()-1,f['id']))
    assert wf.run_once()['current_step']==1
    assert wf.get(f['id'])['status']=='scheduled'


def test_workflow_recurrence_and_cancellation(fx):
    c,tmp=fx
    from neural_core import sky_workflows as wf
    data={'name':'Repaso diario local','steps':[{'agent':'planificador','action':'plan','task':'Preparar plan de estudio de seguridad y redes','params':{}}],
          'interval_minutes':30}
    r=c.post('/api/sky/workflows',headers=HEADERS,json=data);assert r.status_code==201,r.text
    fid=r.json()['id']
    c.post(f'/api/sky/workflows/{fid}/approve',headers=HEADERS,json={'approve':True})
    out=wf.run_once();assert out['status']=='scheduled' and out['run_number']==2
    assert len(out['results'])==1
    assert wf.run_once() is None
    assert c.post(f'/api/sky/workflows/{fid}/cancel',headers=HEADERS).json()['status']=='cancelled'
    assert wf.run_once() is None


def test_workflow_invalid_and_project_link(fx):
    c,tmp=fx
    prj=c.post('/api/sky/projects',headers=HEADERS,json={'title':'Proyecto SKY v9.3'}).json()['id']
    world={'name':'Mundo creativo STEM','project_id':prj,'steps':[{'agent':'creador_3d','action':'world',
           'task':'Crear mundo futurista para enseñar programación','params':{'name':'Ciudad STEAM','prompt':'ciudad futurista con plazas y aulas'}}]}
    f=c.post('/api/sky/workflows',headers=HEADERS,json=world);assert f.status_code==201,f.text
    fid=f.json()['id']
    c.post(f'/api/sky/workflows/{fid}/approve',headers=HEADERS,json={'approve':True})
    from neural_core.sky_workflows import run_once
    result=run_once();assert result['status']=='completed',result
    pid=c.get('/api/sky/projects/'+prj,headers=HEADERS).json()
    assert any(e['kind']=='world' for e in pid['items'])
    bad=payload(steps=[{'agent':'planificador','action':'world','task':'Hacer una acción que no coincide','params':{}}])
    assert c.post('/api/sky/workflows',headers=HEADERS,json=bad).status_code==422
    bad=payload(steps=[{'agent':'documentalista','action':'document','task':'Escribirme algo sin contenido real','params':{}}])
    assert c.post('/api/sky/workflows',headers=HEADERS,json=bad).status_code==422


def test_review_on_ambiguous_side_effect(fx):
    c,_=fx
    from neural_core import sky_workflows as wf
    f=c.post('/api/sky/workflows',headers=HEADERS,json={'name':'Mundo protegido','steps':[
        {'agent':'creador_3d','action':'world','task':'Construir una ciudad interactiva con recorridos','params':{'prompt':'ciudad interactiva'}}]}).json()
    fid=f['id'];wf.approve(fid)
    from neural_core.sky_workbench import create_item
    wi=create_item('Construir una ciudad interactiva con recorridos','world',{'prompt':'ciudad interactiva'})
    with wf.connect() as db:
        db.execute('UPDATE workflows SET status=?,current_item=?,lease_until=? WHERE id=?',('running',wi['id'],time.time()-3,fid))
    # After crash, worker continues using same record, no duplicate work item.
    out=wf.run_once()
    assert out['status']=='completed',out
    # A work item reported as executing after crash is deliberately not replayed.
    g=c.post('/api/sky/workflows',headers=HEADERS,json={'name':'Segundo mundo protegido','steps':[
        {'agent':'creador_3d','action':'world','task':'Construir plaza principal con usuarios','params':{'prompt':'plaza'}}]}).json()
    wf.approve(g['id'])
    wi2=create_item('Construir plaza principal con usuarios','world',{'prompt':'plaza'})
    from neural_core import sky_workbench as wb
    with wb._conn() as db:db.execute("UPDATE work_items SET status='ejecutando' WHERE id=?",(wi2['id'],))
    with wf.connect() as db:db.execute('UPDATE workflows SET status=?,current_item=?,lease_until=? WHERE id=?',('running',wi2['id'],time.time()-3,g['id']))
    out=wf.run_once()
    assert out['status']=='needs_review'
    assert c.post('/api/sky/workflows/'+g['id']+'/retry',headers=HEADERS,json={}).status_code==403
    assert c.post('/api/sky/workflows/'+g['id']+'/retry',headers=HEADERS,json={'acknowledge_partial_effects':True}).status_code==200


def test_no_unauthorized_community_access_even_if_logged_in(fx):
    c,_=fx
    invite=c.post('/api/community/admin/invites',headers=HEADERS,json={'hours':48}).json()['invite_code']
    reg=c.post('/api/community/register',json={'username':'testvisitor93','password':'a-strong-password-12345','display_name':'Visitante','invite':invite})
    assert reg.status_code==201,reg.text
    login=c.post('/api/community/login',json={'username':'testvisitor93','password':'a-strong-password-12345'}).json()
    h={'Authorization':'Bearer '+login['access_token']}
    assert c.get('/api/community/me',headers=h).status_code==200
    assert c.get('/api/sky/owner/baqueano',headers=h).status_code==401
    assert c.get('/api/sky/workflows/status',headers=h).status_code==401
    assert c.get('/api/sky/projects',headers=h).status_code==401
    assert c.post('/api/community/me/ask',headers=h,json={'message':'hola sky, me ayudas con mis metas?','provider':'local'}).status_code==200


def test_backup_preserves_workflows_and_projects(fx,tmp_path):
    c,_=fx
    p=c.post('/api/sky/projects',headers=HEADERS,json={'title':'Aprendizaje continuo'}).json()['id']
    flow=c.post('/api/sky/workflows',headers=HEADERS,json=payload(project_id=p)).json()
    from sky_backup import backup
    files=backup(tmp_path/'backups',include_extended=True)
    assert any('proyectos' in v for v in files)
    assert any('flujos' in v for v in files)
    import sqlite3
    db=next(v for v in files if 'flujos' in v)
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT count(*) FROM workflows').fetchone()[0]==1
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_retry_limited_to_safe_plan_and_recurrence_limit(fx,monkeypatch):
    c,_=fx
    from neural_core import sky_workflows as wf
    world={'name':'Mundo recurrente','interval_minutes':1,'steps':[
        {'agent':'creador_3d','action':'world','task':'Crear un mundo muy amplio de estudio','params':{'prompt':'bosque'}}]}
    assert c.post('/api/sky/workflows',headers=HEADERS,json=world).status_code==422
    data={'name':'Plan resiliente','steps':[{'agent':'planificador','action':'plan','task':'Organizar una revisión semanal de proyectos','params':{}}]}
    created=c.post('/api/sky/workflows',headers=HEADERS,json=data).json();wf.approve(created['id'])
    original=wf.execute_item;counter={'attempts':0}
    def transient(*args,**kwargs):
        if counter['attempts']==0:
            counter['attempts']+=1
            raise TimeoutError('Error transitorio de prueba antes de ejecutar')
        return original(*args,**kwargs)
    monkeypatch.setattr(wf,'execute_item',transient)
    first=wf.run_once();assert first['status']=='retry_wait',first
    with wf.connect() as db:db.execute('UPDATE workflows SET next_run=? WHERE id=?',(time.time()-1,created['id']))
    second=wf.run_once()
    assert second['status']=='completed',second
    assert len(second['results'])==1
