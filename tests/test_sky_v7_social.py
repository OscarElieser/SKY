"""Contract tests on REAL HTTP handlers/SQLite and two in-process WebSockets."""
import os,pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_COMMUNITY_DB',str(tmp_path/'community.sqlite3'))
    monkeypatch.setenv('SKY_METAVERSE_DB',str(tmp_path/'worlds.sqlite3'))
    monkeypatch.setenv('SKY_API_KEY','my-personal-secret-to-sky-system-must-be-long')
    monkeypatch.setenv('SKY_COMUNIDAD_PUBLICA','1')   # SENTINEL: la comunidad sólo se abre si el dueño lo decide
    from metaverse.api import app
    with TestClient(app) as c:yield c

def admin_headers():return {'X-SKY-KEY':'my-personal-secret-to-sky-system-must-be-long'}

def create_user(client,handle):
    invite=client.post('/api/community/admin/invites',json={'hours':2},headers=admin_headers())
    assert invite.status_code==200,invite.text
    payload={'username':handle,'display_name':handle.title(),'password':'long-secure-Pass-'+handle,'invite':invite.json()['invite_code']}
    reg=client.post('/api/community/register',json=payload)
    assert reg.status_code==201,reg.text
    login=client.post('/api/community/login',json={'username':handle,'password':payload['password']})
    assert login.status_code==200,login.text
    return login.json()['user'],{'Authorization':'Bearer '+login.json()['access_token']}

def publish_world(client):
    r=client.post('/api/worlds',json={'name':'SKY Social','prompt':'ciudad futurista','seed':14},headers=admin_headers())
    assert r.status_code==201,r.text
    return r.json()['id']

def test_private_worlds_and_invitation_login(client):
    w=publish_world(client)
    alice,auth=create_user(client,'alice')
    assert client.get('/api/community/worlds',headers=auth).json()==[]
    assert client.get('/api/community/worlds/'+w,headers=auth).status_code==404
    assert client.get('/api/community/me',headers=auth).json()['id']==alice['id']
    assert client.post('/api/community/ws-ticket?wid='+w,headers=auth).status_code==403
    assert client.put('/api/community/admin/worlds/'+w,json={'published':True},headers=admin_headers()).status_code==200
    assert len(client.get('/api/community/worlds',headers=auth).json())==1
    assert client.get('/api/community/worlds/'+w,headers=auth).json()['scene']['objects']
    assert client.get('/api/community/me',headers={'Authorization':'Bearer invalid'}).status_code==401
    assert client.post('/api/community/register',json={'username':'evil','display_name':'Evil','password':'a'*12,'invite':'invalid'}).status_code==403
    assert client.post('/api/community/admin/invites',json={'hours':1},headers=auth).status_code==401
    assert client.post('/api/community/logout',headers=auth).status_code==200
    assert client.get('/api/community/me',headers=auth).status_code==401


def test_two_users_chat_persisted_and_private_memory(client):
    wid=publish_world(client)
    client.put('/api/community/admin/worlds/'+wid,json={'published':True},headers=admin_headers())
    alice,ah=create_user(client,'alice')
    bob,bh=create_user(client,'bob')
    ticket_a=client.post('/api/community/ws-ticket?wid='+wid,headers=ah).json()['ticket']
    ticket_b=client.post('/api/community/ws-ticket?wid='+wid,headers=bh).json()['ticket']
    with client.websocket_connect('/api/community/ws/'+wid+'?ticket='+ticket_a) as aw:
        welcome=aw.receive_json()
        assert welcome['type']=='welcome' and welcome['you']==alice['id']
        with client.websocket_connect('/api/community/ws/'+wid+'?ticket='+ticket_b) as bw:
            bob_welcome=bw.receive_json()
            assert bob_welcome['type']=='welcome' and len(bob_welcome['peers'])==2
            joined=aw.receive_json()
            assert joined['type']=='join' and joined['peer']['username']=='bob'
            aw.send_json({'type':'say','text':'Hola Bob, soy Alice'})
            msg1=aw.receive_json();msg2=bw.receive_json()
            assert msg1['type']=='say' and msg2['message']['body']=='Hola Bob, soy Alice'
            bw.send_json({'type':'move','position':[1.0,0.0,2.0]})
            moved=aw.receive_json()
            assert moved['type']=='move' and moved['peer']['id']==bob['id']
        departed=aw.receive_json()
        assert departed['type']=='leave' and departed['id']==bob['id']
    stored=client.get('/api/community/worlds/'+wid+'/messages',headers=bh).json()
    assert stored[0]['body']=='Hola Bob, soy Alice'
    memory=client.post('/api/community/me/memory',headers=ah,json={'label':'Sueño SKY','content':'Crear un parque digital'}).json()
    assert len(client.get('/api/community/me/memory',headers=ah).json())==1
    assert client.get('/api/community/me/memory',headers=bh).json()==[]
    assert client.delete('/api/community/me/memory/'+memory['id'],headers=bh).status_code==404
    assert client.delete('/api/community/me/memory/'+memory['id'],headers=ah).status_code==200
    assert client.get('/api/community/me/memory',headers=ah).json()==[]


