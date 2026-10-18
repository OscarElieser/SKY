"""SKY v9.9: pruebas sobre la API real y el render FFmpeg, sin servicios fingidos."""
from __future__ import annotations
import io,subprocess
from PIL import Image
from test_sky_v9_7_creative import env,import_image,H


def test_guided_grabcut_and_validation(env):
    client,_=env
    image=Image.new('RGB',(100,100),'white')
    for x in range(27,73):
        for y in range(25,75):image.putpixel((x,y),(10,10,20))
    buf=io.BytesIO();image.save(buf,format='PNG')
    aid=client.post('/api/creative/assets',headers=H,files={'file':('shape.png',buf.getvalue(),'image/png')}).json()['id']
    endpoint=f'/api/creative/assets/{aid}/selection'
    payload={'rectangle':[18,18,63,64],'iterations':3,'foreground':[[45,45]],'background':[[5,5]],'brush_radius':3}
    assert client.post(endpoint,json=payload).status_code==401
    r=client.post(endpoint,headers=H,json=payload)
    assert r.status_code==201,r.text
    assert r.json()['guide_points']=={'foreground':1,'background':1}
    mask=client.get('/api/creative/assets/'+r.json()['mask_asset']['id']+'/download',headers=H).content
    with Image.open(io.BytesIO(mask)) as result:
        assert result.getpixel((45,45))>0
        assert result.getpixel((5,5))==0
    payload['foreground']=[[500,100]]
    assert client.post(endpoint,headers=H,json=payload).status_code==422
    payload['foreground']=[[5,5]]
    assert client.post(endpoint,headers=H,json=payload).status_code==422


def test_multi_keyframe_video_render_and_portable(env):
    client,tmp=env
    aid=import_image(client)
    spec={'width':320,'height':180,'fps':25,'clips':[{ 'asset_id':aid,'start':0,'end':1.7,'speed':1,
        'caption':'SKY v9.9', 'caption_keyframes':[
            {'t':0.0,'x':-20,'y':25},
            {'t':0.4,'x':80,'y':35},
            {'t':1.1,'x':50,'y':65},
            {'t':1.7,'x':140,'y':20}],
        'caption_easing':'smooth'}]}
    response=client.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Timeline SKY','spec':spec})
    assert response.status_code==201,response.text
    pid=response.json()['id']
    from neural_core.sky_creative import run_next_job
    job=client.post(f'/api/creative/projects/{pid}/video/render',headers=H)
    assert job.status_code==200,job.text
    result=run_next_job();assert result['status']=='completed',result
    blob=client.get('/api/creative/assets/'+result['asset_id']+'/download',headers=H).content
    assert blob[:8] != b'' and len(blob)>4000
    target=tmp/'keyframe.mp4';target.write_bytes(blob)
    duration=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
      '-of','default=noprint_wrappers=1:nokey=1',str(target)],capture_output=True,text=True,check=True).stdout)
    assert 1.5<=duration<=1.9
    portable=client.get(f'/api/creative/projects/{pid}/portable',headers=H).content
    imported=client.post('/api/creative/portable',headers=H,files={'file':('edicion.skyzip',portable,'application/zip')})
    assert imported.status_code==201,imported.text
    assert len(imported.json()['spec']['clips'][0]['caption_keyframes'])==4


def test_invalid_keyframe_times_and_interpolation(env):
    client,_=env;aid=import_image(client)
    base={'asset_id':aid,'start':0,'end':1.5,'speed':1,'caption':'SKY',
          'caption_keyframes':[{'t':0.7,'x':0,'y':0},{'t':0.2,'x':30,'y':30}]}
    req=lambda clip:client.post('/api/creative/projects',headers=H,
                 json={'kind':'video','name':'Invalid','spec':{'clips':[clip]}})
    assert req(base).status_code==422
    base['caption_keyframes'][1]['t']=1.6
    assert req(base).status_code==422
    base['caption_keyframes'][1]['t']=1.4
    base['caption_easing']='invalid'
    assert req(base).status_code==422
    base['caption_easing']='linear'
    assert req(base).status_code==201
