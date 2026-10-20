"""SKY v10.7 disaster-recovery EXERCISE with no production-side writes.

This checks recovery integrity, handling of a tampered archive and wrong keys.
It does NOT validate cloud storage availability, DNS, DNS failover or HA.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
from neural_core import sky_recovery_full as recovery


def exercise(*, passphrase: str) -> dict:
    if len(passphrase) < 16:
        raise ValueError('Contraseña de ensayo demasiado corta')
    with tempfile.TemporaryDirectory(prefix='sky_dr_v107_') as tmp:
        root=Path(tmp)
        db=root/'database.sqlite3'
        conn = sqlite3.connect(db)
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('CREATE TABLE fixtures (value TEXT)')
            conn.execute('INSERT INTO fixtures VALUES (?)',('data-never-shared',))
            conn.commit()
        finally:
            conn.close()
        assets=root/'assets';assets.mkdir()
        (assets/'photo.png').write_bytes(b'\x89PNG\r\n\x1a\n'+b'private-asset-content'*20)
        before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [db, assets/'photo.png']}
        archive=root/'sealed.skybackup'
        recovery.create(archive, passphrase=passphrase, databases={'demo':db}, media_roots={'studio':assets})
        valid=recovery.verify(archive, passphrase=passphrase)
        recovered=root/'restored'
        recovery.restore_to_empty(archive,recovered,passphrase=passphrase)
        conn = sqlite3.connect(recovered/'db'/'demo.sqlite3')
        try:
            assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert conn.execute('SELECT COUNT(*) FROM fixtures').fetchone()[0]==1
        finally:
            conn.close()
        assert (recovered/'media'/'studio'/'photo.png').read_bytes()==(assets/'photo.png').read_bytes()
        wrong_key_rejected=False
        try:recovery.verify(archive,passphrase=passphrase+'wrong')
        except ValueError:wrong_key_rejected=True
        corrupted=root/'tampered.skybackup'
        blob=bytearray(archive.read_bytes());blob[-1]^=0x01;corrupted.write_bytes(blob)
        tampering_rejected=False
        try:recovery.verify(corrupted,passphrase=passphrase)
        except ValueError:tampering_rejected=True
        unchanged={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [db,assets/'photo.png']}==before
        assert valid['verified'] and wrong_key_rejected and tampering_rejected and unchanged
        return {'passed':True, 'scope':'synthetic_sqlite_wal_and_media',
                'restored_into_new_directory':True,'live_data_unchanged':unchanged,
                'invalid_password_rejected':wrong_key_rejected,
                'tampering_rejected':tampering_rejected,
                'sqlite_integrity_check':'ok',
                'production_disaster_recovery_certified':False,
                'network_or_host_failover_tested':False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    import os
    secret=os.getenv('SKY_BACKUP_PASSPHRASE')
    if not secret:raise RuntimeError('Configurá SKY_BACKUP_PASSPHRASE fuera del código')
    status=exercise(passphrase=secret)
    if args.report:
        if args.report.exists():raise FileExistsError('No sobrescribir informes de recuperación')
        args.report.write_text(json.dumps(status,indent=2),encoding='utf-8')
    print(json.dumps(status,ensure_ascii=False))

if __name__=='__main__':main()
