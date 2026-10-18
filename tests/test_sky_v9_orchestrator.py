"""Pruebas de integración: herramientas locales reales, SQL y API autenticada."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import re
import pytest
from fastapi.testclient import TestClient
from neural_core.sky_roles import ROLES,select_roles,plan_for
from neural_core.sky_experience import make_experience,experience_html

KEY='skys-authentication-test-private-key-0123456789'

@pytest.fixture()
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_API_KEY',KEY)
    monkeypatch.setenv('SKY_METAVERSE_DB',str(tmp_path/'worlds.sqlite3'))
    monkeypatch.setenv('SKY_COMMUNITY_DB',str(tmp_path/'community.sqlite3'))
    monkeypatch.setenv('SKY_WORKBENCH_DB',str(tmp_path/'workbench.sqlite3'))
    monkeypatch.setenv('SKY_TELEMETRY_DB',str(tmp_path/'telemetry.sqlite3'))
    # Para artefactos de integración, temporalizar ubicación del módulo.
    import neural_core.sky_workbench as w
    monkeypatch.setattr(w,'STORE',tmp_path)
    from metaverse.api import app
    with TestClient(app) as c:yield c

def h():return {'X-SKY-KEY':KEY}

def request(client,task,action='plan',params=None):
    return client.post('/api/sky/tasks',headers=h(),json={'task':task,'action':action,'params':params or {}})

def test_role_catalog_and_multiple_roles():
    assert len(ROLES)>=30
    roles=select_roles('Diseñá un metaverso con curso educativo y negocios')
    assert any(r['id']=='metaverso' for r in roles)
    assert len(roles)>=2

@pytest.mark.parametrize('txt,expected',[
    ('Diseña un curso de capacitación','educacion'),
    ('Controlar facturas y contabilidad','contabilidad'),
    ('Comprar bitcoin con análisis de riesgos','cripto'),
    ('Necesito apoyo en BAQUEANO turismo','baqueano'),
])
def test_specialist_matches(txt,expected):
    assert expected in [r['id'] for r in select_roles(txt)]

def test_empty_and_massive_prompts():
    with pytest.raises(ValueError):select_roles('')
    with pytest.raises(ValueError):select_roles('a'*8001)

def test_role_plan_no_side_effects(client):
    plan=client.post('/api/sky/plan',headers=h(),json={'task':'Diseñame una clase en Word'}).json()
    assert len(plan['steps'])==4
    assert client.get('/api/sky/tasks',headers=h()).json()==[]

def test_privileged_endpoints_need_key(client):
    for path in ['/api/sky/roles','/api/sky/tasks','/api/sky/activity','/api/sky/memory','/api/sky/creator/options']:
        assert client.get(path).status_code==401,path
    assert client.get('/studio').status_code==200
    assert client.get('/static/studio.js').status_code==200
    assert client.get('/api/sky/roles',headers=h()).json()['count']==len(ROLES)

def test_task_plan_persists_and_approves(client):
    r=request(client,'Crear plan para preparar una feria de emprendimiento')
    assert r.status_code==201,r.text
    ident=r.json()['id']
    assert r.json()['status']=='pendiente'
    assert client.post('/api/sky/tasks/'+ident+'/execute',headers=h(),json={'approve':False}).status_code==403
    done=client.post('/api/sky/tasks/'+ident+'/execute',headers=h(),json={'approve':True})
    assert done.status_code==200,done.text
    assert done.json()['status']=='completada'
    assert client.post('/api/sky/tasks/'+ident+'/execute',headers=h(),json={'approve':True}).status_code==409
    assert client.get('/api/sky/tasks/'+ident,headers=h()).json()['output']['kind']=='plan'

def test_task_cannot_run_unknown_action(client):
    assert request(client,'Hacer un documento profesional','shell',{}).status_code==422

def test_experience_is_real_html_and_sanitized(client):
    spec=make_experience('Una escuela digital',{ 'title':'<script>alert(1)</script>','palette':'nature'})
    html=experience_html(spec)
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'grid-template-columns' in html
    assert 'SKY IA' in html
    r=client.post('/api/sky/experiences/preview',headers=h(),json={'prompt':'Creamos un museo interactivo'})
    assert r.status_code==200
    assert '<!doctype html>' in r.json()['html']

def test_workbench_saves_experience(client):
    job=request(client,'Creá una academia digital con aulas virtuales','experience',{'title':'Academia SKY','template':'classroom','palette':'sky'})
    assert job.status_code==201
    ident=job.json()['id']
    done=client.post(f'/api/sky/tasks/{ident}/execute',headers=h(),json={'approve':True})
    assert done.status_code==200,done.text
    assert done.json()['output']['kind']=='experience'
    spec=client.get(f'/api/sky/experiences/{ident}',headers=h()).json()
    assert spec['template']=='classroom'
    html=client.get(f'/api/sky/experiences/{ident}/html',headers=h())
    assert html.status_code==200 and b'Academia SKY' in html.content
    assert 'attachment' in html.headers['content-disposition']

def test_unsupported_template_fails_without_persisting(client):
    data=request(client,'Diseñar un sitio de inteligencia artificial','experience',{'template':'secret-system'})
    ident=data.json()['id']
    response=client.post(f'/api/sky/tasks/{ident}/execute',headers=h(),json={'approve':True})
    assert response.status_code==422
    assert client.get('/api/sky/tasks/'+ident,headers=h()).json()['status']=='error'

def test_real_office_file_persistent_and_download(client):
    payload={'document':{'kind':'pptx','title':'Presentación SKY','content':'# Introducción\nContenido real.\n# Propuesta\nObjetivos'}}
    job=request(client,'Crear presentación para emprendimientos','document',payload)
    ident=job.json()['id']
    assert client.get('/api/sky/files/'+ident,headers=h()).status_code==404
    result=client.post(f'/api/sky/tasks/{ident}/execute',headers=h(),json={'approve':True})
    assert result.status_code==200,result.text
    saved=result.json()['output']
    assert saved['kind']=='file'
    r=client.get('/api/sky/files/'+ident,headers=h())
    assert r.status_code==200 and r.content[:2]==b'PK'
    assert 'presentationml' in r.headers['content-type']
    from pptx import Presentation
    assert len(Presentation(BytesIO(r.content)).slides)>1

def test_xlsx_export_numeric_data(client):
    params={'document':{'kind':'xlsx','title':'Ventas reales','csv':'Producto,Ingresos\nServicios,250\nCursos,150'}}
    item=request(client,'Crear Excel con ingresos empresariales','document',params).json()
    done=client.post('/api/sky/tasks/'+item['id']+'/execute',headers=h(),json={'approve':True})
    assert done.status_code==200,done.text
    x=client.get('/api/sky/files/'+item['id'],headers=h())
    assert x.status_code==200 and x.content[:2]==b'PK'
    assert 'spreadsheetml' in x.headers['content-type']

def test_no_blank_document_without_real_content(client):
    item=request(client,'Generar un reporte no vacío','document',{'document':{'kind':'pdf','title':'Sin datos'}}).json()
    r=client.post('/api/sky/tasks/'+item['id']+'/execute',headers=h(),json={'approve':True})
    assert r.status_code==422

def test_real_world_is_created(client):
    job=request(client,'Crear un mundo metaverso de ciudad futurista','world',{'name':'Mundo SKY','prompt':'ciudad futurista'})
    ident=job.json()['id']
    r=client.post('/api/sky/tasks/'+ident+'/execute',headers=h(),json={'approve':True})
    assert r.status_code==200,r.text
    wid=r.json()['output']['world_id']
    w=client.get('/api/worlds/'+wid,headers=h())
    assert w.status_code==200 and w.json()['scene']['objects']

def test_memory_is_optin_and_deletable(client):
    item=request(client,'Recordar el lema oficial del proyecto SKY','memory',{'label':'Lema','content':'Crea, conecta, evoluciona'})
    ident=item.json()['id']
    client.post('/api/sky/tasks/'+ident+'/execute',headers=h(),json={'approve':True})
    notes=client.get('/api/sky/memory',headers=h()).json()
    assert notes[0]['label']=='Lema'
    r=client.post('/api/sky/assist',headers=h(),json={'message':'Prepara un plan de marketing','provider':'local','include_memory':False})
    assert r.status_code==200 and 'Crea, conecta' not in str(r.json())
    assert client.delete('/api/sky/memory/'+ident,headers=h()).status_code==200
    assert client.get('/api/sky/memory',headers=h()).json()==[]

def test_no_automatic_external_provider(client):
    r=client.post('/api/sky/assist',headers=h(),json={'message':'Preparar un presupuesto','provider':'local'})
    assert r.status_code==200
    assert r.json()['provider']=='sky-local'
    assert r.json()['roles'][0]['id'] in ROLES
    r2=client.post('/api/sky/assist',headers=h(),json={'message':'Hola','provider':'unknown'})
    assert r2.status_code==422

def test_activity_is_real_and_content_free(client):
    client.get('/api/sky/roles',headers=h())
    client.get('/api/sky/tasks',headers=h())
    d=client.get('/api/sky/activity',headers=h()).json()
    assert d['events_sampled']>0
    assert all('content' not in e and 'api_key' not in e for e in d['events'])
    assert d['average_ms_in_sample'] is not None

def test_audit_metadata_does_not_dump_prompts(client):
    task='Propuesta comercial confidencial ABCXYZ2026'
    job=request(client,task)
    audit=client.get('/api/sky/audit',headers=h()).json()
    assert audit and task not in str(audit)
    assert job.json()['id'] in str(audit)

def test_extended_backup_includes_workbench(client,tmp_path):
    from sky_backup import backup
    item=request(client,'Guardar plan de mantenimiento del sistema')
    assert item.status_code==201
    paths=backup(tmp_path/'backups_extended',include_extended=True)
    assert any('workbench' in x for x in paths)
    assert any('telemetria' in x for x in paths)
    from sqlite3 import connect
    for f in paths:
        p=Path(f)
        if p.suffix=='.sqlite3':
            with connect(p) as c:assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
