"""SKY 10.4: encrypted, authenticated and verified *database* snapshots.

Local CLI only.  Does not expose user data over HTTP or write a decrypted
archive.  It does not restore databases into a live installation.  The operator
must separately back up multimedia files and preserve the passphrase offline.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MAGIC = b'SKYBKP1\x00'
MAX_DB_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_DATABASES = 14
ITERATIONS = 2 ** 14


def _cryptography():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise RuntimeError('Instalá cryptography para copias cifradas') from exc
    return AESGCM


def _passphrase(value: str | None = None) -> str:
    secret = value if value is not None else os.environ.get('SKY_BACKUP_PASSPHRASE')
    if not isinstance(secret, str) or len(secret) < 16 or len(secret) > 1024:
        raise ValueError('Configurá SKY_BACKUP_PASSPHRASE de 16 a 1024 caracteres')
    return secret


def database_sources() -> dict[str, Path]:
    """Known application DBs only, not arbitrary filesystem paths."""
    from metaverse.store import path_db as worlds
    from metaverse.community_store import db_path as community
    from neural_core.sky_workbench import _db_path as workbench
    from neural_core.sky_projects import db_path as projects
    from neural_core.sky_workflows import db_path as workflows
    from neural_core.sky_intelligent import db_path as intelligent
    from neural_core.sky_creative import db_path as creative
    root = Path(__file__).resolve().parents[1]
    return {
        'worlds': Path(worlds()), 'community': Path(community()),
        'workbench': Path(workbench()), 'projects': Path(projects()),
        'workflows': Path(workflows()), 'intelligent': Path(intelligent()),
        'creative': Path(creative()),
        'telemetry': Path(os.getenv('SKY_TELEMETRY_DB') or root / 'local_data' / 'sky_telemetry.sqlite3'),
        'evolution': Path(os.getenv('SKY_EVOLUTION_DB') or root / 'data' / 'sky_evolution.sqlite3'),
        'neuralt': root / 'local_data' / 'neuralt.sqlite3',
    }


def _snapshot(source: Path) -> bytes:
    if source.is_symlink() or not source.is_file():
        raise ValueError('La fuente no es un archivo SQLite ordinario')
    if source.stat().st_size > MAX_DB_BYTES:
        raise ValueError('Base SQLite supera el límite de tamaño')
    # Online backup API provides a consistent snapshot while SKY can still read.
    uri = source.resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True, timeout=10) as original:
        with sqlite3.connect(':memory:') as isolated:
            original.backup(isolated, pages=256, sleep=0.1)
            if isolated.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('La base de origen no supera integrity_check')
            raw = bytearray(isolated.serialize())
            # SQLite online backup from WAL mode can serialize pages with WAL
            # header flags (2,2) even though the backed-up database is complete.
            # A standalone restored DB must use rollback-journal flags (1,1).
            if raw[18:20] == b'\x02\x02':
                raw[18:20] = b'\x01\x01'
            content = bytes(raw)
    if len(content) > MAX_DB_BYTES:
        raise ValueError('Instantánea supera el límite de tamaño')
    return content


def _encrypt(plaintext: bytes, passphrase: str) -> bytes:
    aes = _cryptography()
    salt, nonce = os.urandom(16), os.urandom(12)
    key = hashlib.scrypt(passphrase.encode('utf-8'), salt=salt, n=ITERATIONS, r=8, p=1, dklen=32)
    header = MAGIC + salt + nonce
    return header + aes(key).encrypt(nonce, plaintext, header)


def _decrypt(blob: bytes, passphrase: str) -> bytes:
    if len(blob) > MAX_ARCHIVE_BYTES or len(blob) < len(MAGIC) + 16 + 12 + 16 or not blob.startswith(MAGIC):
        raise ValueError('Formato o tamaño de respaldo inválido')
    aes = _cryptography()
    offset = len(MAGIC)
    salt, nonce = blob[offset:offset+16], blob[offset+16:offset+28]
    header = blob[:offset + 28]
    key = hashlib.scrypt(passphrase.encode('utf-8'), salt=salt, n=ITERATIONS, r=8, p=1, dklen=32)
    try:
        return aes(key).decrypt(nonce, blob[offset+28:], header)
    except Exception as exc:
        raise ValueError('No se puede autenticar el respaldo: clave errónea o archivo alterado') from exc


def create_backup(output: str | Path, *, passphrase: str | None = None,
                  sources: dict[str, Path] | None = None) -> dict:
    password = _passphrase(passphrase)
    candidates = sources if sources is not None else database_sources()
    if len(candidates) > MAX_DATABASES:
        raise ValueError('Demasiadas bases')
    entries: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    for name, source in sorted(candidates.items()):
        if not name.isascii() or not name.replace('_', '').isalnum() or name in seen:
            raise ValueError('Nombre de base inválido')
        seen.add(name)
        path = Path(source)
        if path.exists() or path.is_symlink():
            entries.append((name, _snapshot(path)))
    if not entries:
        raise ValueError('No existen bases inicializadas para respaldar')
    manifest = {'format': 'sky-encrypted-sqlite-v1', 'created_at': datetime.now(timezone.utc).isoformat(),
                'scope': 'sqlite_only_not_media', 'databases': {}}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, content in entries:
            filename = 'db/' + name + '.sqlite3'
            z.writestr(filename, content)
            manifest['databases'][name] = {'path': filename, 'bytes': len(content),
                                            'sha256': hashlib.sha256(content).hexdigest()}
        z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    encrypted = _encrypt(stream.getvalue(), password)
    if len(encrypted) > MAX_ARCHIVE_BYTES:
        raise ValueError('El respaldo cifrado supera el límite')
    dest = Path(output)
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        raise FileExistsError('Se prohíbe sobrescribir respaldos anteriores')
    # Exclusive open + restrictive mode, never a decrypted staging file.
    with dest.open('xb') as handle:
        os.chmod(dest, 0o600)
        handle.write(encrypted)
        handle.flush()
        os.fsync(handle.fileno())
    return {'databases': sorted(manifest['databases']), 'file': str(dest),
            'encrypted': True, 'size': len(encrypted), 'includes_media': False}


def verify_backup(path: str | Path, *, passphrase: str | None = None) -> dict:
    password = _passphrase(passphrase)
    file = Path(path)
    if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('Respaldo no válido')
    content = _decrypt(file.read_bytes(), password)
    with zipfile.ZipFile(io.BytesIO(content), 'r') as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or 'manifest.json' not in names or len(names) > MAX_DATABASES + 1:
            raise ValueError('Manifiesto o entradas inválidas')
        if sum(item.file_size for item in archive.infolist()) > MAX_ARCHIVE_BYTES:
            raise ValueError('El contenido expandido supera el límite de respaldo')
        for item in archive.infolist():
            if item.file_size > MAX_DB_BYTES or item.filename.startswith('/') or '..' in Path(item.filename).parts:
                raise ValueError('Entrada de respaldo no válida')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != 'sky-encrypted-sqlite-v1':
            raise ValueError('Versión de respaldo no compatible')
        databases = manifest.get('databases')
        if not isinstance(databases, dict) or not databases:
            raise ValueError('Lista de bases no válida')
        if set(names) != {'manifest.json', *(f'db/{name}.sqlite3' for name in databases)}:
            raise ValueError('Entradas no coinciden con el manifiesto')
        for name, expected in databases.items():
            if not isinstance(name, str) or not name.isascii() or not name.replace('_', '').isalnum():
                raise ValueError('Identificador de base inválido')
            row = archive.getinfo(f'db/{name}.sqlite3')
            if row.file_size > MAX_DB_BYTES: raise ValueError('Base demasiado grande')
            raw = archive.read(row)
            if (hashlib.sha256(raw).hexdigest() != expected['sha256'] or
                len(raw) != expected['bytes'] or expected['path'] != row.filename):
                raise ValueError('Fallo de integridad en base de datos')
            # Real restore *rehearsal* into volatile SQLite only. No live writes.
            with sqlite3.connect(':memory:') as restored:
                restored.deserialize(raw)
                if restored.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('La base recuperada no supera integrity_check')
    return {'verified': True, 'databases': sorted(databases),
            'restoration_test': 'in_memory_only', 'live_data_modified': False,
            'includes_media': False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='SKY: copia SQLite cifrada y restauración de prueba')
    commands = parser.add_subparsers(dest='action', required=True)
    for operation in ('create', 'verify'):
        command = commands.add_parser(operation)
        command.add_argument('--file', required=True, help='Ruta local del respaldo cifrado')
    args = parser.parse_args(argv)
    if args.action == 'create': result = create_backup(args.file)
    else: result = verify_backup(args.file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
