"""Offline, fail-closed SKY recovery for an INDEPENDENT machine/container.

An operator transfers a .skybackup file over a trusted channel and supplies
its known SHA-256 out of band. No network connectivity or live overwrite.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from neural_core import sky_recovery_full
from neural_core.sky_backup_schedule_v108 import secret_from_file

HASH = re.compile(r"^[0-9a-f]{64}$")


def archive_sha256(file: Path) -> str:
    if file.is_symlink() or not file.is_file() or file.suffix != '.skybackup':
        raise ValueError('Se requiere un archivo .skybackup regular, sin enlaces')
    if file.stat().st_size > 300 * 1024 * 1024:
        raise ValueError('Archivo excede límite de recuperación')
    digest = hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def recover(archive: Path, destination: Path, key_file: Path, expected_sha256: str) -> dict:
    if not isinstance(expected_sha256, str) or not HASH.fullmatch(expected_sha256):
        raise ValueError('La huella SHA-256 externa es obligatoria')
    if archive_sha256(archive) != expected_sha256:
        raise ValueError('El respaldo cambió durante el traslado')
    secret = secret_from_file(key_file)
    inspected = sky_recovery_full.verify(archive, passphrase=secret)
    if not inspected.get('verified'):
        raise ValueError('La copia no superó integridad')
    result = sky_recovery_full.restore_to_empty(archive, destination, passphrase=secret)
    files = sorted(p for p in destination.rglob('*') if p.is_file())
    if len(files) != inspected['files']:
        raise ValueError('Recuperación incompleta')
    return {'transfer_sha256_verified': True,'authentication_verified': True,
            'restored_files': len(files),'sqlite': inspected['sqlite'],
            'media': inspected['media'],'restored_to_new_directory': True,
            'source_untouched': True,'production_certified': False}


def make_fixture(archive: Path, key_file: Path) -> dict:
    """Generate synthetic SQLite + image in a sealed archive for a separate runner."""
    secret = secret_from_file(key_file)
    with tempfile.TemporaryDirectory(prefix='sky-v109-source-') as folder:
        root=Path(folder)
        db=root/'synthetic.sqlite3'
        con = sqlite3.connect(db)
        try:
            con.execute('CREATE TABLE dummy (name TEXT)')
            con.execute('INSERT INTO dummy VALUES (?)', ('restauracion-sintetica',))
            con.commit()
        finally:
            con.close()
        media=root/'images';media.mkdir()
        # Minimal synthetic 1x1 PNG, never customer data.
        import base64
        (media/'sample.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlI7hQAAAAASUVORK5CYII='))
        created=sky_recovery_full.create(archive,passphrase=secret,
            databases={'synthetic':db},media_roots={'images':media})
    return {'fixture_only':True,'encrypted':created['encrypted'],
            'archive_sha256':archive_sha256(archive),'files':created['files']}


def main(argv=None):
    p=argparse.ArgumentParser(description='SKY independent-host encrypted recovery, no live data')
    p.add_argument('operation',choices=['fixture','restore','sha256'])
    p.add_argument('--file',type=Path,required=True)
    p.add_argument('--key-file',type=Path)
    p.add_argument('--expected-sha256')
    p.add_argument('--destination',type=Path)
    args=p.parse_args(argv)
    if args.operation=='sha256': outcome={'sha256':archive_sha256(args.file)}
    elif args.operation=='fixture':
        if args.key_file is None: p.error('--key-file obligatorio')
        outcome=make_fixture(args.file,args.key_file)
    else:
        if args.key_file is None or args.destination is None or args.expected_sha256 is None:
            p.error('--key-file, --destination y --expected-sha256 obligatorios')
        outcome=recover(args.file,args.destination,args.key_file,args.expected_sha256)
    print(json.dumps(outcome,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
