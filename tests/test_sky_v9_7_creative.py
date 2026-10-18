"""SKY v9.7 — pruebas reales de composición de imagen/video, API y continuidad."""
from __future__ import annotations
import io,subprocess,zipfile
from PIL import Image
import pytest
from fastapi.testclient import TestClient

KEY='owner-creative-key-long-and-secure-test'
H={'X-SKY-KEY':KEY}

@pytest.fixture
def env(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_API_KEY',KEY)
    monkeypatch.setenv('SKY_WORKFLOWS_ENABLED','0')
    monkeypatch.setenv('SKY_CREATIVE_WORKER','0')
    monkeypatch.setenv('SKY_CREATIVE_DB',str(tmp_path/'creative.db'))
    monkeypatch.setenv('SKY_CREATIVE_DIR',str(tmp_path/'media_store'))
    monkeypatch.setenv('SKY_PROJECTS_DB',str(tmp_path/'projects.db'))
    monkeypatch.setenv('SKY_METAVERSE_DB',str(tmp_path/'worlds.db'))
    from metaverse.api import app
    with TestClient(app) as client:yield client,tmp_path

def png(colour='red'):
    b=io.BytesIO();Image.new('RGB',(40,40),colour).save(b,format='PNG');return b.getvalue()

def import_image(client):
    r=client.post('/api/creative/assets',headers=H,files={'file':('pintura.png',png(),'image/png')})
    assert r.status_code==201,r.text
    return r.json()['id']

def test_private_upload_magic_and_library(env):
    c,_=env
    assert c.get('/api/creative/assets').status_code==401
    assert c.post('/api/creative/assets',files={'file':('hello.png',png(),'image/png')}).status_code==401
    bad=c.post('/api/creative/assets',headers=H,files={'file':('bad.png',b'not an image','image/png')})
    assert bad.status_code==422
    id=import_image(c)
    r=c.get('/api/creative/assets',headers=H)
    assert r.status_code==200 and r.json()[0]['id']==id
    assert c.get('/api/creative/assets/'+id+'/preview').status_code==401
    binary=c.get('/api/creative/assets/'+id+'/download',headers=H).content
    assert binary==png()
    assert c.get('/api/creative/assets/asset_unknown/preview',headers=H).status_code==404

def test_multilayer_image_versioning_export_real(env):
    c,_=env;id=import_image(c)
    spec={'width':360,'height':200,'background':'#112233','layers':[
        {'type':'rectangle','x':30,'y':20,'width':60,'height':45,'color':'#00ff00','opacity':1},
        {'type':'image','asset_id':id,'x':110,'y':20,'width':50,'opacity':1},
        {'type':'text','text':'SKY IA','x':160,'y':90,'size':30,'color':'#ffffff','opacity':1}],
        'adjustments':{'contrast':1,'brightness':1,'saturation':1}}
    r=c.post('/api/creative/projects',headers=H,json={'kind':'image','name':'Póster de SKY','spec':spec})
    assert r.status_code==201,r.text;pid=r.json()['id']
    a=c.post(f'/api/creative/projects/{pid}/image/render?format=png',headers=H).json()
    with Image.open(io.BytesIO(c.get('/api/creative/assets/'+a['id']+'/download',headers=H).content)) as image:
        assert image.size==(360,200)
        assert image.getpixel((45,33))[:3]==(0,255,0)
        assert image.getpixel((125,36))[:3]==(255,0,0)
    spec['layers'][0]['color']='#0000ff'
    assert c.put(f'/api/creative/projects/{pid}',headers=H,json={'spec':spec,'expected_version':0}).status_code==422
    v=c.put(f'/api/creative/projects/{pid}',headers=H,json={'spec':spec,'expected_version':1});assert v.status_code==200
    assert c.put(f'/api/creative/projects/{pid}',headers=H,json={'spec':spec,'expected_version':1}).status_code==409
    a2=c.post(f'/api/creative/projects/{pid}/image/render?format=webp',headers=H).json()
    assert a2['id']!=a['id']
    assert len(c.get(f'/api/creative/projects/{pid}/exports',headers=H).json())==2

def test_sky_project_hub_links_creative_spec_and_binary(env):
    c,_=env;id=import_image(c)
    from neural_core.sky_projects import create_project,export_zip,brief
    root=create_project('Diseño editorial')
    p=c.post('/api/creative/projects',headers=H,json={'kind':'image','name':'Diseño integrado','sky_project_id':root['id'],
       'spec':{'width':200,'height':150,'layers':[{'type':'image','asset_id':id,'width':50,'x':0,'y':0}]}})
    assert p.status_code==201,p.text
    c.post(f'/api/creative/projects/{p.json()["id"]}/image/render',headers=H)
    assert any(x['kind']=='creative' for x in brief(root['id'])['items'])
    data,_=export_zip(root['id'])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert any(x.endswith('creative_project.json') for x in z.namelist())
        assert any(x.endswith('png') for x in z.namelist())

def test_real_video_render_with_caption_and_two_clips(env):
    c,tmp=env
    video=tmp/'sample.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=blue:s=320x180:r=25',
                   '-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2.2','-c:v','libx264','-pix_fmt','yuv420p',
                   '-c:a','aac',str(video)],check=True,timeout=40)
    imported=c.post('/api/creative/assets',headers=H,files={'file':('video.mp4',video.read_bytes(),'video/mp4')})
    assert imported.status_code==201,imported.text
    asset=imported.json()
    spec={'width':320,'height':180,'fps':25,'clips':[
        {'asset_id':asset['id'],'start':0,'end':1,'speed':1,'caption':'SKY Edición real'},
        {'asset_id':asset['id'],'start':0.5,'end':1.5,'speed':1,'caption':''}]}
    r=c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Mi primer montaje','spec':spec})
    assert r.status_code==201,r.text;pid=r.json()['id']
    j=c.post(f'/api/creative/projects/{pid}/video/render',headers=H)
    assert j.status_code==200,j.text
    from neural_core.sky_creative import run_next_job
    result=run_next_job()
    assert result['status']=='completed',result
    b=c.get('/api/creative/assets/'+result['asset_id']+'/download',headers=H)
    assert b.status_code==200 and len(b.content)>4000
    rendered=tmp/'output.mp4';rendered.write_bytes(b.content)
    duration=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(rendered)],
        capture_output=True,text=True,check=True).stdout
    assert 1.7<float(duration)<2.4
    assert result['progress']==100

