"""SKY 9.8: composiciones, máscaras, exportación portable y animación real."""
import io, subprocess, shutil
from PIL import Image
import pytest
from test_sky_v9_7_creative import env, png, import_image, H


def test_grabcut_mask_private_and_editable(env):
    c,_=env
    b=io.BytesIO(); im=Image.new('RGB',(100,100),'white')
    for x in range(30,70):
        for y in range(30,70):im.putpixel((x,y),(0,0,0))
    im.save(b,format='PNG')
    source=c.post('/api/creative/assets',headers=H,files={'file':('test.png',b.getvalue(),'image/png')}).json()['id']
    url='/api/creative/assets/'+source+'/selection'
    assert c.post(url,json={'rectangle':[20,20,60,60]}).status_code==401
    r=c.post(url,headers=H,json={'rectangle':[20,20,60,60]})
    assert r.status_code==201,r.text
    mask=r.json()['mask_asset'];assert mask['kind']=='image'
    proj=c.post('/api/creative/projects',headers=H,json={'kind':'image','name':'Mascara','spec':{
        'width':100,'height':100,'background':'#ff0000',
        'layers':[{'type':'image','asset_id':source,'mask_asset_id':mask['id'],'width':100,'height':100}]}})
    assert proj.status_code==201,proj.text
    result=c.post(f'/api/creative/projects/{proj.json()["id"]}/image/render',headers=H)
    assert result.status_code==200,result.text
    binary=c.get('/api/creative/assets/'+result.json()['id']+'/download',headers=H).content
    with Image.open(io.BytesIO(binary)) as picture:
        assert picture.getpixel((0,0))[:3]==(255,0,0)
        assert picture.getpixel((50,50))[:3]!=(255,0,0)
    archive=c.get(f'/api/creative/projects/{proj.json()["id"]}/portable',headers=H).content
    saved=c.post('/api/creative/portable',headers=H,files={'file':('portable.skyzip',archive,'application/zip')})
    assert saved.status_code==201,saved.text
    assert saved.json()['spec']['layers'][0]['mask_asset_id']!=mask['id']


def test_mask_validation_and_protection(env):
    c,_=env;aid=import_image(c)
    assert c.post(f'/api/creative/assets/{aid}/selection',headers=H,json={'rectangle':[0,0,800,800]}).status_code==422
    spec={'width':120,'height':120,'layers':[{'type':'image','asset_id':aid,'mask_asset_id':'missing'}]}
    assert c.post('/api/creative/projects',headers=H,json={'kind':'image','name':'Invalid','spec':spec}).status_code==422


def test_video_keyframes_and_sticker_real(env):
    c,tmp=env;aid=import_image(c)
    spec={'width':320,'height':180,'fps':25,'clips':[{'asset_id':aid,'start':0,'end':1.5,'speed':1,
        'caption':'SKY v9.8','caption_motion':{'x0':-80,'x1':0,'y0':40,'y1':25,'fade_in':0.3,'fade_out':0.3},
        'sticker_asset_id':aid,'sticker_x':180,'sticker_y':40,'sticker_width':60}]}
    p=c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Animación','spec':spec})
    assert p.status_code==201,p.text
    job=c.post(f'/api/creative/projects/{p.json()["id"]}/video/render',headers=H)
    assert job.status_code==200,job.text
    from neural_core.sky_creative import run_next_job
    run=run_next_job();assert run['status']=='completed',run
    data=c.get('/api/creative/assets/'+run['asset_id']+'/download',headers=H).content
    assert len(data)>3000
    outfile=tmp/'anim.mp4';outfile.write_bytes(data)
    duration=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(outfile)],capture_output=True,text=True,check=True).stdout.strip()
    assert 1.3<float(duration)<1.8


def test_bad_motion_rejected(env):
    c,_=env;aid=import_image(c)
    spec={'clips':[{'asset_id':aid,'start':0,'end':1,'speed':1,'caption':'X','caption_motion':{'fade_in':0.7,'fade_out':0.7}}]}
    assert c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Bad','spec':spec}).status_code==422
