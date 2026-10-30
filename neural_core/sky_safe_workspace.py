"""Espacio de archivos privado de SKY, portable en Windows/Linux y accesible por API.

No permite acceder a Documentos, Escritorio, Downloads ni rutas del SO.
Operaciones de un solo archivo, sin paths, enlaces, ejecución o borrado permanente.
El recibo de consentimiento vive en sky_approvals y se consume una sola vez.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
_LOCK = threading.RLock()
MAX_FILE = 12 * 1024 * 1024
MAX_TEXT = 120_000
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,90}$")
ID = re.compile(r"^[a-f0-9]{32}$")
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".py", ".html"}
DOC_EXT = {".docx", ".xlsx", ".pptx", ".pdf"}
EXTS = TEXT_EXT | DOC_EXT
OPS = {"create", "replace", "append", "rename", "trash", "restore"}
_ALLOWED = {"op", "name", "text", "new_name", "trash_id", "document"}
_EMPTY = "absent"


class WorkspaceError(ValueError):
    pass


class WorkspaceConflict(RuntimeError):
    pass


def _root() -> Path:
    path = Path(os.getenv("SKY_SAFE_WORKSPACE_ROOT") or ROOT / "local_data" / "sky_safe_workspace")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise WorkspaceError("Directorio de trabajo no seguro.")
    return path


def _name(value: str) -> str:
    if not isinstance(value, str) or not NAME.fullmatch(value) or value in (".", ".."):
        raise WorkspaceError("Usá un nombre de archivo simple, sin carpetas ni rutas.")
    if Path(value).suffix.lower() not in EXTS:
        raise WorkspaceError("Extensión de archivo no admitida.")
    if value.startswith("."):
        raise WorkspaceError("No se admiten nombres ocultos.")
    return value


def _safe_file(path: Path):
    try:
        meta = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or meta.st_size > MAX_FILE:
        raise WorkspaceError("Archivo inseguro o superior al límite.")
    return meta


def _hash(path: Path) -> str:
    if _safe_file(path) is None:
        return _EMPTY
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(131072), b""):
            digest.update(block)
    return digest.hexdigest()


def _db():
    folder = _root()
    conn = sqlite3.connect(folder / ".sky_workspace_audit.sqlite3", timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("""CREATE TABLE IF NOT EXISTS trash (
        id TEXT PRIMARY KEY, original TEXT NOT NULL, sha TEXT NOT NULL,
        bytes INTEGER NOT NULL, at INTEGER NOT NULL, restored INTEGER DEFAULT 0)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL,
        filename_hash TEXT NOT NULL, result TEXT NOT NULL,
        size INTEGER NOT NULL, at INTEGER NOT NULL)""")
    conn.commit()
    return conn


def _audit(db, action, name, result, size=0):
    # Ni texto ni nombre del archivo se guardan en este registro.
    hashed = hashlib.sha256(name.encode("utf-8")).hexdigest()
    db.execute("INSERT INTO actions(action,filename_hash,result,size,at) VALUES(?,?,?,?,?)",
               (action, hashed, result, size, int(time.time())))


def _trash_dir():
    p = _root() / ".trash"
    p.mkdir(mode=0o700, exist_ok=True)
    if p.is_symlink() or not p.is_dir():
        raise WorkspaceError("Papelera insegura.")
    return p


def _validate(spec: dict) -> dict:
    if not isinstance(spec, dict) or set(spec) - _ALLOWED:
        raise WorkspaceError("Especificación no autorizada.")
    op = spec.get("op")
    if not isinstance(op, str) or op not in OPS:
        raise WorkspaceError("Operación fuera del catálogo.")
    name = _name(spec.get("name"))
    normalized = {"op": op, "name": name}
    accepted = {"op", "name"}
    if op in {"create", "replace", "append"}:
        accepted |= {"text", "document"}
        if op == "append" or Path(name).suffix.lower() in TEXT_EXT:
            if spec.get("document") is not None:
                raise WorkspaceError("Especificación incompatible con archivo de texto.")
            content = spec.get("text")
            if not isinstance(content, str) or not content or len(content.encode("utf-8")) > MAX_TEXT:
                raise WorkspaceError("Texto vacío o demasiado extenso.")
            if "\x00" in content:
                raise WorkspaceError("Caracter NUL no admitido.")
            if Path(name).suffix.lower() == ".json":
                if op == "append":
                    raise WorkspaceError("No se añade texto libre a JSON.")
                try:
                    json.loads(content, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                except (ValueError, RecursionError) as exc:
                    raise WorkspaceError("JSON inválido.") from exc
            normalized["text"] = content
        else:
            if op == "append":
                raise WorkspaceError("Solo se puede añadir texto a archivos de texto.")
            doc = spec.get("document")
            if not isinstance(doc, dict) or set(doc) - {"kind","title","content","headers","rows","csv","template","ai_provider"}:
                raise WorkspaceError("Documento estructurado inválido.")
            try:
                length = len(json.dumps(doc, ensure_ascii=False, allow_nan=False))
            except (TypeError, ValueError, OverflowError) as exc:
                raise WorkspaceError("Datos de documento inválidos.") from exc
            if length > 145_000:
                raise WorkspaceError("Documento estructurado demasiado extenso.")
            if str(doc.get("kind", "")).lower() != Path(name).suffix[1:].lower():
                raise WorkspaceError("Tipo de documento diferente de su extensión.")
            if not isinstance(doc.get("content", ""), str) or not doc.get("content", "").strip():
                # XLSX con filas reales puede no contener contenido narrativo.
                if not (doc.get("rows") or doc.get("csv")):
                    raise WorkspaceError("El documento necesita contenido real.")
            if doc.get("ai_provider") not in (None, "none", ""):
                raise WorkspaceError("No se permite envío implícito a una IA externa.")
            normalized["document"] = doc
    elif op == "rename":
        accepted.add("new_name")
        if spec.get("new_name") is None:
            raise WorkspaceError("Falta el nuevo nombre.")
        normalized["new_name"] = _name(spec["new_name"])
        if normalized["new_name"] == name:
            raise WorkspaceError("Nombre nuevo igual al anterior.")
        if Path(normalized["new_name"]).suffix.lower() != Path(name).suffix.lower():
            raise WorkspaceError("No se cambia el tipo de archivo al renombrarlo.")
    elif op == "restore":
        accepted.add("trash_id")
        ident = spec.get("trash_id")
        if not isinstance(ident, str) or not ID.fullmatch(ident):
            raise WorkspaceError("Identificador de papelera inválido.")
        normalized["trash_id"] = ident
    if set(spec) - accepted:
        raise WorkspaceError("No se permiten campos inesperados para la operación.")
    try:
        raw = json.dumps(normalized, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise WorkspaceError("Los datos del documento deben ser JSON válido.") from exc
    if len(raw) > 160_000:
        raise WorkspaceError("Solicitud excesiva.")
    return normalized


def _render(spec):
    if "text" in spec:
        return spec["text"].encode("utf-8")
    from .sky_office import create_document
    data = create_document(spec["document"]).data
    if not data or len(data) > MAX_FILE:
        raise WorkspaceError("Documento generado vacío o demasiado grande.")
    return data


def _preview(spec):
    folder = _root()
    op, name = spec["op"], spec["name"]
    target = folder / name
    original = _hash(target)
    other = None
    if op == "create" and original != _EMPTY:
        raise WorkspaceConflict("Ya existe este archivo.")
    if op in {"replace", "append", "rename", "trash"} and original == _EMPTY:
        raise WorkspaceConflict("El archivo no existe.")
    if op == "append" and Path(name).suffix.lower() not in TEXT_EXT:
        raise WorkspaceError("Añadir solo se permite para archivos de texto.")
    if op == "rename":
        other = _hash(folder / spec["new_name"])
        if other != _EMPTY:
            raise WorkspaceConflict("El destino ya existe.")
    if op == "restore":
        if original != _EMPTY:
            raise WorkspaceConflict("El destino ya existe.")
        with closing(_db()) as db:
            row = db.execute("SELECT * FROM trash WHERE id=? AND restored=0",
                             (spec["trash_id"],)).fetchone()
        if row is None or row["original"] != name:
            raise WorkspaceConflict("Elemento no encontrado en papelera.")
        if _hash(_trash_dir() / row["id"]) != row["sha"]:
            raise WorkspaceConflict("El archivo de papelera cambió.")
        other = row["sha"]
    new_size = 0
    if op in {"create", "replace", "append"}:
        data = _render(spec)
        new_size = len(data)
        if op == "append":
            old_size = target.stat().st_size
            if old_size + new_size > MAX_FILE:
                raise WorkspaceError("El archivo final supera el tamaño máximo.")
            # Exigir UTF-8 previo válido para no corromper archivos binarios disfrazados.
            target.read_text(encoding="utf-8")
        if new_size > MAX_FILE:
            raise WorkspaceError("Archivo demasiado grande.")
    return {"op": op, "name": name, "expected_sha": original,
            "destination_state": other, "bytes_to_write": new_size,
            "requires_confirmation": True, "physical_device_verified": False,
            "spec_digest": hashlib.sha256(json.dumps(spec, sort_keys=True,
                ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()}


def preview(spec):
    """No cambia archivos de usuario. El comprobante real lo emite la API."""
    s = _validate(spec)
    with _LOCK:
        return _preview(s)


def _write(path: Path, data: bytes, overwrite: bool):
    root = _root()
    tmp = None
    try:
        fd, filename = tempfile.mkstemp(prefix=".sky-write-", dir=root)
        tmp = Path(filename)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if not overwrite:
            # hard-link con semántica exclusiva: jamás sobreescribe si otro
            # proceso crea el archivo después del preview.
            try:
                os.link(tmp, path)
            except FileExistsError as exc:
                raise WorkspaceConflict("El nombre ya está ocupado.") from exc
            tmp.unlink()
            return _hash(path)
        os.replace(tmp, path)
        return _hash(path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def commit(spec, expected_sha: str, destination_state: str | None):
    """Usar sólo DESPUÉS de consumir token de aprobación bajo el mismo lock API."""
    s = _validate(spec)
    with _LOCK:
        actual = _preview(s)
        if actual["expected_sha"] != expected_sha or actual["destination_state"] != destination_state:
            raise WorkspaceConflict("El archivo cambió después de la vista previa.")
        folder = _root()
        op, name = s["op"], s["name"]
        target = folder / name
        with closing(_db()) as db:
            with db:
                result = {}
                if op in {"create", "replace", "append"}:
                    blob = _render(s)
                    if op == "append":
                        blob = target.read_bytes() + blob
                    if len(blob) > MAX_FILE:
                        raise WorkspaceError("Archivo final demasiado grande.")
                    digest = _write(target, blob, overwrite=op != "create")
                    if digest != hashlib.sha256(blob).hexdigest():
                        raise WorkspaceConflict("El archivo escrito no superó la comprobación.")
                    result = {"sha256": digest, "bytes": len(blob),
                              "download": "/api/sky/safe-files/download/" + name}
                elif op == "rename":
                    os.rename(target, folder / s["new_name"])
                    result = {"name": s["new_name"], "sha256": _hash(folder / s["new_name"])}
                elif op == "trash":
                    dest = _trash_dir()
                    ident = secrets.token_hex(16)
                    os.rename(target, dest / ident)
                    db.execute("INSERT INTO trash(id,original,sha,bytes,at) VALUES(?,?,?,?,?)",
                               (ident, name, expected_sha, (dest / ident).stat().st_size, int(time.time())))
                    result = {"trash_id": ident, "recoverable": True}
                else:
                    origin = _trash_dir() / s["trash_id"]
                    os.rename(origin, target)
                    db.execute("UPDATE trash SET restored=1 WHERE id=? AND restored=0", (s["trash_id"],))
                    result = {"sha256": _hash(target), "restored": True}
                _audit(db, op, name, "verified", int(result.get("bytes", 0)))
        return {"ok": True, "operation": op, "name": name,
                "result": result, "verified_after_write": True,
                "external_device_action": False}


def files():
    with _LOCK:
        items = []
        for p in sorted(_root().iterdir(), key=lambda v:v.name.casefold()):
            if p.name.startswith(".") or p.suffix.lower() not in EXTS:
                continue
            if _safe_file(p) is None:
                continue
            items.append({"name": p.name, "bytes": p.stat().st_size, "sha256": _hash(p)})
        return {"files": items[:250], "workspace_only": True, "all_os_files_accessible": False}


def trash_items():
    with _LOCK, closing(_db()) as db:
        rows = db.execute("SELECT id,original,sha,bytes,at FROM trash WHERE restored=0 ORDER BY at DESC LIMIT 250").fetchall()
        return {"items": [dict(row) for row in rows], "permanent_deletion_supported": False}


def file_bytes(name):
    with _LOCK:
        path = _root() / _name(name)
        if _safe_file(path) is None:
            raise FileNotFoundError(name)
        return path.read_bytes()


def audit(limit=50):
    with closing(_db()) as db:
        rows = db.execute("SELECT action,filename_hash,result,size,at FROM actions ORDER BY id DESC LIMIT ?",
                          (min(100, max(1, int(limit))),)).fetchall()
        return {"events": [dict(r) for r in rows], "contains_file_content": False}
