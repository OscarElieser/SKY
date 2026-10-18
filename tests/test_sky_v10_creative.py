"""SKY v10 — seguimiento real de fotogramas, composición, API y seguridad."""
from __future__ import annotations
import io, os, subprocess
from pathlib import Path
import pytest
from PIL import Image, ImageDraw
from test_sky_v9_7_creative import env, H


def moving_sample():
    """MP4 auténtico con una marca visual que avanza de izquierda a derecha."""
    import cv2, numpy as np
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as t:
        path=Path(t)/'moving.mp4'
        writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),12,(320,180))
        assert writer.isOpened()
        patch=np.random.default_rng(123).integers(20,240,(30,30,3),dtype=np.uint8)
        for n in range(24):
            frame=np.full((180,320,3),30,dtype=np.uint8)
            x=45+3*n
            frame[60:90,x:x+30]=patch
            writer.write(frame)
        writer.release()
        return path.read_bytes()


def layer_image():
    src=Image.new('RGBA',(80,50),(0,0,0,0))
    ImageDraw.Draw(src).rectangle((2,2,77,47),fill=(245,55,100,230))
    raw=io.BytesIO();src.save(raw,format='PNG');return raw.getvalue()


def test_v10_tracking_render_and_frame_from_actual_export(env):
    client,folder=env
    movie=client.post('/api/creative/assets',headers=H,files={'file':('moving.mp4',moving_sample(),'video/mp4')})
    assert movie.status_code==201,movie.text
    aid=movie.json()['id']
    icon=client.post('/api/creative/assets',headers=H,files={'file':('overlay.png',layer_image(),'image/png')})
    assert icon.status_code==201,icon.text
    tracking={'rectangle':[45,60,30,30],'start':0,'end':1.5,'step':.25,'width':320,'height':180}
    assert client.post(f'/api/creative/assets/{aid}/track',json=tracking).status_code==401
    received=client.post(f'/api/creative/assets/{aid}/track',headers=H,json=tracking)
    assert received.status_code==200,received.text
    points=received.json()['keyframes']; assert len(points)>=6
    assert points[-1]['x']>points[0]['x']+25,points
    assert received.json()['method']=='opencv-template-matching'
    spec={'width':320,'height':180,'fps':24,'clips':[{'asset_id':aid,'start':0,'end':1.6,'speed':1,
        'overlays':[{'asset_id':icon.json()['id'],'width':30,'opacity':.8,'keyframes':points,'from':0,'to':1.5}]}]}
    created=client.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Composición SKY 10','spec':spec})
    assert created.status_code==201,created.text
    pid=created.json()['id']
    exact=f'/api/creative/projects/{pid}/video/frame?t=.5'
    assert client.get(exact,headers=H).status_code==409
    queued=client.post(f'/api/creative/projects/{pid}/video/render',headers=H)
    assert queued.status_code==200,queued.text
    from neural_core.sky_creative import run_next_job
    job=run_next_job();assert job['status']=='completed',job
    assert client.get(exact).status_code==401
    frame=client.get(exact,headers=H)
    assert frame.status_code==200,frame.text[:200] if frame.status_code!=200 else ''
    with Image.open(io.BytesIO(frame.content)) as image: assert image.size==(320,180)
    export=client.get(f'/api/creative/projects/{pid}/portable',headers=H)
    assert export.status_code==200
    imported=client.post('/api/creative/portable',headers=H,files={'file':('respaldo.skyzip',export.content,'application/zip')})
    assert imported.status_code==201,imported.text
    assert imported.json()['spec']['clips'][0]['overlays'][0]['keyframes'][-1]['x']==points[-1]['x']
    changed=client.post(f'/api/creative/projects/{pid}/command',headers=H,json={
      'instruction':'opacidad capa 1 del clip 1 a 0.5','expected_version':1})
    assert changed.status_code==200,changed.text
    assert changed.json()['spec']['clips'][0]['overlays'][0]['opacity']==.5
    assert client.get(exact,headers=H).status_code==409 # versión 2 sin render


def test_v10_safety_and_validation(env):
    client,_=env
    clip=client.post('/api/creative/assets',headers=H,files={'file':('moving.mp4',moving_sample(),'video/mp4')}).json()['id']
    icon=client.post('/api/creative/assets',headers=H,files={'file':('logo.png',layer_image(),'image/png')}).json()['id']
    path=f'/api/creative/assets/{clip}/track'
    bad={'rectangle':[1000,10,30,30],'end':.9}
    assert client.post(path,headers=H,json=bad).status_code==422
    bad={'rectangle':[45,60,30,30],'start':0,'end':25,'width':320,'height':180}
    assert client.post(path,headers=H,json=bad).status_code==422
    spec={'width':320,'height':180,'clips':[{'asset_id':clip,'start':0,'end':1,'overlays':[
          {'asset_id':icon,'from':0,'to':1,'keyframes':[{'t':.9,'x':0,'y':0},{'t':.1,'x':3,'y':5}]}]}]}
    assert client.post('/api/creative/projects',headers=H,json={'kind':'video','name':'bad','spec':spec}).status_code==422
    spec['clips'][0]['overlays'][0]['keyframes']=[{'t':0,'x':1,'y':2},{'t':.7,'x':3,'y':5}]
    good=client.post('/api/creative/projects',headers=H,json={'kind':'video','name':'good','spec':spec})
    assert good.status_code==201,good.text
    pid=good.json()['id']
    assert client.post(f'/api/creative/projects/{pid}/command',headers=H,json={
        'instruction':'mueve capa 1 del clip 1 a x 35 y 30','expected_version':1}).status_code==200