def test_job_recovery_no_silent_reprocessing(env):
    from neural_core import sky_creative as s
    with s.connection() as db:
        db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)',('job_crashed','crt_x','running',22,'',None,s.now(),s.now()))
    s.mark_interrupted()
    assert s.job_info('job_crashed')['status']=='needs_review'
    with pytest.raises(RuntimeError):s.retry_job('missing')
    assert s.retry_job('job_crashed')['status']=='queued'
    assert s.cancel_job('job_crashed')
    assert s.job_info('job_crashed')['status']=='cancelled'

def test_invalid_specs_security_and_limits(env):
    c,_=env
    for bad in [ {'width':100,'height':100,'layers':[{'type':'image','asset_id':'../../etc/passwd'}]},
                 {'width':5000,'height':100,'layers':[]}, {'width':640,'height':360,'layers':[{'type':'script','data':'evil'}]} ]:
        assert c.post('/api/creative/projects',headers=H,json={'name':'invalid','kind':'image','spec':bad}).status_code==422
    assert c.post('/api/creative/projects',headers=H,json={'name':'Sin video','kind':'video','spec':{'clips':[]}}).status_code==422

def test_no_creator_access_through_social_bearer(env):
    c,_=env
    assert c.get('/api/creative/projects',headers={'Authorization':'Bearer prueba'}).status_code==401
    assert c.get('/creative').status_code==200  # shell público, sin datos
    assert c.get('/api/creative/jobs').status_code==401

def test_spanish_commands_are_real_and_versioned(env):
    c,_=env
    obj=c.post('/api/creative/projects',headers=H,json={'kind':'image','name':'Póster guiado',
                'spec':{'width':320,'height':180,'layers':[]}}).json()
    r=c.post(f'/api/creative/projects/{obj["id"]}/command',headers=H,
             json={'instruction':'Agrega texto Innovación con SKY','expected_version':1})
    assert r.status_code==200,r.text
    assert r.json()['spec']['layers'][0]['text']=='Innovación con SKY'
    r=c.post(f'/api/creative/projects/{obj["id"]}/command',headers=H,
             json={'instruction':'contraste 1.7','expected_version':2})
    assert r.status_code==200,r.text
    assert r.json()['spec']['adjustments']['contrast']==1.7
    assert c.post(f'/api/creative/projects/{obj["id"]}/command',headers=H,
             json={'instruction':'brillo 1.9','expected_version':1}).status_code==409
    versions=c.get(f'/api/creative/projects/{obj["id"]}/versions',headers=H).json()
    assert len(versions)==3
    assert 'Innovación' not in versions[-1]['spec']  # original intacto
    assert c.post(f'/api/creative/projects/{obj["id"]}/command',headers=H,
             json={'instruction':'abrí la cuenta del banco','expected_version':3}).status_code==422

def test_slideshow_from_image_is_real_mp4(env):
    c,tmp=env;img=import_image(c)
    r=c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Video creado desde fotografía',
      'spec':{'width':320,'height':180,'fps':25,'clips':[{'asset_id':img,'start':0,'end':1.2,'speed':1,'caption':'Creatividad con SKY'}]}})
    assert r.status_code==201,r.text
    p=r.json();job=c.post(f'/api/creative/projects/{p["id"]}/video/render',headers=H).json()
    from neural_core.sky_creative import run_next_job
    state=run_next_job()
    assert state['status']=='completed',state
    video=c.get('/api/creative/assets/'+state['asset_id']+'/download',headers=H)
    assert video.status_code==200 and len(video.content)>3000
    assert any(x['kind']=='video' and (x['duration'] or 0)>1 for x in c.get('/api/creative/assets',headers=H).json())

