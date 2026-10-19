"""SKY v10.6: offline subprocess STT, encrypted restore drill and honest i18n."""
from __future__ import annotations
import io
import json
import os
import sqlite3
import subprocess
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from neural_core import sky_stt_isolated_v106 as stt
from neural_core import sky_recovery_drill_v106 as drill
from neural_core.sky_i18n_audit import report
from neural_core.sky_global_ui import glossary
from neural_core.sky_languages import normalize
from scripts.validate_local_voice_v106 import word_error_rate

PASSWORD='long-example-password-for-testing-2026'


def _wav():
    output=io.BytesIO()
    with wave.open(output,'wb') as stream:
        stream.setframerate(16000);stream.setnchannels(1);stream.setsampwidth(2)
        stream.writeframes(b'\0\0'*3200)
    return output.getvalue()


def test_voice_is_truthfully_unavailable_without_a_real_model(monkeypatch):
    monkeypatch.delenv('SKY_STT_MODEL_DIR',raising=False)
    caps=stt.capabilities()
    assert caps['available'] is False and caps['real_model_validated'] is False
    assert caps['process_isolated'] is True and caps['os_sandboxed'] is False
    with pytest.raises(RuntimeError,match='no disponible'):
        stt.isolated_transcribe(_wav(),filename='voice.wav')


def test_voice_worker_receives_no_api_keys_and_returns_real_worker_json(monkeypatch):
    from neural_core import sky_stt_local
    monkeypatch.setattr(sky_stt_local,'capabilities',lambda:{'available':True})
    monkeypatch.setattr(sky_stt_local,'model_directory',lambda:Path('/tmp/sky-installed-model'))
    monkeypatch.setattr(sky_stt_local,'_pcm_mono_16khz',lambda body, filename: body)
    monkeypatch.setenv('SKY_API_KEY','should-not-enter-worker')
    monkeypatch.setenv('OPENAI_API_KEY','should-never-enter-worker')
    invoked={}
    def fake_run(command,**kwargs):
        invoked.update(kwargs)
        assert command[0] and command[1:3]==['-m','neural_core.sky_stt_worker_v106']
        assert '--language' in command and command[-1]=='fr'
        assert Path(command[command.index('--file')+1]).exists()
        return SimpleNamespace(returncode=0,stdout=json.dumps({
            'text':'bonjour','detected_language':'fr','segments':[],
        }).encode('utf-8'),stderr=b'')
    monkeypatch.setattr(stt.subprocess,'run',fake_run)
    result=stt.isolated_transcribe(_wav(),filename='test.wav',language='fr-FR')
    assert result['text']=='bonjour' and result['offline'] and result['process_isolated']
    assert invoked['env']['HF_HUB_OFFLINE']=='1'
    assert 'SKY_API_KEY' not in invoked['env']
    assert 'OPENAI_API_KEY' not in invoked['env']


def test_voice_worker_timeout_and_nonzero_fail_closed(monkeypatch):
    from neural_core import sky_stt_local
    monkeypatch.setattr(sky_stt_local,'capabilities',lambda:{'available':True})
    monkeypatch.setattr(sky_stt_local,'model_directory',lambda:Path('/tmp/sky-model'))
    monkeypatch.setattr(sky_stt_local,'_pcm_mono_16khz',lambda body, filename: body)
    def timeout(*a,**k):raise subprocess.TimeoutExpired(cmd='sky',timeout=1)
    monkeypatch.setattr(stt.subprocess,'run',timeout)
    with pytest.raises(RuntimeError,match='tiempo límite'):
        stt.isolated_transcribe(_wav())
    monkeypatch.setattr(stt.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=3,stdout=b'',stderr=b'secret'))
    with pytest.raises(RuntimeError,match='Falló') as exc:
        stt.isolated_transcribe(_wav())
    assert 'secret' not in str(exc.value)


def test_voice_rejects_invalid_language_before_running_model(monkeypatch):
    from neural_core import sky_stt_local
    monkeypatch.setattr(sky_stt_local,'capabilities',lambda:{'available':True})
    with pytest.raises(ValueError):
        stt.isolated_transcribe(_wav(),language='es; rm -rf /')


def test_wer_normalization_and_real_validation_contract():
    assert word_error_rate('Hola mundo','hola mundo')==0
    assert word_error_rate('Hola mundo','hola')==0.5
    assert word_error_rate('Hello world','goodbye universe')==1
    with pytest.raises(ValueError):word_error_rate('','hola')


def test_recovery_drill_real_sqlite_and_media_in_isolation(tmp_path):
    result=drill.run_drill(passphrase=PASSWORD)
    assert result['passed'] and result['encrypted']
    assert result['db_count']==1 and result['media_count']==1
    assert result['source_unchanged'] and not result['complete_system_recovery_certified']
    source_db=tmp_path/'source.sqlite3'
    with sqlite3.connect(source_db) as db:
        db.execute('CREATE TABLE test (value TEXT)')
        db.execute('INSERT INTO test VALUES (?)',('private',))
    media=tmp_path/'media';media.mkdir();(media/'sample.png').write_bytes(b'\x89PNG\r\n\x1a\n'+b'abc'*40)
    before=source_db.read_bytes()
    custom=drill.run_drill(installed=True,passphrase=PASSWORD,
                           database_sources={'db':source_db},media_sources={'studio':media})
    assert custom['passed'] and custom['db_count']==1 and custom['media_count']==1
    assert source_db.read_bytes()==before
    assert (media/'sample.png').exists()


def test_restore_drill_fails_closed_if_wrong_password():
    with pytest.raises(ValueError):drill.run_drill(passphrase='bad')


def test_coverage_increases_but_never_claims_worldwide_completion():
    static=Path(__file__).resolve().parents[1]/'metaverse'/'static'
    numbers=report(static)['languages']
    for locale,minimum in [('pt',95),('fr',95),('ar',90),('zh',90),('ja',90),('sw',78)]:
        assert numbers[locale]['translated']>=minimum
        assert numbers[locale]['translated'] < numbers[locale]['visible_labels']
        assert glossary(locale)['Alto'] not in ('Alto',None)
    assert normalize('ar-MA',strict=True)=='ar-ma'


def test_http_voice_capabilities_still_require_owner(tmp_path,monkeypatch):
    from test_sky_v9_7_creative import env,H
    for client,_ in env.__wrapped__(tmp_path,monkeypatch):
        assert client.get('/api/global-media/stt/capabilities').status_code==401
        authorized=client.get('/api/global-media/stt/capabilities',headers=H)
        assert authorized.status_code==200
        result=authorized.json()
        assert result['process_isolated'] is True
        assert result['os_sandboxed'] is False
        break
