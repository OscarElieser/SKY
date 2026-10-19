"""SKY v10.3 real localization/voice and access regression tests."""
from __future__ import annotations
import shutil,struct,wave
import pytest
from test_sky_v9_7_creative import env,H
from test_sky_v10_creative import moving_sample
from neural_core.sky_global_ui import glossary,coverage
from neural_core.sky_i18n_audit import report
from neural_core.sky_voice_local import voices,synthesize,select_voice
from pathlib import Path


def test_extended_reviewed_translations_no_false_universal_claim(env):
    c,_=env
    for code in ('pt','fr','ar','zh','ja','sw'):
        r=c.get('/api/i18n/ui',params={'locale':code})
        assert r.status_code==200
        info=r.json()
        assert info['translations'].get('Capas editables')!='Capas editables'
        assert info['coverage']['reviewed_strings']>=40
    r=c.get('/api/i18n/ui',params={'locale':'qu'}).json()
    assert r['completeness']=='fallback'
    assert r['provider_called'] is False
    assert r['private_content_translated'] is False
    assert c.get('/api/i18n/ui?locale=ar').json()['direction']=='rtl'


def test_i18n_audit_private_and_static(env):
    c,_=env
    assert c.get('/api/i18n/coverage').status_code==401
    resp=c.get('/api/i18n/coverage',headers=H)
    assert resp.status_code==200
    data=resp.json()
    assert len(data['pages'])>=7
    assert data['visible_static_labels']>60
    assert data['not_a_full_translation']
    assert data['languages']['fr']['translated']<data['languages']['fr']['visible_labels']
    js=c.get('/static/sky-global-i18n.js').text
    assert 'characterData:true' in js
    assert 'skyOriginalPlaceholder' in js
    assert 'data-sky-i18n-aria' in js


def test_voice_does_not_allow_unauthenticated_requests(env):
    c,_=env
    assert c.get('/api/global-media/voice/local-capabilities').status_code==401
    assert c.post('/api/global-media/voice/local-wav',json={'text':'Hola'}).status_code==401
    assert c.post('/api/global-media/voice/dub-mp4',json={'text':'Hola','video_asset_id':'invalid'}).status_code==401
    assert c.get('/api/global-media/voice/transcription/availability').status_code==401


def test_local_voice_real_wav_and_supported_languages(env):
    if not shutil.which('espeak') and not shutil.which('espeak-ng'):
        pytest.skip('eSpeak no instalado')
    c,_=env
    r=c.get('/api/global-media/voice/local-capabilities',headers=H)
    assert r.json()['available'] is True
    assert r.json()['no_network'] is True
    r=c.post('/api/global-media/voice/local-wav',headers=H,json={'text':'Bonjour, ceci est SKY.','language':'fr'})
    assert r.status_code==200,r.text[:150] if r.status_code!=200 else ''
    assert r.headers['content-type'].startswith('audio/wav')
    assert r.content[:4]==b'RIFF'
    assert len(r.content)>10000
    assert c.post('/api/global-media/voice/local-wav',headers=H,json={'text':'X'*801}).status_code==422
    assert c.post('/api/global-media/voice/local-wav',headers=H,json={'text':'Hello','language':'qu'}).status_code==422


def test_local_video_dubbing_mp4_real(env):
    if not shutil.which('ffmpeg') or not shutil.which('espeak'):
        pytest.skip('FFmpeg/eSpeak no instalados')
    c,_=env
    asset=c.post('/api/creative/assets',headers=H,files={'file':('clip.mp4',moving_sample(),'video/mp4')})
    assert asset.status_code==201,asset.text
    aid=asset.json()['id']
    r=c.post('/api/global-media/voice/dub-mp4',headers=H,json={
        'text':'Bienvenidos a SKY.','language':'es','video_asset_id':aid})
    assert r.status_code==200,r.text[:200] if r.status_code!=200 else ''
    assert r.content[4:8]==b'ftyp'
    assert len(r.content)>1500
    # Source asset must remain available after dub.
    from neural_core import sky_creative
    assert sky_creative.get_asset(aid) is not None


def test_no_cloud_transcription_claim_without_model(env,monkeypatch):
    c,_=env
    monkeypatch.delenv('SKY_WHISPER_LOCAL_MODEL',raising=False)
    r=c.get('/api/global-media/voice/transcription/availability',headers=H)
    assert r.status_code==200
    assert r.json()['available'] is False
