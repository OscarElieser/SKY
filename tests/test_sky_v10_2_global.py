"""SKY v10.2: system-wide i18n, per-user preferences, TOTP, subtitles, safety."""
from __future__ import annotations
import base64,io,time
import pytest
from test_sky_v9_7_creative import env,H
from test_sky_v10_creative import moving_sample
from neural_core import sky_languages
from neural_core.sky_global_ui import BASE,glossary
from neural_core.sky_subtitles import parse_srt,to_vtt

SRT="""1
00:00:00,200 --> 00:00:00,900
欢迎来到 SKY

2
00:00:01,100 --> 00:00:01,800
مرحبًا بالعالم
"""


def test_catalogue_is_extensible_and_q_weighted(env):
    c,_=env
    r=c.get('/api/i18n/languages',headers={'Accept-Language':'en;q=0.2,ar;q=0.9,fr;q=0'})
    assert r.status_code==200
    data=r.json();assert len(data['languages'])>=80
    assert data['negotiated']=='ar'
    assert data['catalogue_is_not_full_translation'] is True
    for code in ('zh','ar','ja','sw','hi','ru','tr','id','pt'):
        result=c.get('/api/i18n/ui',params={'locale':code}).json()
        assert result['translations']['Espacios']!= 'Espacios'
        assert result['provider_called'] is False
        assert result['private_content_translated'] is False
    assert c.get('/api/i18n/ui?locale=ar').json()['direction']=='rtl'
    assert c.get('/api/i18n/ui?locale=sw').json()['direction']=='ltr'
    assert c.get('/api/i18n/ui?locale=qu').json()['completeness']=='fallback'
    assert c.get('/api/i18n/ui?locale=bad!').status_code==422


def test_integration_js_and_mfa_scripts_exposed_all_pages(env):
    c,_=env
    for path in ('/sky','/studio','/creative','/office','/flows','/community','/world'):
        html=c.get(path).text
        assert 'sky-global-i18n.js' in html,(path,'localizer missing')
        assert 'sky-security-ui.js' in html,(path,'MFA helper missing')
    j=c.get('/static/creative.js').text
    for marker in ('v102-vtt','v102-caption-video','v102-narrate'):
        assert marker in j
    assert j.rstrip().endswith('})();')
    assert 'sky_v102_media' not in c.get('/static/sky-home.js').text


def test_owner_second_factor_blocks_all_private_routes(env,monkeypatch):
    from metaverse import owner_mfa
    monkeypatch.setenv('SKY_OWNER_MFA_SECRET',base64.b32encode(b'01234567890123456789012345678901').decode().rstrip('='))
    owner_mfa.SESSIONS.clear();owner_mfa.FAILURES.clear();owner_mfa.LAST_TOTP_STEP=-1
    c,_=env
    assert c.get('/api/sky/roles',headers=H).status_code==401
    assert c.get('/api/security/owner-mfa/status').json()['required'] is True
    assert c.post('/api/security/owner-mfa/session',json={'code':owner_mfa.code_at(time.time())}).status_code==401
    bad=c.post('/api/security/owner-mfa/session',headers=H,json={'code':'000000'})
    assert bad.status_code==401
    good=c.post('/api/security/owner-mfa/session',headers=H,json={'code':owner_mfa.code_at(time.time())})
    assert good.status_code==200,good.text
    session=good.json()['session']; assert len(session)>30
    headers={**H,'X-SKY-SESSION':session}
    assert c.get('/api/security/owner-mfa/verify',headers=headers).json()['authenticated'] is True
    assert c.get('/api/sky/roles',headers=headers).status_code==200
    # A TOTP code cannot be reused to mint additional sessions immediately.
    duplicate=c.post('/api/security/owner-mfa/session',headers=H,json={'code':owner_mfa.code_at(time.time())})
    assert duplicate.status_code==401
    assert c.post('/api/security/owner-mfa/logout',headers=headers).status_code==200
    assert c.get('/api/sky/roles',headers=headers).status_code==401
    owner_mfa.SESSIONS.clear();owner_mfa.FAILURES.clear();owner_mfa.LAST_TOTP_STEP=-1