def test_social_feed_feedback_and_versions(client):
    wid=publish_world(client)
    client.put('/api/community/admin/worlds/'+wid,json={'published':True},headers=admin_headers())
    alice,ah=create_user(client,'alice')
    bob,bh=create_user(client,'bob')
    post=client.post('/api/community/posts',headers=ah,json={'body':'Bienvenidos a SKY','world_id':wid})
    assert post.status_code==201
    pid=post.json()['id']
    client.put('/api/community/posts/'+pid+'/like',headers=bh)
    feed=client.get('/api/community/posts',headers=bh).json()
    assert feed[0]['likes']==1
    assert client.put('/api/community/users/'+alice['id']+'/follow',headers=bh).status_code==200
    assert client.post('/api/community/me/feedback',headers=ah,json={'topic':'avatar','score':5,'comment':'Me encanta'}).status_code==201
    summary=client.get('/api/community/me/learning',headers=ah).json()
    assert summary['feedback_by_topic'][0]['mean_score']==5
    assert 'NO reentrenamiento' in summary['method']
    assert client.post('/api/community/reports',headers=bh,json={'target_id':pid,'reason':'Publicación inapropiada'}).status_code==201
    assert len(client.get('/api/community/admin/reports',headers=admin_headers()).json())==1
    client.put('/api/community/admin/worlds/'+wid,json={'published':False},headers=admin_headers())
    assert client.get('/api/community/worlds/'+wid,headers=ah).status_code==404


def test_sky_private_memory_retrieval_and_social_sessions(client):
    user,auth=create_user(client,'creator')
    client.post('/api/community/me/memory',headers=auth,json={'label':'SKY','content':'crear un metaverso educativo'})
    result=client.post('/api/community/me/ask',headers=auth,json={'message':'SKY, ¿qué recuerdas de mí?','provider':'local'})
    assert result.status_code==200
    assert 'metaverso educativo' in result.json()['answer']
    assert result.json()['memory_shared'] is False
    another,bh=create_user(client,'member')
    result2=client.post('/api/community/me/ask',headers=bh,json={'message':'¿qué recuerdos tienes?','provider':'local'})
    assert 'metaverso educativo' not in result2.json()['answer']


def test_sqlite_online_backup_is_valid(client,tmp_path):
    from sky_backup import backup
    import sqlite3
    user,auth=create_user(client,'oscar')
    client.post('/api/community/me/memory',headers=auth,json={'label':'Meta','content':'Una red social creativa'})
    paths=backup(tmp_path/'backups')
    assert len(paths)==2
    for path in paths:
        with sqlite3.connect(path) as c:
            assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_voice_signaling_routes_only_to_intended_participant(client):
    wid=publish_world(client)
    client.put('/api/community/admin/worlds/'+wid,json={'published':True},headers=admin_headers())
    alice,ah=create_user(client,'alice')
    bob,bh=create_user(client,'bob')
    t1=client.post('/api/community/ws-ticket?wid='+wid,headers=ah).json()['ticket']
    t2=client.post('/api/community/ws-ticket?wid='+wid,headers=bh).json()['ticket']
    with client.websocket_connect('/api/community/ws/'+wid+'?ticket='+t1) as aw:
        aw.receive_json()
        with client.websocket_connect('/api/community/ws/'+wid+'?ticket='+t2) as bw:
            bw.receive_json()
            aw.receive_json()
            aw.send_json({'type':'webrtc-offer','to':bob['id'],'data':{'sdp':{'type':'offer','sdp':'v=0'}}})
            delivered=bw.receive_json()
            assert delivered['type']=='webrtc-offer'
            assert delivered['from']==alice['id']
            assert delivered['data']['sdp']['sdp']=='v=0'
            bw.send_json({'type':'webrtc-answer','to':alice['id'],'data':{'sdp':{'type':'answer','sdp':'v=0'}}})
            response=aw.receive_json()
            assert response['type']=='webrtc-answer' and response['from']==bob['id']
