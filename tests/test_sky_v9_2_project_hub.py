"""Comprobaciones de regresión, privacidad e integración de proyectos SKY 9.2."""
import io,json,zipfile,os
import pytest
from fastapi.testclient import TestClient

KEY='a-private-project-master-key-long-enough-for-tests-2026'

@pytest.fixture
def cli(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_API_KEY',KEY)
    for k,name in [('SKY_METAVERSE_DB','worlds.db'),('SKY_COMMUNITY_DB','community.db'),
                   ('SKY_WORKBENCH_DB','workbench.db'),('SKY_TELEMETRY_DB','metrics.db'),
                   ('SKY_PROJECTS_DB','projects.db')]:
        monkeypatch.setenv(k,str(tmp_path/name))
    from neural_core import sky_workbench
    monkeypatch.setattr(sky_workbench,'STORE',tmp_path)
    from metaverse.api import app
    with TestClient(app) as client:yield client,tmp_path

def headers():return {'X-SKY-KEY':KEY}

def project(client,title='Academia SKY'):
    res=client.post('/api/sky/projects',headers=headers(),json={'title':title,'description':'Aprender y crear una academia en el metaverso'})
    assert res.status_code==201,res.text
    return res.json()['id']

def task(client,pid,action,body):
    res=client.post(f'/api/sky/projects/{pid}/tasks',headers=headers(),json={
        'task':'Proyecto de experiencia educativa inmersiva', 'action':action,'params':body})
    assert res.status_code==201,res.text
    ident=res.json()['id']
    executed=client.post('/api/sky/tasks/'+ident+'/execute',headers=headers(),json={'approve':True})
    assert executed.status_code==200,executed.text
    return executed.json()

def test_auth_all_read_write_and_export(cli):
    c,_=cli
    for url in ('/api/sky/projects','/api/sky/projects/nonexistent','/api/sky/projects/nonexistent/messages','/api/sky/projects/nonexistent/export.zip'):
        assert c.get(url).status_code==401
    assert c.post('/api/sky/projects',json={'title':'Sin clave'}).status_code==401

def test_project_version_conflict_and_validation(cli):
    c,_=cli;pid=project(c)
    before=c.get(f'/api/sky/projects/{pid}',headers=headers()).json()['project']
    update={'title':'Sky Academia II','description':'Nuevo objetivo','expected_version':before['version']}
    assert c.put(f'/api/sky/projects/{pid}',headers=headers(),json=update).status_code==200
    assert c.put(f'/api/sky/projects/{pid}',headers=headers(),json=update).status_code==409
    assert c.post('/api/sky/projects',headers=headers(),json={'title':''}).status_code==422

def test_persisted_notes_messages_and_forgetting(cli):
    c,_=cli;pid=project(c)
    note=c.post(f'/api/sky/projects/{pid}/notes',headers=headers(),json={'title':'Paleta','content':'Cian y violeta'}).json()
    assist=c.post('/api/sky/assist',headers=headers(),json={'message':'Enseñame los pasos para un mundo educativo',
        'provider':'local','project_id':pid,'share_project_context':True,'save_to_project':True})
    assert assist.status_code==200,assist.text
    assert 'Academia SKY' in assist.json()['answer']
    msgs=c.get(f'/api/sky/projects/{pid}/messages',headers=headers()).json()
    assert len(msgs)==2 and msgs[0]['role']=='user' and msgs[1]['role']=='assistant'
    assert len(c.get(f'/api/sky/projects/{pid}/notes',headers=headers()).json())==1
    data=c.get(f'/api/sky/projects/{pid}/export.zip',headers=headers()).content
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert 'proyecto.json' in z.namelist()
        content=z.read('proyecto.json').decode()
        assert 'Cian y violeta' not in content and msgs[0]['content'] not in content
    assert c.delete(f'/api/sky/projects/{pid}/notes/{note["id"]}',headers=headers()).status_code==200
    assert c.delete(f'/api/sky/projects/{pid}/messages',headers=headers()).json()['removed']==2
    assert not c.get(f'/api/sky/projects/{pid}/messages',headers=headers()).json()

def test_cross_project_scoping(cli):
    c,_=cli;a=project(c,'Proyecto Uno');b=project(c,'Proyecto Dos')
    item=task(c,a,'memory',{'label':'Nota','content':'Solo en proyecto uno'})
    pa=c.get(f'/api/sky/projects/{a}',headers=headers()).json()
    pb=c.get(f'/api/sky/projects/{b}',headers=headers()).json()
    assert len(pa['items'])==1 and len(pb['items'])==0
    assert c.delete(f'/api/sky/projects/{b}/links/{pa["items"][0]["id"]}',headers=headers()).status_code==404
    assert c.post('/api/sky/assist',headers=headers(),json={'message':'Hola SKY','provider':'local','project_id':'absent'}).status_code==404

def test_full_project_document_world_design_export(cli):
    c,tmp=cli;pid=project(c,'Laboratorio SKY')
    doc=task(c,pid,'document',{'document':{'kind':'docx','title':'Guía para SKY','content':'# Experiencias\nEducación inmersiva y proyectos reales.'}})
    world=task(c,pid,'world',{'name':'Ciudad STEAM','prompt':'aula de realidad virtual futurista'})
    design=task(c,pid,'experience',{'title':'Academia Futurista','template':'classroom','palette':'sky'})
    item=c.get(f'/api/sky/projects/{pid}',headers=headers()).json()
    assert len(item['items'])==3
    assert sorted(x.get('output_kind') for x in item['items'])==['experience','file','world']
    data=c.get(f'/api/sky/projects/{pid}/export.zip',headers=headers()).content
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist();assert len(names)>=6
        assert any(n.endswith('.docx') for n in names)
        assert any(n.endswith('world.json') for n in names)
        assert any(n.endswith('world.glb') for n in names)
        assert any(n.endswith('experience.html') for n in names)
        assert any(n.endswith('experience_spec.json') for n in names)
        from docx import Document
        body=next(z.read(n) for n in names if n.endswith('.docx'))
        assert 'Experiencias' in '\n'.join(x.text for x in Document(io.BytesIO(body)).paragraphs)
        j=json.loads(z.read('proyecto.json'))
        assert len(j['items'])==3
        assert len(z.read('proyecto.json'))>200
    assert c.get('/api/worlds/'+world['output']['world_id'],headers=headers()).status_code==200
    assert c.get('/api/sky/experiences/'+design['id'],headers=headers()).status_code==200

def test_link_missing_resources_and_duplicate(cli):
    c,_=cli;pid=project(c)
    body={'kind':'world','ref':'not_real','label':'Mundo inexistente'}
    assert c.post(f'/api/sky/projects/{pid}/links',headers=headers(),json=body).status_code==404
    world=task(c,pid,'world',{'name':'Bosque','prompt':'bosque digital'})
    ident=world['output']['world_id'];body.update({'ref':ident,'label':'Bosque compartido'})
    assert c.post(f'/api/sky/projects/{pid}/links',headers=headers(),json=body).status_code==201
    assert c.post(f'/api/sky/projects/{pid}/links',headers=headers(),json=body).status_code==201
    assert len(c.get(f'/api/sky/projects/{pid}',headers=headers()).json()['items'])==2

def test_user_has_opt_in_to_send_project_context(cli,monkeypatch):
    c,_=cli;pid=project(c)
    captured=[]
    def fake_reply(messages,provider):captured.append(messages);return 'Respuesta de prueba'
    import neural_core.providers as providers
    monkeypatch.setattr(providers,'reply',fake_reply)
    base={'message':'Necesito actividades para mi clase','provider':'gemini','project_id':pid}
    r=c.post('/api/sky/assist',headers=headers(),json=base)
    assert r.status_code==200
    assert 'Academia SKY' not in json.dumps(captured[-1])
    r=c.post('/api/sky/assist',headers=headers(),json={**base,'share_project_context':True,'save_to_project':True})
    assert r.status_code==200
    assert 'Academia SKY' in json.dumps(captured[-1])
    assert len(c.get(f'/api/sky/projects/{pid}/messages',headers=headers()).json())==2
    r=c.post('/api/sky/assist',headers=headers(),json={**base,'share_project_history':True})
    assert r.status_code==200
    assert len(captured[-1])>=4
    assert 'Academia SKY' not in captured[-1][0]['content']

def test_project_ui_and_legacy_routes(cli):
    c,_=cli
    html=c.get('/studio').text;js=c.get('/static/studio.js').text
    for token in ('SKY Project Hub','id="project-select"','id="create-project"','id="export-project"','id="project-chat-history"','id="link-project-item"'):
        assert token in html
    for token in ('loadProjects()','loadProjectMessages()','share_project_context','/api/sky/projects/'):
        assert token in js
    assert c.get('/api/sky/actions',headers=headers()).status_code==200
    assert c.get('/api/sky/integrations',headers=headers()).status_code==200

def test_no_implicit_project_export_secrets(cli):
    c,_=cli;pid=project(c)
    from neural_core import sky_projects as prj
    file,name=prj.export_zip(pid)
    assert zipfile.is_zipfile(io.BytesIO(file))
    assert b'SKY_API_KEY' not in file and b'gemini-key' not in file


def test_project_db_integration_check_is_readonly(cli):
    c,tmp=cli
    # Primera petición de diagnóstico no debería crear una DB vacía.
    info=c.get('/api/sky/integrations',headers=headers()).json()
    assert info['version']=='9.2.0'
    assert info['databases']['proyectos_compartidos_entre_modulos']['state']=='not_initialized'
    assert not (tmp/'projects.db').exists()
    project(c)
    info=c.get('/api/sky/integrations',headers=headers()).json()
    assert info['databases']['proyectos_compartidos_entre_modulos']['state']=='ready'

def test_existing_world_can_be_linked_to_project(cli):
    c,_=cli;pid=project(c)
    created=c.post('/api/worlds',headers=headers(),json={'name':'Exploración','prompt':'isla tecnológica','seed':42})
    assert created.status_code in (200,201),created.text
    wid=created.json()['id']
    r=c.post(f'/api/sky/projects/{pid}/links',headers=headers(),json={'kind':'world','ref':wid,'label':'Isla anterior'})
    assert r.status_code==201,r.text
    assert c.get(f'/api/sky/projects/{pid}',headers=headers()).json()['items'][0]['label']=='Isla anterior'
