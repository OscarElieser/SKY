"""SKY v10.5: encrypted recovery bundles for SQLite and approved private media.

Local administrator-only CLI; never registers an HTTP route, writes decrypted
media to a public directory or modifies a running installation. Restore is only
into a new, empty destination outside the project directory.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from . import sky_secure_backup as crypto

FORMAT = 'sky-recovery-full-v2'
VALID_BUCKET = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
ALLOWED_MEDIA = frozenset({'.png', '.jpg', '.jpeg', '.webp', '.gif', '.mp4', '.mov', '.webm',
                           '.mkv', '.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.glb'})
MAX_FILE = 80 * 1024 * 1024
MAX_TOTAL = 230 * 1024 * 1024
MAX_COUNT = 2500


def media_sources() -> dict[str, Path]:
    """Only application-managed storage, never arbitrary local_data or .env."""
    from .sky_creative import store_dir
    return {'creative': Path(store_dir()) / 'media'}


def _file_list(roots: dict[str, Path]) -> list[tuple[str, Path]]:
    result = []
    for bucket, root in sorted(roots.items()):
        if not VALID_BUCKET.fullmatch(bucket):
            raise ValueError('Nombre de colección multimedia inválido')
        root = Path(root)
        if not root.exists():
            continue
        if root.is_symlink() or not root.is_dir():
            raise ValueError('La colección multimedia debe ser un directorio real')
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise ValueError('Enlaces simbólicos prohibidos en el respaldo')
            if path.is_dir():
                continue
            if not path.is_file() or path.suffix.lower() not in ALLOWED_MEDIA:
                raise ValueError('Medio no permitido en la colección privada')
            if path.stat().st_size > MAX_FILE:
                raise ValueError('Medio supera el límite individual')
            relative = path.relative_to(root)
            if len(relative.parts) > 6 or any(part.startswith('.') for part in relative.parts):
                raise ValueError('Ruta de medio no admitida')
            result.append((f'media/{bucket}/{relative.as_posix()}', path))
            if len(result) > MAX_COUNT:
                raise ValueError('Demasiados medios para una sola copia')
    return result


def _validate_names(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) > MAX_COUNT + crypto.MAX_DATABASES + 1:
        raise ValueError('Demasiadas entradas de respaldo')
    if len({item.filename for item in infos}) != len(infos):
        raise ValueError('Entradas de respaldo duplicadas')
    total = 0
    for entry in infos:
        name = entry.filename
        parts = Path(name).parts
        if (not name or name.startswith('/') or '\\' in name or '\x00' in name
                or '..' in parts or len(parts) > 9 or entry.is_dir()):
            raise ValueError('Ruta insegura en el respaldo')
        if name != 'manifest.json' and not (name.startswith('db/') or name.startswith('media/')):
            raise ValueError('Entrada fuera de directorio permitido')
        if entry.file_size > MAX_FILE and not name.startswith('db/'):
            raise ValueError('Medio demasiado grande en el respaldo')
        if entry.file_size > crypto.MAX_DB_BYTES and name.startswith('db/'):
            raise ValueError('Base demasiado grande en el respaldo')
        # Unix symlink bit in ZIP external attributes.
        if (entry.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError('Enlaces simbólicos prohibidos')
        total += entry.file_size
        if total > MAX_TOTAL:
            raise ValueError('Respaldo expandido excede el límite')
    return infos


def _bundle(content: bytes, passphrase: str) -> tuple[dict, dict[str, bytes]]:
    if len(content) > crypto.MAX_ARCHIVE_BYTES:
        raise ValueError('Archivo supera el límite')
    decrypted = crypto._decrypt(content, crypto._passphrase(passphrase))
    with zipfile.ZipFile(io.BytesIO(decrypted)) as archive:
        infos = _validate_names(archive)
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != FORMAT:
            raise ValueError('Formato de respaldo no compatible')
        items = manifest.get('files')
        if not isinstance(items, dict) or not items or set(items) != {i.filename for i in infos} - {'manifest.json'}:
            raise ValueError('Archivos y manifiesto no coinciden')
        checked = {}
        for name, info in items.items():
            if not isinstance(info, dict) or not re.fullmatch(r'[a-f0-9]{64}', str(info.get('sha256'))):
                raise ValueError('Hash inválido en manifiesto')
            raw = archive.read(name)
            if len(raw) != info.get('bytes') or hashlib.sha256(raw).hexdigest() != info['sha256']:
                raise ValueError('El archivo no coincide con el manifiesto')
            if name.startswith('db/'):
                with sqlite3.connect(':memory:') as db:
                    db.deserialize(raw)
                    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('SQLite inválido en respaldo')
            elif not name.startswith('media/') or Path(name).suffix.lower() not in ALLOWED_MEDIA:
                raise ValueError('Medio no autorizado')
            checked[name] = raw
        return manifest, checked


def create(output: str | Path, *, passphrase: str | None = None,
           databases: dict[str, Path] | None = None,
           media_roots: dict[str, Path] | None = None) -> dict:
    password = crypto._passphrase(passphrase)
    dbs = crypto.database_sources() if databases is None else databases
    if len(dbs) > crypto.MAX_DATABASES:
        raise ValueError('Demasiadas bases de datos')
    media = _file_list(media_sources() if media_roots is None else media_roots)
    files = {}
    total = 0
    for name, path in sorted(dbs.items()):
        if not VALID_BUCKET.fullmatch(name):
            raise ValueError('Nombre de base inválido')
        p = Path(path)
        if p.exists() or p.is_symlink():
            contents = crypto._snapshot(p)
            files[f'db/{name}.sqlite3'] = contents
            total += len(contents)
    for name, path in media:
        data = path.read_bytes()
        if len(data) > MAX_FILE:
            raise ValueError('Archivo multimedia cambió durante la copia')
        files[name] = data
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError('La copia supera el límite máximo')
    if not files:
        raise ValueError('No hay archivos que respaldar')
    manifest = {'format': FORMAT, 'created_utc': datetime.now(timezone.utc).isoformat(),
                'files': {name: {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
                          for name, blob in sorted(files.items())},
                'scope': 'selected_private_databases_and_media'}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, blob in sorted(files.items()):
            archive.writestr(name, blob)
        archive.writestr('manifest.json', json.dumps(manifest, sort_keys=True, ensure_ascii=False))
    ciphertext = crypto._encrypt(buffer.getvalue(), password)
    if len(ciphertext) > crypto.MAX_ARCHIVE_BYTES:
        raise ValueError('Copia cifrada supera el límite')
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.exists() or target.is_symlink():
        raise FileExistsError('El respaldo existente nunca se sobrescribe')
    with target.open('xb') as handle:
        os.chmod(target, 0o600)
        handle.write(ciphertext)
        handle.flush()
        os.fsync(handle.fileno())
    return {'encrypted': True, 'files': len(files), 'sqlite': sum(n.startswith('db/') for n in files),
            'media': sum(n.startswith('media/') for n in files), 'path': str(target)}


def verify(path: str | Path, *, passphrase: str | None = None) -> dict:
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > crypto.MAX_ARCHIVE_BYTES:
        raise ValueError('Respaldo no válido')
    manifest, files = _bundle(p.read_bytes(), crypto._passphrase(passphrase))
    return {'verified': True, 'files': len(files), 'sqlite': sum(n.startswith('db/') for n in files),
            'media': sum(n.startswith('media/') for n in files),
            'integrity_check': 'sqlite_and_sha256', 'live_data_modified': False,
            'created_utc': manifest['created_utc']}


def restore_to_empty(path: str | Path, destination: str | Path, *, passphrase: str | None = None) -> dict:
    """Explicit offline recovery only. No overwrites or live SKY paths."""
    dest = Path(destination).absolute()
    root = Path(__file__).resolve().parents[1]
    if dest.exists() or dest.is_symlink():
        raise FileExistsError('Elegí una ruta de restauración que no exista')
    if dest.is_relative_to(root) or root.is_relative_to(dest):
        raise ValueError('La restauración debe estar fuera de la instalación activa')
    source = Path(path)
    if source.is_symlink() or source.stat().st_size > crypto.MAX_ARCHIVE_BYTES:
        raise ValueError('Respaldo inválido')
    _, files = _bundle(source.read_bytes(), crypto._passphrase(passphrase))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sky_restore_', dir=dest.parent) as stage:
        folder = Path(stage)
        for name, data in files.items():
            target = folder / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with target.open('xb') as stream:
                os.chmod(target, 0o600)
                stream.write(data)
        if dest.exists() or dest.is_symlink():
            raise FileExistsError('La ruta de restauración se creó mientras se verificaba')
        # Atomic rename on same filesystem. Never follows zip-supplied paths.
        os.rename(folder, dest)
    return {'restored': True, 'destination': str(dest), 'files': len(files),
            'live_installation_modified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description='SKY: copias completas cifradas y restauración offline')
    sub = parser.add_subparsers(dest='command', required=True)
    for action in ('create', 'verify', 'restore'):
        p = sub.add_parser(action)
        p.add_argument('--file', required=True)
        if action == 'restore':
            p.add_argument('--destination', required=True)
    options = parser.parse_args(argv)
    if options.command == 'create': result = create(options.file)
    elif options.command == 'verify': result = verify(options.file)
    else: result = restore_to_empty(options.file, options.destination)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
