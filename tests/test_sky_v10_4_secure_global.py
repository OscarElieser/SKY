"""SKY v10.4: encrypted recovery drills, internationalization and access controls."""
from __future__ import annotations
import io,sqlite3,zipfile,hashlib,json
from pathlib import Path
import pytest
from neural_core import sky_secure_backup as s
from neural_core.sky_i18n_audit import report
from neural_core.sky_global_ui import BASE,glossary


def _database(path:Path)->Path:
    with sqlite3.connect(path) as db:
        db.execute('create table users (id integer primary key, name text)')
        db.execute('insert into users(name) values (?)', ('SKY: prueba de recuperación',))
    return path


def test_encrypted_backup_and_real_in_memory_recovery(tmp_path):
    original=_database(tmp_path/'users.sqlite3')
    backup=tmp_path/'private'/'sky-encrypted.skybackup'
    result=s.create_backup(backup,passphrase='secret-long-and-private-1234',sources={'accounts':original})
    assert result['databases']==['accounts']
    assert result['includes_media'] is False
    payload=backup.read_bytes()
    assert payload.startswith(s.MAGIC)
    assert b'SKY: prueba de recuperaci' not in payload
    assert b'users' not in payload
    status=s.verify_backup(backup,passphrase='secret-long-and-private-1234')
    assert status['verified'] and status['live_data_modified'] is False
    assert status['restoration_test']=='in_memory_only'
    with sqlite3.connect(original) as db:
        assert db.execute('select count(*) from users').fetchone()[0]==1


def test_wrong_key_and_tampering_fails_closed(tmp_path):
    source=_database(tmp_path/'a.sqlite3')
    path=tmp_path/'a.skybackup'
    s.create_backup(path,passphrase='a strong secret passphrase',sources={'sky':source})
    with pytest.raises(ValueError,match='autenticar'):
        s.verify_backup(path,passphrase='different very long secret')
    payload=bytearray(path.read_bytes());payload[-20]^=1
    path.write_bytes(payload)
    with pytest.raises(ValueError,match='autenticar'):
        s.verify_backup(path,passphrase='a strong secret passphrase')


def test_backup_refuses_overwrite_missing_sources_symlink(tmp_path):
    source=_database(tmp_path/'db.sqlite3')
    backup=tmp_path/'locked.skybackup'
    with pytest.raises(ValueError):
        s.create_backup(backup,passphrase='short',sources={'database':source})
    with pytest.raises(ValueError):
        s.create_backup(backup,passphrase='valid secret phrase 1234',sources={'database':tmp_path/'absent.db'})
    link=tmp_path/'link.db'; link.symlink_to(source)
    with pytest.raises(ValueError):
        s.create_backup(backup,passphrase='valid secret phrase 1234',sources={'database':link})
    s.create_backup(backup,passphrase='valid secret phrase 1234',sources={'database':source})
    with pytest.raises(FileExistsError):
        s.create_backup(backup,passphrase='valid secret phrase 1234',sources={'database':source})


def test_signed_archive_rejects_unlisted_paths_even_with_correct_key(tmp_path):
    # White-box adversarial archive: valid encryption but invalid manifest contents.
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w') as z:
        z.writestr('manifest.json',json.dumps({'format':'sky-encrypted-sqlite-v1','databases':{'sky':{'path':'db/sky.sqlite3','bytes':0,'sha256':'0'}}}))
        z.writestr('../outside.sqlite3',b'bad')
    path=tmp_path/'tampered.skybackup'
    path.write_bytes(s._encrypt(raw.getvalue(),'safe secret passphrase 1234'))
    with pytest.raises(ValueError):
        s.verify_backup(path,passphrase='safe secret passphrase 1234')


def test_static_i18n_coverage_is_truthful():
    static=Path(__file__).resolve().parents[1]/'metaverse'/'static'
    result=report(static)
    assert result['not_a_full_translation'] is True
    assert result['languages']['en']['translated'] < result['languages']['en']['visible_labels']
    for code in ('fr','pt','ar','zh','ja','sw'):
        assert 'Guardar' in glossary(code)


def test_sensitive_content_is_excluded_from_i18n_script():
    path=Path(__file__).resolve().parents[1]/'metaverse'/'static'/'sky-global-i18n.js'
    code=path.read_text(encoding='utf-8')
    assert '.conversation' in code
    assert '.project-chat' in code
    assert '.answer' in code
    assert 'skyOriginalAriaLabel' in code
    assert 'skyOriginalTitle' in code
    assert 'characterData:true' in code


def test_dependency_and_key_material_not_in_backups(tmp_path):
    path=_database(tmp_path/'db.sqlite3')
    output=tmp_path/'back.skybackup'
    s.create_backup(output,passphrase='password-very-long-and-random',sources={'data':path})
    assert not output.read_bytes().startswith(b'PK')
    assert 'private' not in str(s.verify_backup(output,passphrase='password-very-long-and-random')).lower()


def test_database_snapshot_remains_consistent_with_wal(tmp_path):
    dbfile=tmp_path/'wal.sqlite3'
    with sqlite3.connect(dbfile) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('create table event (message text)')
        db.execute('insert into event values (?)', ('before snapshot',))
    backup=tmp_path/'wal.skybackup'
    s.create_backup(backup,passphrase='a sufficiently strong password',sources={'events':dbfile})
    with sqlite3.connect(dbfile) as db:
        db.execute('insert into event values (?)', ('after snapshot',))
    assert s.verify_backup(backup,passphrase='a sufficiently strong password')['verified']
    # Verify the exact snapshot is unaffected by later changes.
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    decrypted=s._decrypt(backup.read_bytes(),'a sufficiently strong password')
    with zipfile.ZipFile(io.BytesIO(decrypted)) as z:
        with sqlite3.connect(':memory:') as con:
            con.deserialize(z.read('db/events.sqlite3'))
            assert con.execute('select message from event').fetchall()==[('before snapshot',)]


def test_i18n_http_reviewed_phrases_and_private_coverage(tmp_path, monkeypatch):
    from test_sky_v9_7_creative import env,H
    # Unpack the fixture generator normally; isolate client from real user data.
    for client,_ in env.__wrapped__(tmp_path,monkeypatch):
        assert client.get('/api/i18n/coverage').status_code==401
        report_response=client.get('/api/i18n/coverage',headers=H)
        assert report_response.status_code==200
        fr=client.get('/api/i18n/ui',params={'locale':'fr'}).json()
        assert fr['translations']['Enviar mensaje']=='Envoyer un message'
        assert fr['coverage']['complete'] is False
        ar=client.get('/api/i18n/ui',params={'locale':'ar'}).json()
        assert ar['direction']=='rtl'
        break
