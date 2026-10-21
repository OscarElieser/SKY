"""Notas locales del propietario, aisladas de sus otros documentos.

SOLO se permiten notas .txt con nombres simples dentro de ~/.neuralt/notes.
Toda operación de escritura exige autorización explícita en la UI + opt-in local.
La eliminación mueve el archivo a .trash, sin borrado permanente.
"""
from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

MAX_CHARS = 12_000
MAX_FILE_BYTES = 64_000
NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
NOTE_ACTIONS = frozenset({"note_create", "note_append", "note_trash"})


def notes_root() -> Path:
    root = Path.home() / ".neuralt" / "notes"
    if root.is_symlink():
        raise RuntimeError("La carpeta de notas no puede ser un enlace simbólico.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("Carpeta de notas no válida.")
    return root


def _note_path(name: str) -> Path:
    if not isinstance(name, str) or NAME_PATTERN.fullmatch(name) is None:
        raise ValueError("El nombre debe tener entre 1 y 64 letras, números, guiones o guiones bajos.")
    path = notes_root() / (name + ".txt")
    if path.is_symlink():
        raise ValueError("No se permiten enlaces simbólicos.")
    return path


def _content(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_CHARS or "\x00" in value:
        raise ValueError("El texto debe tener entre 1 y 12 000 caracteres válidos.")
    return value


def run_note_action(action: str, params: dict) -> dict:
    if action not in NOTE_ACTIONS or not isinstance(params, dict):
        raise ValueError("Operación de notas inválida.")
    if os.getenv("SKY_NOTES_ENABLED", "0") != "1":
        raise PermissionError("Activá SKY_NOTES_ENABLED=1 en el equipo propietario.")
    if params.get("confirmed") is not True:
        raise PermissionError("Confirmación individual obligatoria desde el panel.")
    path = _note_path(params.get("name", ""))
    if action == "note_create":
        text = _content(params.get("content", ""))
        try:
            with path.open("x", encoding="utf-8") as f:
                f.write(text + "\n")
        except FileExistsError as exc:
            raise ValueError("La nota ya existe; no se sobrescribió.") from exc
        return {"ok": True, "message": "Nota nueva creada.", "note": path.name}
    if not path.is_file() or path.is_symlink():
        raise ValueError("No existe una nota válida con ese nombre.")
    if action == "note_append":
        text = _content(params.get("content", ""))
        if path.stat().st_size + len(text.encode("utf-8")) + 2 > MAX_FILE_BYTES:
            raise ValueError("La nota llegó a su límite seguro de 64 KB.")
        with path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")
        return {"ok": True, "message": "Texto agregado sin sustituir contenido previo.", "note": path.name}
    trash = notes_root() / ".trash"
    if trash.is_symlink():
        raise RuntimeError("Papelera no válida.")
    trash.mkdir(mode=0o700, exist_ok=True)
    name = path.stem + "-" + secrets.token_hex(8) + ".txt"
    path.rename(trash / name)
    return {"ok": True, "message": "Nota trasladada a papelera recuperable.", "note": path.name}
