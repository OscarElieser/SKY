"""Regression and adversarial tests for SKY v10.5."""
from __future__ import annotations
import io
import json
import sqlite3
import zipfile
import wave
from pathlib import Path
import pytest
from neural_core import sky_recovery_full as recovery
from neural_core import sky_secure_backup as legacy
from neural_core import sky_stt_local as speech
from neural_core.sky_global_ui import glossary, coverage

PASSWORD = 'sky-example-password-2026-keep-private'


def _db(file: Path) -> Path:
    with sqlite3.connect(file) as con:
        con.execute('CREATE TABLE example (value TEXT)')
        con.execute('INSERT INTO example VALUES (?)', ('test - non-public',))
    return file


def test_full_backup_roundtrip_db_and_media_and_offline_restore(tmp_path):
    original = _db(tmp_path/'src.sqlite3')
    media = tmp_path/'media'
    media.mkdir()
    (media/'poster.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'generated-test')
    bundle = tmp_path/'backup.skybackup'
    result = recovery.create(bundle, passphrase=PASSWORD, databases={'example': original},media_roots={'studio': media})
    assert result['media'] == result['sqlite'] == 1
    assert bundle.read_bytes().startswith(legacy.MAGIC)
    assert b'generated-test' not in bundle.read_bytes()
    checked = recovery.verify(bundle, passphrase=PASSWORD)
    assert checked['verified'] and checked['files'] == 2 and not checked['live_data_modified']
    output = tmp_path/'restore-new'
    status = recovery.restore_to_empty(bundle, output, passphrase=PASSWORD)
    assert status['restored'] and not status['live_installation_modified']
    assert (output/'media'/'studio'/'poster.png').read_bytes() == (media/'poster.png').read_bytes()
    with sqlite3.connect(output/'db'/'example.sqlite3') as db:
        assert db.execute('SELECT value FROM example').fetchone()[0] == 'test - non-public'
    with pytest.raises(FileExistsError):
        recovery.restore_to_empty(bundle, output, passphrase=PASSWORD)


def test_full_backup_no_overwrite_and_wrong_password_and_tampering(tmp_path):
    original = _db(tmp_path/'test.sqlite3')
    bundle = tmp_path/'file.skybackup'
    recovery.create(bundle, passphrase=PASSWORD,databases={'db':original},media_roots={})
    with pytest.raises(FileExistsError):
        recovery.create(bundle,passphrase=PASSWORD,databases={'db':original},media_roots={})
    with pytest.raises(ValueError):
        recovery.verify(bundle,passphrase='incorrect-long-password-1234')
    corrupted = bytearray(bundle.read_bytes())
    corrupted[-1] ^= 1
    bundle.write_bytes(corrupted)
    with pytest.raises(ValueError):
        recovery.verify(bundle,passphrase=PASSWORD)


def test_media_allowlist_no_symlinks_secrets(tmp_path):
    root = tmp_path/'assets';root.mkdir()
    (root/'.env').write_text('SECRET=123')
    with pytest.raises(ValueError,match='no permitido|no admitida'):
        recovery._file_list({'studio':root})
    (root/'.env').unlink()
    (root/'file.png').write_bytes(b'PNG')
    (root/'alias.png').symlink_to(root/'file.png')
    with pytest.raises(ValueError,match='Enlaces'):
        recovery._file_list({'studio':root})
    (root/'alias.png').unlink()
    assert recovery._file_list({'studio':root}) == [('media/studio/file.png',root/'file.png')]
    with pytest.raises(ValueError):
        recovery._file_list({'../escape':root})


def test_full_backup_rejects_signed_but_unsafe_zip_names(tmp_path):
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('manifest.json',json.dumps({'format':recovery.FORMAT,'files': {'media/x/../../outside.png': {'bytes':4,'sha256':'0'*64}}}))
        z.writestr('media/x/../../outside.png',b'test')
    encrypted=legacy._encrypt(archive.getvalue(),PASSWORD)
    with pytest.raises(ValueError):
        recovery._bundle(encrypted,PASSWORD)


def test_full_backup_no_restore_into_installation(tmp_path):
    file = _db(tmp_path/'db.sqlite3')
    bundle=tmp_path/'file.skybackup'
    recovery.create(bundle,passphrase=PASSWORD,databases={'db':file},media_roots={})
    root=Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError,match='fuera'):
        recovery.restore_to_empty(bundle,root/'data'/'unwanted-restore',passphrase=PASSWORD)


def test_curated_ui_additions_include_multiple_scripts():
    for lang in ('pt','fr','de','it','ar','zh','ja','sw'):
        tr=glossary(lang)
        assert tr['Nueva imagen'] != 'Nueva imagen'
        assert tr['Reconocimiento de voz'] != 'Reconocimiento de voz'
        assert tr['Privacidad'] != 'Privacidad'
        assert coverage(lang)['complete'] is False
    assert glossary('ar')['Eliminar'] == 'حذف'
    assert glossary('zh')['Crear proyecto'] == '创建项目'


def test_voice_without_local_model_is_explicitly_unavailable(monkeypatch):
    monkeypatch.delenv('SKY_STT_MODEL_DIR',raising=False)
    assert speech.capabilities()['available'] is False
    with pytest.raises(RuntimeError,match='Instalá'):
        speech.transcribe(b'dummy',filename='audio.wav')


def test_audio_conversion_rejects_unsupported_and_accepts_local_wav(tmp_path):
    with pytest.raises(ValueError):
        speech._pcm_mono_16khz(b'text','secrets.env')
    audio=io.BytesIO()
    with wave.open(audio,'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2);stream.setframerate(16000)
        stream.writeframes(b'\0\0'*1600)
    decoded=speech._pcm_mono_16khz(audio.getvalue(),'test.wav')
    with wave.open(io.BytesIO(decoded),'rb') as stream:
        assert stream.getframerate()==16000 and stream.getnchannels()==1
    with pytest.raises(ValueError):
        speech._pcm_mono_16khz(b'\0'*(speech.MAX_INPUT_BYTES+1),'test.wav')


def test_audio_endpoint_auth_protection(tmp_path,monkeypatch):
    from test_sky_v9_7_creative import env,H
    for client,_ in env.__wrapped__(tmp_path,monkeypatch):
        assert client.get('/api/global-media/stt/capabilities').status_code == 401
        response=client.get('/api/global-media/stt/capabilities',headers=H)
        assert response.status_code==200
        assert response.json()['network_access'] is False
        assert client.post('/api/global-media/stt/transcribe',files={'file':('audio.wav',b'data','audio/wav')}).status_code==401
        break


def test_long_audio_is_rejected_not_silently_truncated():
    audio=io.BytesIO()
    with wave.open(audio, 'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000)
        stream.writeframes(b'\0\0'*(16000*61))
    with pytest.raises(ValueError, match='60 segundos'):
        speech._pcm_mono_16khz(audio.getvalue(), 'audio.wav')
