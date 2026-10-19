"""SKY v10.6 offline restoration drill, NO active-data modifications.

Synthetic mode is the CI default. Optional --installed uses the current
allowlisted app DBs/media and restores into an isolated temporary folder;
it never copies .env, tokens or private keys.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from . import sky_recovery_full as recovery
from . import sky_secure_backup as backup


def _digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def run_drill(*, installed: bool = False, passphrase: str | None = None,
              database_sources: dict[str, Path] | None = None,
              media_sources: dict[str, Path] | None = None) -> dict:
    """Never mutate existing sources; zero private payload in returned report."""
    # Explicit passphrase for tests; operator password normally via env only.
    secret = backup._passphrase(passphrase)
    with tempfile.TemporaryDirectory(prefix='sky_restore_drill_') as temp:
        sandbox = Path(temp)
        if not installed:
            origin = sandbox / 'source'; origin.mkdir()
            dbpath = origin / 'test.sqlite3'
            with sqlite3.connect(dbpath) as connection:
                connection.execute('CREATE TABLE recovery_probe (id INTEGER PRIMARY KEY, value TEXT)')
                connection.execute('INSERT INTO recovery_probe (value) VALUES (?)', ('private-smoke-test',))
            mediapath = origin / 'assets'; mediapath.mkdir()
            (mediapath / 'example.png').write_bytes(b'\x89PNG\r\n\x1a\nSKY-private-fixture')
            databases = {'example': dbpath}
            media = {'assets': mediapath}
        else:
            databases = backup.database_sources() if database_sources is None else database_sources
            media = recovery.media_sources() if media_sources is None else media_sources
        # Snapshot before backup and after for the source files. Source DB may
        # legitimately change during a live installation; require SKY stopped
        # for installed-mode drills to make hashes meaningful.
        origins = {}
        for name, path in databases.items():
            p = Path(path)
            if p.exists():
                origins[f'db/{name}.sqlite3'] = p
        for name, path in media.items():
            p = Path(path)
            if p.is_dir():
                for asset in p.rglob('*'):
                    if asset.is_file():
                        origins[f'media/{name}/{asset.relative_to(p).as_posix()}'] = asset
        before = {name: _digest(p.read_bytes()) for name, p in origins.items()}
        archive = sandbox / 'encrypted.skybackup'
        created = recovery.create(archive, passphrase=secret, databases=databases,
                                  media_roots=media)
        checked = recovery.verify(archive, passphrase=secret)
        restored = sandbox / 'recovered'
        status = recovery.restore_to_empty(archive, restored, passphrase=secret)
        # Encrypted package never contains the source plaintext media bytes.
        for name, original in origins.items():
            if name.startswith('media/'):
                if original.stat().st_size > 24 and original.read_bytes() in archive.read_bytes():
                    raise AssertionError('El respaldo expuso texto multimedia sin cifrar')
        for name, original in origins.items():
            if name.startswith('db/'):
                with sqlite3.connect(restored / name) as conn:
                    if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise AssertionError('SQLite recuperado inválido')
            elif _digest((restored / name).read_bytes()) != before[name]:
                raise AssertionError('El recurso recuperado difiere del original')
        after = {name: _digest(p.read_bytes()) for name, p in origins.items()}
        if before != after:
            raise AssertionError('Los archivos activos cambiaron durante la prueba')
        if not (checked['verified'] and status['restored'] and created['encrypted']):
            raise AssertionError('Falló el ensayo de restauración')
        return {'passed': True, 'synthetic': not installed, 'encrypted': True,
                'db_count': created['sqlite'], 'media_count': created['media'],
                'integrity_check': True, 'source_unchanged': True,
                'temporary_restore_removed_after_exit': True,
                'complete_system_recovery_certified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description='SKY — restauración cifrada aislada')
    parser.add_argument('--installed', action='store_true', help='Usar datos autorizados con SKY apagado')
    args = parser.parse_args(argv)
    # Never embed a password in an argv parameter or log.
    print(json.dumps(run_drill(installed=args.installed), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
