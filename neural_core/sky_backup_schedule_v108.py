"""SKY v10.8: encrypted backup rotation, verification and offline recovery rehearsals.

Owner-operated CLI only. No HTTP endpoints, plaintext backups, or background
scheduling inside the web server. Use an external timer (systemd/Task Scheduler).
This is NOT disaster-recovery certification for a production deployment.
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import re
import secrets
import stat
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from . import sky_recovery_full as recovery

BACKUP_PATTERN = re.compile(r'^sky-\d{8}T\d{6}Z-[a-f0-9]{12}\.skybackup$')


def secret_from_file(path: str | Path | None = None) -> str:
    """Obtain backup key from a private, non-symlinked regular file."""
    raw = path if path is not None else os.environ.get('SKY_BACKUP_PASSPHRASE_FILE')
    if not raw:
        raise RuntimeError('SKY_BACKUP_PASSPHRASE_FILE debe apuntar a un archivo privado')
    source = Path(raw)
    if source.is_symlink() or not source.is_file():
        raise ValueError('La clave debe estar en un archivo ordinario no enlazado')
    if os.name == 'posix' and source.stat().st_mode & 0o077:
        raise PermissionError('Los permisos de la clave deben ser 0600 o más restrictivos')
    if source.stat().st_size > 2048:
        raise ValueError('El archivo secreto es demasiado grande')
    # O_NOFOLLOW blocks symlink replacement between validation and open (POSIX).
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(source, flags)
    with os.fdopen(fd, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError('Archivo de clave inválido')
        value = handle.read(2049).decode('utf-8').rstrip('\r\n')
    if '\n' in value or '\r' in value or not (20 <= len(value) <= 1024):
        raise ValueError('La frase de respaldo debe tener entre 20 y 1024 caracteres')
    return value


def _safe_directory(directory: str | Path, *, create: bool) -> Path:
    root = Path(directory).absolute()
    if root.is_symlink():
        raise ValueError('No se admite directorio enlazado para respaldos')
    if create:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not root.is_dir():
        raise ValueError('No existe el directorio de respaldos')
    if os.name == 'posix' and root.stat().st_mode & 0o077:
        raise PermissionError('El directorio de respaldos debe tener permisos 0700')
    # The managed directory itself must not be a symlink; backups inside are checked.
    return root


@contextlib.contextmanager
def _lock_backup(root: Path):
    """Non-blocking lock for local operations; fail rather than race."""
    if os.name != 'posix':
        raise RuntimeError('Planificación automática verificada solo en POSIX; usar CLI manual')
    import fcntl
    target = root / '.sky-backup.lock'
    descriptor = os.open(target, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError('Archivo de bloqueo inválido')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Ya existe otro respaldo en ejecución') from exc
        yield
    finally:
        os.close(descriptor)


def _archive_files(root: Path) -> list[Path]:
    found = []
    for file in root.iterdir():
        if file.is_symlink():
            if BACKUP_PATTERN.fullmatch(file.name):
                raise ValueError('Respaldo enlazado: revisión manual necesaria')
            continue
        if BACKUP_PATTERN.fullmatch(file.name) and file.is_file():
            found.append(file)
    return sorted(found, key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)


def run_once(directory: str | Path, *, keep: int = 7, passphrase: str | None = None,
             databases: dict[str, Path] | None = None,
             media_roots: dict[str, Path] | None = None) -> dict:
    """Create+verify encrypted snapshot, then rotate only managed verified backups.

    Caller may supply fixture databases/media for testing; production CLI leaves
    them unset and uses only trusted application-managed sources.
    """
    if type(keep) is not int or not 2 <= keep <= 90:
        raise ValueError('Retención permitida: entre 2 y 90 copias')
    password = passphrase if passphrase is not None else secret_from_file()
    root = _safe_directory(directory, create=True)
    with _lock_backup(root):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        filename = f'sky-{stamp}-{secrets.token_hex(6)}.skybackup'
        final = root / filename
        partial = root / ('.partial-' + filename)
        try:
            result = recovery.create(partial, passphrase=password,
                                     databases=databases, media_roots=media_roots)
            check = recovery.verify(partial, passphrase=password)
            if not check['verified'] or check['files'] != result['files']:
                raise ValueError('La copia no coincide con la verificación')
            os.rename(partial, final)
            if os.name == 'posix':
                dirfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
                try:os.fsync(dirfd)
                finally:os.close(dirfd)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
        # Never delete an archive that fails authentication, or a non-managed file.
        archives = _archive_files(root)
        deleted = []
        for old in archives[keep:]:
            try:
                if recovery.verify(old, passphrase=password)['verified']:
                    old.unlink()
                    deleted.append(old.name)
            except (ValueError, OSError):
                continue
        return {'created': filename, 'encrypted': True, 'verified': True,
                'files': check['files'], 'databases': check['sqlite'],
                'media': check['media'], 'rotated': deleted,
                'remaining': len(_archive_files(root)),
                'scope': 'local_managed_private_data', 'production_certified': False}


def rehearse_latest(directory: str | Path, *, passphrase: str | None = None,
                    max_rpo_hours: float = 48.0) -> dict:
    """Verify and restore most recent archive into a temporary unrelated folder.

    The RPO estimate comes from backup age, not a measured failure interval.
    """
    if not 0 < max_rpo_hours <= 720:
        raise ValueError('Objetivo RPO inválido')
    password = passphrase if passphrase is not None else secret_from_file()
    root = _safe_directory(directory, create=False)
    with _lock_backup(root):
        files = _archive_files(root)
        if not files:
            raise FileNotFoundError('No existen respaldos administrados')
        candidate = files[0]
        started = time.monotonic()
        before_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
        info = recovery.verify(candidate, passphrase=password)
        with tempfile.TemporaryDirectory(prefix='sky-v108-rehearsal-') as work:
            target = Path(work) / 'recovered'
            restored = recovery.restore_to_empty(candidate, target, passphrase=password)
            # Verify actual byte identity against the authenticated bundle.
            _, manifest = recovery._bundle(candidate.read_bytes(), password)
            if {str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in target.rglob('*') if p.is_file()} != {
                name:hashlib.sha256(data).hexdigest() for name,data in manifest.items()}:
                raise ValueError('Restauración incompleta o modificada')
            count = restored['files']
        elapsed = round(time.monotonic() - started, 3)
        age = round(max(0, (time.time() - candidate.stat().st_mtime) / 3600), 3)
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != before_sha:
            raise ValueError('Respaldo alterado durante el ensayo')
        return {'rehearsal_passed':True,'restored_files':count,
                'rto_seconds_measured':elapsed,'backup_age_hours':age,
                'rpo_target_hours':max_rpo_hours,'rpo_age_within_target':age<=max_rpo_hours,
                'backup':candidate.name,'source_untouched':True,
                'uses_synthetic_or_local_data_only':True,
                'production_disaster_recovery_certified':False}
