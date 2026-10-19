"""Read administrator credentials from environment OR mounted secret files.

Never log or return values to HTTP routes. A *_FILE setting takes precedence
only when the inline variable is absent; configuring both fails closed.
"""
from __future__ import annotations
import os
from pathlib import Path


def get_secret(name: str, *, max_bytes: int = 4096) -> str:
    inline = os.environ.get(name, '').strip()
    file_name = os.environ.get(name + '_FILE', '').strip()
    if inline and file_name:
        raise RuntimeError(f'Definí {name} o {name}_FILE, nunca ambos')
    if not file_name:
        return inline
    path = Path(file_name)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise RuntimeError(f'Archivo secreto inválido para {name}')
    stat = path.stat()
    if stat.st_size > max_bytes or not stat.st_size:
        raise RuntimeError(f'Tamaño de secreto inválido para {name}')
    try:
        value = path.read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f'No se pudo leer el secreto {name}') from exc
    if not value or '\x00' in value or '\n' in value:
        raise RuntimeError(f'Contenido secreto inválido para {name}')
    return value