def test_video_instruction_updates_caption(env):
    c,_=env;img=import_image(c)
    r=c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Corto',
      'spec':{'width':320,'height':180,'clips':[{'asset_id':img,'start':0,'end':2,'speed':1}]}})
    p=r.json()
    edit=c.post(f'/api/creative/projects/{p["id"]}/command',headers=H,
      json={'instruction':'Pon texto ¡Bienvenidos a SKY! en clip 1','expected_version':1})
    assert edit.status_code==200,edit.text
    assert edit.json()['spec']['clips'][0]['caption']=='¡Bienvenidos a SKY!'

def test_portable_export_import_with_real_media(env):
    c,_=env;asset=import_image(c)
    spec={'width':260,'height':180,'layers':[{'type':'image','asset_id':asset,'width':100,'x':0,'y':0}]}
    created=c.post('/api/creative/projects',headers=H,json={'kind':'image','name':'Proyecto transportable','spec':spec}).json()
    archive=c.get(f'/api/creative/projects/{created["id"]}/portable',headers=H)
    assert archive.status_code==200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        assert 'SKY_Creative_Project.json' in z.namelist()
        assert any(s.endswith('.png') for s in z.namelist())
    imported=c.post('/api/creative/portable',headers=H,files={'file':('sky.skyzip',archive.content,'application/zip')})
    assert imported.status_code==201,imported.text
    another=imported.json()
    assert another['id']!=created['id']
    saved=c.post(f'/api/creative/projects/{another["id"]}/image/render',headers=H)
    assert saved.status_code==200
    broken=bytearray(archive.content);broken[-22:]=bytes(22)
    assert c.post('/api/creative/portable',headers=H,files={'file':('tampered.skyzip',bytes(broken),'application/zip')}).status_code==422

def test_optional_gemini_image_generation_requires_owner_and_explicit_provider(env,monkeypatch):
    c,_=env
    from neural_core import gemini_provider
    monkeypatch.setattr(gemini_provider,'generar_imagen',lambda prompt:(png('blue'),'image/png'))
    path='/api/creative/generate-image'
    assert c.post(path,json={'prompt':'Ilustración de ciudad futurista'}).status_code==401
    assert c.post(path,headers=H,json={'prompt':'Ilustración de ciudad futurista','provider':'openai'}).status_code==422
    r=c.post(path,headers=H,json={'prompt':'Ilustración de ciudad futurista','provider':'gemini'})
    assert r.status_code==201,r.text
    assert r.json()['kind']=='image'
    assert c.get('/api/creative/assets/'+r.json()['id']+'/download',headers=H).content==png('blue')

def test_queued_render_uses_approved_spec_snapshot(env):
    c,_=env;aid=import_image(c)
    spec={'width':320,'height':180,'clips':[{'asset_id':aid,'start':0,'end':1,'speed':1,'caption':'Original'}]}
    p=c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Revisión','spec':spec}).json()
    j=c.post(f'/api/creative/projects/{p["id"]}/video/render',headers=H).json()
    spec['clips'][0]['caption']='Editado después'
    updated=c.put(f'/api/creative/projects/{p["id"]}',headers=H,json={'expected_version':1,'spec':spec})
    assert updated.status_code==200
    from neural_core.sky_creative import connection,run_next_job
    with connection() as db:
        row=db.execute('SELECT project_version,spec FROM job_specs WHERE job_id=?',(j['id'],)).fetchone()
        assert row['project_version']==1
        assert 'Original' in row['spec'] and 'Editado después' not in row['spec']
    result=run_next_job()
    assert result['status']=='completed',result
    history=c.get(f'/api/creative/projects/{p["id"]}/exports',headers=H).json()
    assert history[0]['version']==1

def test_background_worker_completes_approved_job_without_manual_run(tmp_path,monkeypatch):
    """Prueba real del bucle FastAPI: el render avanza en segundo plano local."""
    import time
    monkeypatch.setenv('SKY_API_KEY',KEY)
    monkeypatch.setenv('SKY_WORKFLOWS_ENABLED','0')
    monkeypatch.setenv('SKY_CREATIVE_WORKER','1')
    monkeypatch.setenv('SKY_CREATIVE_DB',str(tmp_path/'auto.db'))
    monkeypatch.setenv('SKY_CREATIVE_DIR',str(tmp_path/'auto_media'))
    monkeypatch.setenv('SKY_METAVERSE_DB',str(tmp_path/'worlds.db'))
    from metaverse.api import app
    with TestClient(app) as c:
        asset=import_image(c)
        p=c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Video automático',
          'spec':{'width':320,'height':180,'clips':[{'asset_id':asset,'start':0,'end':1,'speed':1,'caption':'Proceso SKY'}]}}).json()
        job=c.post('/api/creative/projects/'+p['id']+'/video/render',headers=H).json()
        deadline=time.monotonic()+13
        while time.monotonic()<deadline:
            state=c.get('/api/creative/jobs/'+job['id'],headers=H).json()
            if state['status'] in ('completed','failed'):break
            time.sleep(.25)
        assert state['status']=='completed',state
        data=c.get('/api/creative/assets/'+state['asset_id']+'/download',headers=H).content
        assert len(data)>2000
