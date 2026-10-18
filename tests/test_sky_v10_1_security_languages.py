"""SKY v10.1: real API, language and security regression tests."""
import io,os
from PIL import Image
from test_sky_v9_7_creative import env,H


def png(color='white',size=(40,40)):
    out=io.BytesIO();Image.new('RGB',size,color).save(out,format='PNG');return out.getvalue()


def upload(client,color='white',name='file.png'):
    response=client.post('/api/creative/assets',headers=H,files={'file':(name,png(color),'image/png')})
    assert response.status_code==201,response.text
    return response.json()['id']


def test_locales_and_fallback_and_scripts(env):
    c,_=env
    langs=c.get('/api/i18n/languages',headers={'Accept-Language':'fr-CA,fr;q=.9,en;q=.2'})
    assert langs.status_code==200
    assert langs.json()['negotiated'].startswith('fr')
    assert len(langs.json()['languages'])>=25
    assert c.get('/api/i18n/phrases?locale=ko').json()['phrases']['hello'].startswith('오늘')
    assert c.get('/api/i18n/phrases?locale=sw').json()['offline'] is False
    assert c.get('/api/i18n/phrases?locale=ar').json()['direction']=='rtl'
    assert c.post('/api/i18n/script-hint',headers=H,json={'text':'こんにちは'}).json()['hint']=='ja'


def test_owner_language_memory_and_external_consent(env,monkeypatch):
    c,tmp=env
    monkeypatch.setenv('SKY_LANGUAGE_PREFS',str(tmp/'pref.json'))
    assert c.get('/api/i18n/preference').status_code==401
    assert c.put('/api/i18n/preference',headers=H,json={'language':'zh-Hant'}).status_code==200
    assert c.get('/api/i18n/preference',headers=H).json()['language']=='zh-hant'
    assert c.put('/api/i18n/preference',headers=H,json={'language':'not_valid!'}).status_code==422
    assert c.post('/api/i18n/translate',headers=H,json={'text':'Hola','target':'en','provider':'gemini','consent':False}).status_code==409
    assert c.post('/api/i18n/translate',headers=H,json={'text':'Hola','target':'en','provider':'none','consent':True}).status_code==409
    assert c.post('/api/i18n/translate',headers=H,json={'text':'Hola','source':'en','target':'en'}).json()['text']=='Hola'
    assert 'Hola' not in (tmp/'pref.json').read_text()


def test_hardening_host_headers_and_body_limit(env):
    c,_=env
    r=c.get('/api/health')
    assert r.headers['X-Content-Type-Options']=='nosniff'
    assert r.headers['X-Frame-Options']=='DENY'
    assert 'frame-ancestors' in r.headers['Content-Security-Policy']
    assert c.get('/api/health',headers={'Host':'evil.example'}).status_code==400
    assert c.get('/api/creative/jobs').status_code==401
    assert c.get('/api/creative/jobs',headers={'Authorization':'Bearer social-token'}).status_code==401
    r=c.post('/api/i18n/script-hint',headers={**H,'Content-Length':str(5*1024*1024), 'Content-Type':'application/json'},content=b'{}')
    assert r.status_code==413


def test_v10_1_global_visual_tracks_and_real_mask_frames(env):
    c,_=env
    base=upload(c,'blue','base.png')
    sticker=upload(c,'red','sticker.png')
    hidden=upload(c,'black','black.png')
    visible=upload(c,'white','white.png')
    spec={'width':320,'height':180,'fps':15,
          'clips':[{'asset_id':base,'start':0,'end':2,'caption':''}],
          'tracks':[{'asset_id':sticker,'width':40,'x':40,'y':30,'from':0,'to':1.9,
                  'mask_keyframes':[{'t':0,'mask_asset_id':hidden},{'t':1.4,'mask_asset_id':visible}]}]}
    r=c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Máscara y pista SKY','spec':spec})
    assert r.status_code==201,r.text
    pid=r.json()['id']
    c.post(f'/api/creative/projects/{pid}/video/render',headers=H)
    from neural_core.sky_creative import run_next_job
    job=run_next_job()
    assert job['status']=='completed',job
    def sample(t):
        frame=c.get(f'/api/creative/projects/{pid}/video/frame?t={t}',headers=H)
        assert frame.status_code==200,frame.text[:300] if frame.status_code!=200 else ''
        with Image.open(io.BytesIO(frame.content)) as im:return im.convert('RGB').getpixel((52,43))
    first=sample(.1);last=sample(1.6)
    assert last[0]>first[0]+70,(first,last)
    p=c.get(f'/api/creative/projects/{pid}/portable',headers=H)
    assert p.status_code==200
    imported=c.post('/api/creative/portable',headers=H,files={'file':('edit.skyzip',p.content,'application/zip')})
    assert imported.status_code==201,imported.text
    assert len(imported.json()['spec']['tracks'][0]['mask_keyframes'])==2


def test_v10_1_mask_rejects_invalid_images_and_timing(env):
    c,_=env
    base=upload(c,'blue')
    mask=upload(c,'white')
    spec={'width':320,'height':180,'clips':[{'asset_id':base,'start':0,'end':2}],
          'tracks':[{'asset_id':base,'width':40,'mask_keyframes':[
              {'t':1.5,'mask_asset_id':mask},{'t':0.5,'mask_asset_id':mask}]}]}
    r=c.post('/api/creative/projects',headers=H,json={'kind':'video','name':'Inválido','spec':spec})
    assert r.status_code==422
    assert not c.get('/api/creative/projects',headers=H).json()


def test_language_switcher_and_editor_javascript_scopes(env):
    c,_=env
    html=c.get('/sky').text
    assert 'sky-language-ui.js' in html
    js=c.get('/static/creative.js').text
    # The v10/v10.1 action handlers must remain inside the existing closure.
    assert js.rstrip().endswith('})();')
    assert js.index("$('v10-track')") < js.rindex('})();')
    assert "$('v101-add-track')" in js