def test_distinct_community_user_language_preferences(env,monkeypatch):
    c,tmp=env
    monkeypatch.setenv('SKY_COMMUNITY_DB',str(tmp/'global_users.db'))
    from metaverse import community_store as store
    invite1=store.issue_invite();invite2=store.issue_invite()
    users=[]
    for idx,invite in enumerate((invite1,invite2),1):
        handle='skyuser'+str(idx)
        registered=c.post('/api/community/register',json={'username':handle,'password':'Abc123!abc123!','display_name':handle,'invite':invite})
        assert registered.status_code==201,registered.text
        login=c.post('/api/community/login',json={'username':handle,'password':'Abc123!abc123!'})
        assert login.status_code==200
        users.append({'Authorization':'Bearer '+login.json()['access_token']})
    assert c.put('/api/community/me/language',headers=users[0],json={'language':'ja-JP'}).status_code==200
    assert c.put('/api/community/me/language',headers=users[1],json={'language':'ar'}).status_code==200
    assert c.get('/api/community/me/language',headers=users[0]).json()['language']=='ja-jp'
    assert c.get('/api/community/me/language',headers=users[1]).json()['language']=='ar'
    assert c.get('/api/community/me/language').status_code==401
    assert c.put('/api/community/me/language',headers=users[0],json={'language':'bad!'}).status_code==422


def test_subtitle_convert_and_refuse_external_by_default(env):
    c,_=env
    v=c.post('/api/global-media/subtitles/vtt',json={'srt':SRT,'language':'zh'})
    assert v.status_code==401
    v=c.post('/api/global-media/subtitles/vtt',headers=H,json={'srt':SRT,'language':'zh'})
    assert v.status_code==200,v.text
    assert v.text.startswith('WEBVTT')
    assert '欢迎来到 SKY' in v.text
    assert '00:00:01.100 --> 00:00:01.800' in v.text
    assert c.post('/api/global-media/narration/mp3',headers=H,json={'text':'Hola','language':'es'}).status_code==409
    assert c.post('/api/global-media/narration/mp3',headers=H,json={'text':'Hola','language':'es','provider':'gtts','external_consent':False}).status_code==409
    assert c.post('/api/global-media/subtitles/vtt',headers=H,json={'srt':'bad','language':'es'}).status_code==422
    assert '&lt;script&gt;' in to_vtt('1\n00:00:00,000 --> 00:00:00,500\n<script>\n')


def test_subtitle_render_actual_mp4(env):
    c,_=env
    uploaded=c.post('/api/creative/assets',headers=H,files={'file':('base.mp4',moving_sample(),'video/mp4')})
    assert uploaded.status_code==201,uploaded.text
    aid=uploaded.json()['id']
    rendered=c.post('/api/global-media/subtitles/render',headers=H,json={'video_asset_id':aid,'srt':SRT,'language':'ar'})
    assert rendered.status_code==200,rendered.text[:220] if rendered.status_code!=200 else ''
    assert rendered.headers['content-type'].startswith('video/mp4')
    assert rendered.content[4:8]==b'ftyp'
    assert len(rendered.content)>3000
    assert c.post('/api/global-media/subtitles/render',headers=H,json={'video_asset_id':'../../x','srt':SRT,'language':'ar'}).status_code==422


def test_public_mode_fails_closed_without_mfa_or_redis(monkeypatch):
    from metaverse.deployment_v102 import validate_environment
    monkeypatch.setenv('SKY_DEPLOYMENT_MODE','public')
    monkeypatch.setenv('SKY_TRUSTED_HOSTS','sky.example.test')
    monkeypatch.delenv('SKY_API_KEY',raising=False)
    with pytest.raises(RuntimeError,match='SKY_API_KEY'):validate_environment()
    monkeypatch.setenv('SKY_API_KEY','owner-api-key-for-public-tests-123456789')
    monkeypatch.delenv('SKY_OWNER_MFA_SECRET',raising=False)
    with pytest.raises(RuntimeError,match='MFA'):validate_environment()
    monkeypatch.setenv('SKY_OWNER_MFA_SECRET',base64.b32encode(b'01234567890123456789012345678901').decode().rstrip('='))
    monkeypatch.delenv('SKY_REDIS_URL',raising=False)
    with pytest.raises(RuntimeError,match='Redis'):validate_environment()


def test_public_mode_rejects_reused_owner_secrets(monkeypatch):
    from metaverse.deployment_v102 import validate_environment
    shared=base64.b32encode(b'01234567890123456789012345678901').decode().rstrip('=')
    monkeypatch.setenv('SKY_DEPLOYMENT_MODE','public')
    monkeypatch.setenv('SKY_TRUSTED_HOSTS','sky.example.test')
    monkeypatch.setenv('SKY_API_KEY',shared)
    monkeypatch.setenv('SKY_OWNER_MFA_SECRET',shared)
    with pytest.raises(RuntimeError,match='distintos'):validate_environment()


def test_http_origin_block_and_no_cache(env):
    c,_=env
    wrong=c.post('/api/i18n/script-hint',headers={**H,'Origin':'https://evil.example'},json={'text':'مرحبا'})
    assert wrong.status_code==403
    valid=c.post('/api/i18n/script-hint',headers={**H,'Origin':'http://testserver'},json={'text':'こんにちは'})
    assert valid.status_code==200
    assert 'no-store' in c.get('/api/i18n/preference',headers=H).headers['cache-control']
