"""SKY v10.8: executable operator controls, not claims about production."""
from __future__ import annotations
import json
import os
import sqlite3
import subprocess
import sys
import wave
from pathlib import Path
import pytest
from neural_core import sky_backup_schedule_v108 as backups
from scripts import container_preflight_v108 as containers
from scripts import benchmark_voice_multilingual_v108 as voice


def fixture_sources(root):
    database=root/'user.sqlite3'
    with sqlite3.connect(database) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('create table items(name text)')
        conn.execute('insert into items values(?)',('archivo privado',))
    folder=root/'photos';folder.mkdir()
    (folder/'picture.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'example-pixel'*50)
    return {'project':database},{'photos':folder}


def test_private_secret_file_reading(tmp_path):
    p=tmp_path/'password';p.write_text('this-is-an-example-test-passphrase-2026\n');p.chmod(0o600)
    assert backups.secret_from_file(p)=='this-is-an-example-test-passphrase-2026'
    p.chmod(0o644)
    if os.name == 'posix':
        with pytest.raises(PermissionError):backups.secret_from_file(p)


def test_secret_symlink_rejected(tmp_path):
    p=tmp_path/'password';p.write_text('this-is-an-example-test-passphrase-2026');p.chmod(0o600)
    link=tmp_path/'link';link.symlink_to(p)
    with pytest.raises(ValueError):backups.secret_from_file(link)


def test_backup_archive_and_isolated_rehearsal(tmp_path):
    db,media=fixture_sources(tmp_path)
    target=tmp_path/'backup'
    s=backups.run_once(target,keep=3,passphrase='this-is-a-local-test-passphrase-2026',databases=db,media_roots=media)
    assert s['verified'] and s['media']==1 and s['databases']==1
    assert (target/s['created']).exists()
    exercise=backups.rehearse_latest(target,passphrase='this-is-a-local-test-passphrase-2026')
    assert exercise['rehearsal_passed'] and exercise['restored_files']==2
    assert not exercise['production_disaster_recovery_certified']
    with sqlite3.connect(db['project']) as conn:
        assert conn.execute('select name from items').fetchone()[0]=='archivo privado'


def test_rotation_only_managed_verified_files(tmp_path):
    db,media=fixture_sources(tmp_path)
    folder=tmp_path/'backups';password='this-is-a-local-test-passphrase-2026'
    runs=[backups.run_once(folder,keep=2,passphrase=password,databases=db,media_roots=media) for _ in range(3)]
    assert len(list(folder.glob('sky-*.skybackup')))==2
    assert (folder/runs[0]['created']).exists() is False
    assert len(runs[2]['rotated'])==1
    (folder/'important.txt').write_text('never delete')
    backups.run_once(folder,keep=2,passphrase=password,databases=db,media_roots=media)
    assert (folder/'important.txt').read_text()=='never delete'


def test_wrong_secret_and_tampered_backup_are_rejected(tmp_path):
    db,media=fixture_sources(tmp_path);password='this-is-a-local-test-passphrase-2026'
    result=backups.run_once(tmp_path/'backups',passphrase=password,databases=db,media_roots=media)
    file=tmp_path/'backups'/result['created']
    with pytest.raises(ValueError):backups.rehearse_latest(file.parent,passphrase='wrong-but-long-enough-password')
    raw=bytearray(file.read_bytes());raw[-2]^=0x01;file.write_bytes(raw)
    with pytest.raises(ValueError):backups.rehearse_latest(file.parent,passphrase=password)


def test_rotation_validation_and_symlink_rejection(tmp_path):
    db,media=fixture_sources(tmp_path)
    with pytest.raises(ValueError):backups.run_once(tmp_path/'b',keep=1,passphrase='longer-than-twenty-characters',databases=db,media_roots=media)
    folder=tmp_path/'real';folder.mkdir(mode=0o700)
    alias=tmp_path/'alias';alias.symlink_to(folder,target_is_directory=True)
    with pytest.raises(ValueError):backups.run_once(alias,passphrase='longer-than-twenty-characters',databases=db,media_roots=media)


def test_static_compose_isolation_checks():
    result=containers.static_audit()
    assert result['static_passed'] and not result['docker_executed']
    assert result['production_certified'] is False


def test_missing_runtime_reports_not_run(monkeypatch):
    monkeypatch.setattr(containers.shutil,'which',lambda command:None)
    status=containers.docker_smoke(runtime=True)
    assert status['runtime_status']=='not_run_docker_missing'
    assert not status['docker_executed']


def test_voice_benchmark_reports_model_not_available(tmp_path):
    folder=tmp_path/'audios';folder.mkdir()
    for name in ('spanish','french'):
        with wave.open(str(folder/f'{name}.wav'),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(bytes(16000))
    manifest=tmp_path/'samples.json'
    manifest.write_text(json.dumps([{'file':'spanish.wav','language':'es','reference':'hola mundo'},
                                    {'file':'french.wav','language':'fr','reference':'bonjour monde'}]),encoding='utf-8')
    result=voice.benchmark(manifest,folder,model_status={'available':False})
    assert not result['tested'] and result['actual_transcriptions']==0
    assert not result['certified']


def test_voice_benchmark_harness_never_prints_transcripts(tmp_path):
    folder=tmp_path/'audios';folder.mkdir()
    for name in ('spanish','french'):
        with wave.open(str(folder/f'{name}.wav'),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(bytes(16000))
    manifest=tmp_path/'samples.json'
    manifest.write_text(json.dumps([{'file':'spanish.wav','language':'es','reference':'hola mundo'},
                                    {'file':'french.wav','language':'fr','reference':'bonjour monde'}]))
    # Fixture-only transcriber tests arithmetic and report privacy; NOT model quality.
    fake=lambda *_args,**kwargs:{'text':'hola mundo' if kwargs['language']=='es' else 'bonjour monde'}
    result=voice.benchmark(manifest,folder,transcriber=fake,model_status={'available':True})
    assert result['all_within_target'] and len(result['results_without_transcripts'])==2
    assert 'hola mundo' not in json.dumps(result)


def test_voice_benchmark_rejects_audio_traversal(tmp_path):
    folder=tmp_path/'audios';folder.mkdir()
    manifest=tmp_path/'samples.json'
    manifest.write_text(json.dumps([{'file':'../token.wav','language':'es','reference':'x'},
                                    {'file':'good.wav','language':'fr','reference':'y'}]))
    with pytest.raises(ValueError):voice.benchmark(manifest,folder)


def test_new_glossary_has_nine_locales():
    from neural_core.sky_global_ui import glossary
    for language in ('en','pt','fr','de','it','ar','zh','ja','sw'):
        assert glossary(language).get('Respaldo automático') and glossary(language)['Respaldo automático']!='Respaldo automático'
