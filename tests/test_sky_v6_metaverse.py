"""Tests integrados para API propia, escenas y sesión 3D sin llamadas a la nube."""
from io import BytesIO
import json, os, pytest
import trimesh
from fastapi.testclient import TestClient
from metaverse.engine import generate_scene, validate_object,theme_of
from metaverse.export3d import export_scene_glb
from metaverse import store

@pytest.fixture(autouse=True)
def private_env(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_METAVERSE_DB',str(tmp_path/'scenes.sqlite3'))
    monkeypatch.setenv('SKY_API_KEY','sk_test_token_private_abcdefghijklmnopqrstuvwxyz')

@pytest.fixture()
def cli():
    from metaverse.api import app
    return TestClient(app)

def headers():return {'X-SKY-KEY':'sk_test_token_private_abcdefghijklmnopqrstuvwxyz'}

@pytest.mark.parametrize('text,theme',[('Creá una selva','bosque'),('La playa','playa'),('Edificios de una ciudad','ciudad'),('Viajar a Marte','espacio'),('Laboratorio creativo','estudio')])
def test_themes(text,theme):assert generate_scene(text)['theme']==theme

def test_unique_ids_and_limits():
    data=generate_scene('ciudad',11)
    assert len({x['id'] for x in data['objects']})==len(data['objects'])
    assert 5<len(data['objects'])<=180
    with pytest.raises(ValueError):validate_object({'kind':'__import__','color':'#ff0000'})
    with pytest.raises(ValueError):validate_object({'kind':'box','position':[float('inf'),0,0]})
    with pytest.raises(ValueError):generate_scene('')

def test_export_real_glb():
    blob=export_scene_glb(generate_scene('playa',10))
    assert blob[:4]==b'glTF'
    scene=trimesh.load(BytesIO(blob),file_type='glb')
    assert len(scene.geometry)>10

def test_private_api(cli):
    assert cli.get('/api/health').status_code==200
    assert cli.get('/api/worlds').status_code==401
    assert cli.get('/api/worlds',headers={'X-SKY-KEY':'wrong'}).status_code==401
    assert cli.get('/api/capabilities',headers=headers()).status_code==200

def test_crud_versions(cli):
    created=cli.post('/api/worlds',headers=headers(),json={'name':'Bosque','prompt':'Selva tropical'}).json()
    assert created['version']==1
    wid=created['id'];assert cli.get('/api/worlds/'+wid,headers=headers()).status_code==200
    updated=cli.put('/api/worlds/'+wid,headers=headers(),json={'version':1,'scene':created['scene']})
    assert updated.json()['version']==2
    stale=cli.put('/api/worlds/'+wid,headers=headers(),json={'version':1,'scene':created['scene']})
    assert stale.status_code==409
    assert cli.get('/api/worlds/'+wid+'/export.glb',headers=headers()).content[:4]==b'glTF'
    assert cli.delete('/api/worlds/'+wid,headers=headers()).status_code==200
    assert cli.get('/api/worlds/'+wid,headers=headers()).status_code==404

def test_generator_append_and_add_object(cli):
    data=cli.post('/api/worlds',headers=headers(),json={'name':'Ideas','prompt':'estudio'}).json()
    res=cli.post('/api/worlds/'+data['id']+'/generate',headers=headers(),json={'version':1,'prompt':'playa','append':True})
    assert res.status_code==200
    result=res.json();assert len(result['scene']['objects'])>len(data['scene']['objects'])
    ob=cli.post('/api/worlds/'+data['id']+'/objects',headers=headers(),json={'version':result['version'],'object':{'kind':'sphere','color':'#FFAC01'}})
    assert ob.status_code==200
    assert ob.json()['scene']['objects'][-1]['kind']=='sphere'

def test_socket_and_ticket(cli):
    wid=cli.post('/api/worlds',headers=headers(),json={'name':'Room','prompt':'galaxia'}).json()['id']
    data=cli.post('/api/ws-ticket',headers=headers()).json()
    with cli.websocket_connect('/api/ws/'+wid+'?ticket='+data['ticket']) as s:
        assert s.receive_json()['type']=='peers'
        assert s.receive_json()['type']=='join'
        s.send_json({'type':'say','text':'Hola SKY'})
        assert s.receive_json()['text']=='Hola SKY'
    # tickets cannot be reused
    with pytest.raises(Exception):
        with cli.websocket_connect('/api/ws/'+wid+'?ticket='+data['ticket']) as s:s.receive_json()

def test_skills_and_chat(cli):
    assert cli.post('/api/tools/run',headers=headers(),json={'name':'calcular','argument':'(12+8)/4'}).json()['result']==5
    assert cli.post('/api/tools/run',headers=headers(),json={'name':'os.system','argument':'pwd'}).status_code==422
    assert 'Resultado:' in cli.post('/api/chat',headers=headers(),json={'message':'/sky calcula 7*6'}).json()['answer']
    assert 'SKY local' in cli.post('/api/chat',headers=headers(),json={'message':'hola'}).json()['answer']

def test_storage_persistence_and_conflict():
    w=store.create_world('Mi estudio','estudio')
    assert store.get_world(w['id'])['scene']['objects']
    with pytest.raises(RuntimeError):store.save_scene(w['id'],w['scene'],2)
    with pytest.raises(ValueError):store.save_scene(w['id'],{**w['scene'],'objects':[w['scene']['objects'][0]]*181},1)

def test_openai_compatible_client(cli):
    data=cli.post('/v1/chat/completions',headers=headers(),json={
        'model':'local','messages':[{'role':'user','content':'/sky calcula 2+5'}]}).json()
    assert data['choices'][0]['message']['content'].endswith('7.0')
    assert cli.post('/v1/chat/completions',headers=headers(),json={
        'model':'local','messages':[{'role':'user','content':'hola'}],'stream':True}).status_code==422
    assert cli.get('/v1/models',headers=headers()).status_code==200

def test_photo_to_glb_local(cli):
    from PIL import Image
    img=Image.new('RGB',(40,40),'white')
    for i in range(10,30):
        for j in range(10,30): img.putpixel((i,j),(26,140,218))
    bio=BytesIO();img.save(bio,format='PNG')
    r=cli.post('/api/studio/photo-to-glb?x0=0.20&y0=0.20&x1=0.80&y1=0.80',headers={**headers(),'Content-Type':'image/png'},content=bio.getvalue())
    assert r.status_code==200,r.text[:200]
    assert r.content[:4]==b'glTF'
    assert r.headers['X-SKY-3D-Method']=='2.5D-silhouette-extrusion'
    assert cli.post('/api/studio/photo-to-glb',headers={**headers(),'Content-Type':'text/plain'},content=b'fake').status_code==415
