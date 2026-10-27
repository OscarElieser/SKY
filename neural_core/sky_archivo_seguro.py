"""Escritura atómica y bloqueo entre procesos para los JSON de estado de SKY (v12.6).

Por qué: varios procesos de SKY (API, voz manos libres, agente, Streamlit) leen y escriben los mismos archivos de
estado. Con `Path.write_text` un lector podía ver el archivo a medio escribir (JSON inválido → «no escucha») y dos
escritores simultáneos perdían cambios del otro (leer → modificar → escribir sin bloqueo).

  * `escribir_json` escribe en un temporal del MISMO directorio, hace fsync y lo reemplaza con `os.replace`
    (atómico en Windows y POSIX). En Windows reintenta si otro proceso tiene el archivo abierto un instante.
  * `bloqueo(ruta)` es un candado entre procesos (msvcrt en Windows, fcntl en POSIX) sobre un archivo «.lock».
  * `actualizar_json` = bloqueo + leer + modificar + escritura atómica.
Sólo biblioteca estándar.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterator


def leer_json(ruta: Path | str, defecto: Any = None) -> Any:
    try:
        return json.loads(Path(ruta).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return defecto


def escribir_json(ruta: Path | str, datos: Any, *, indent: int | None = None, privado: bool = False) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + ruta.name + '.', suffix='.tmp', dir=str(ruta.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        if privado:
            with contextlib.suppress(OSError):
                os.chmod(tmp, 0o600)
        for intento in range(20):
            try:
                os.replace(tmp, ruta)
                return
            except PermissionError:   # Windows: otro proceso lo tiene abierto en este instante
                if intento == 19:
                    raise
                time.sleep(0.025 * (intento + 1))
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp)


@contextlib.contextmanager
def bloqueo(ruta: Path | str, espera_max: float = 10.0) -> Iterator[None]:
    """Candado exclusivo entre procesos. Lanza TimeoutError si no se obtiene a tiempo."""
    candado = Path(str(ruta) + '.lock')
    candado.parent.mkdir(parents=True, exist_ok=True)
    f = open(candado, 'a+b')
    limite = time.monotonic() + espera_max
    try:
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > limite:
                    raise TimeoutError(f'No pude bloquear {candado.name} en {espera_max:.0f} s')
                time.sleep(0.02)
        yield
    finally:
        try:
            if os.name == 'nt':
                import msvcrt
                f.seek(0)
                with contextlib.suppress(OSError):
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            f.close()


def actualizar_json(ruta: Path | str, cambio: Callable[[Any], Any], defecto: Any = None, *,
                    indent: int | None = None, privado: bool = False) -> Any:
    """Lee, aplica `cambio(datos)` (puede modificar en el lugar o devolver datos nuevos) y escribe, todo bajo candado."""
    with bloqueo(ruta):
        datos = leer_json(ruta, defecto)
        nuevo = cambio(datos)
        datos = datos if nuevo is None else nuevo
        escribir_json(ruta, datos, indent=indent, privado=privado)
        return datos


class CandadoInstancia:
    """Candado de proceso único que dura toda la vida del proceso (supervisor de SKY).
    Lo libera el sistema operativo si el proceso muere: no deja candados huérfanos."""

    def __init__(self, ruta: Path | str):
        self.ruta = Path(ruta)
        self._f = None

    def adquirir(self) -> bool:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.ruta, 'a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False
        self._f = f
        return True

    def ocupado(self) -> bool:
        """True si OTRO proceso tiene el candado (sin quedárselo)."""
        if self._f is not None:
            return False
        if self.adquirir():
            self.liberar()
            return False
        return True

    def liberar(self) -> None:
        if self._f is None:
            return
        try:
            if os.name == 'nt':
                import msvcrt
                self._f.seek(0)
                with contextlib.suppress(OSError):
                    msvcrt.locking(self._f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._f.fileno(), fcntl.LOCK_UN)
        finally:
            self._f.close()
            self._f = None
