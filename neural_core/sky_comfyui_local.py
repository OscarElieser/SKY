"""Motor multimedia local de SKY, conectado a ComfyUI ya instalado.

No descarga modelos, no ejecuta scripts, no permite definir URLs o workflows
desde el navegador. Cada creación usa un workflow API de confianza elegido
localmente por el propietario, en ComfyUI sobre 127.0.0.1.
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib import parse, request, error

ROOT = Path(__file__).resolve().parents[1]
MAX_OUTPUT = 75_000_000
MAX_WORKFLOW = 500_000
UUID = re.compile(r"^[0-9a-fA-F-]{36}$")
NAME = re.compile(r"^[^/\\\x00-\x1f]{1,180}$")
SUBDIR = re.compile(r"^[a-zA-Z0-9_/-]{0,140}$")


class LocalMediaError(ValueError):
    pass


class LocalMediaUnavailable(RuntimeError):
    pass


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def enabled() -> bool:
    return os.getenv("SKY_COMFYUI_ENABLED", "0") == "1"


def base_url() -> str:
    port = os.getenv("SKY_COMFYUI_PORT", "8188")
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise LocalMediaError("Puerto local ComfyUI inválido.")
    return "http://127.0.0.1:" + port


def _call(method: str, path: str, body: dict | None = None,
          max_size: int = 300_000) -> tuple[bytes, str]:
    if not enabled():
        raise LocalMediaUnavailable("ComfyUI desactivado; activalo en el .env privado de SKY.")
    if not (path in ("/system_stats", "/prompt") or
            re.fullmatch(r"/history/[0-9a-fA-F-]{36}", path) or
            path.startswith("/view?")):
        raise LocalMediaError("Ruta ComfyUI no permitida.")
    if path.startswith("/view?") and method != "GET":
        raise LocalMediaError("Solo lectura de medios.")
    raw = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(base_url() + path, method=method, data=raw,
                          headers={"Content-Type": "application/json",
                                   "Accept": "application/json" if not path.startswith("/view?") else "*/*"})
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=25 if method == "POST" else 12) as resp:
            ctype = resp.headers.get("Content-Type", "")
            data = resp.read(max_size + 1)
        if len(data) > max_size:
            raise LocalMediaUnavailable("Respuesta local supera el límite permitido.")
        return data, ctype
    except (error.URLError, TimeoutError, OSError) as exc:
        raise LocalMediaUnavailable("ComfyUI local no responde: revisá su servidor y modelos.") from exc


def _json(method: str, path: str, body: dict | None = None) -> dict:
    raw, _ = _call(method, path, body)
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError()
        return parsed
    except ValueError as exc:
        raise LocalMediaUnavailable("ComfyUI devolvió datos no reconocidos.") from exc


def _dbpath() -> Path:
    return Path(os.getenv("SKY_COMFYUI_DB") or ROOT / "local_data" / "sky_comfyui_jobs.sqlite3")


@contextmanager
def _db():
    path = _dbpath()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS jobs(
        id TEXT PRIMARY KEY, comfy_id TEXT NOT NULL, kind TEXT NOT NULL,
        status TEXT NOT NULL, asset_id TEXT, created_at TEXT NOT NULL
    )""")
    try:
        yield con
        if con.in_transaction:
            con.commit()
    except BaseException:
        if con.in_transaction:
            con.rollback()
        raise
    finally:
        con.close()


def capabilities() -> dict:
    return {"controller": "SKY", "engine": "ComfyUI local",
            "configured": enabled(), "server_verified": False,
            "image_workflow": bool(os.getenv("SKY_COMFYUI_WORKFLOW_IMAGE")),
            "video_workflow": bool(os.getenv("SKY_COMFYUI_WORKFLOW_VIDEO")),
            "supports_diffusion_workflows": True, "model_verified": False, "model_bundled": False,
            "source": "local_workflows_selected_by_owner",
            "outputs_verified_only_after_download": True}


def check() -> dict:
    stats = _json("GET", "/system_stats")
    return {"connected": True, "engine": "ComfyUI local",
            "devices": len(stats.get("devices", [])) if isinstance(stats.get("devices"), list) else 0}


def _workflow(kind: str, prompt: str) -> dict:
    if kind not in ("image", "video"):
        raise LocalMediaError("Creación local: image o video.")
    var = "SKY_COMFYUI_WORKFLOW_" + kind.upper()
    node_var = "SKY_COMFYUI_PROMPT_NODE_" + kind.upper()
    location = os.getenv(var, "").strip()
    if not location:
        raise LocalMediaUnavailable("Configurá " + var + " con un workflow API exportado de ComfyUI.")
    file = Path(location).expanduser().resolve()
    if not file.is_file() or file.stat().st_size > MAX_WORKFLOW:
        raise LocalMediaUnavailable("El workflow local no existe o supera el límite.")
    try:
        graph = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LocalMediaUnavailable("El workflow API no es JSON válido.") from exc
    if not isinstance(graph, dict) or not graph or len(graph) > 200:
        raise LocalMediaError("Workflow API inválido o excesivo.")
    for node in graph.values():
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            raise LocalMediaError("Nodo ComfyUI inválido.")
    node_id = os.getenv(node_var, "").strip()
    if node_id not in graph or graph[node_id].get("class_type") != "CLIPTextEncode":
        raise LocalMediaUnavailable("Elegí un nodo CLIPTextEncode positivo mediante " + node_var + ".")
    if "text" not in graph[node_id]["inputs"] or not isinstance(graph[node_id]["inputs"]["text"], str):
        raise LocalMediaError("Nodo no admite texto en inputs.text.")
    graph[node_id]["inputs"]["text"] = prompt
    return graph


def submit(kind: str, prompt: str) -> dict:
    if not enabled():
        raise LocalMediaUnavailable("Configurá primero ComfyUI local.")
    if not isinstance(prompt, str) or not 8 <= len(prompt.strip()) <= 2000:
        raise LocalMediaError("La descripción debe tener entre 8 y 2000 caracteres.")
    graph = _workflow(kind, prompt.strip())
    result = _json("POST", "/prompt", {"prompt": graph, "client_id": "SKY_" + uuid.uuid4().hex})
    cid = result.get("prompt_id")
    if not isinstance(cid, str) or not UUID.fullmatch(cid):
        raise LocalMediaUnavailable("ComfyUI no confirmó el identificador de la tarea.")
    ident = "skylocal_" + uuid.uuid4().hex
    with _db() as db:
        db.execute("INSERT INTO jobs(id,comfy_id,kind,status,created_at) VALUES(?,?,?,?,?)",
                   (ident, cid, kind, "queued", datetime.now(timezone.utc).isoformat()))
    return {"job_id": ident, "kind": kind, "status": "queued", "asset_id": None,
            "engine": "ComfyUI local", "image_or_video_generated": False}


def _output(entries: dict, kind: str) -> dict | None:
    preferred = ("images",) if kind == "image" else ("gifs", "videos")
    for node in entries.values():
        if not isinstance(node, dict):
            continue
        for key in preferred:
            items = node.get(key)
            if not isinstance(items, list):
                continue
            for entry in items:
                if not isinstance(entry, dict):
                    continue
                filename = entry.get("filename", "")
                subfolder = entry.get("subfolder", "")
                type_ = entry.get("type", "output")
                ext = Path(filename).suffix.lower()
                if not NAME.fullmatch(filename) or not SUBDIR.fullmatch(subfolder) or ".." in subfolder.split("/"):
                    continue
                if type_ != "output":
                    continue
                if ext in ((".png", ".jpg", ".jpeg", ".webp") if kind == "image" else (".mp4", ".webm")):
                    return {"filename": filename, "subfolder": subfolder, "type": "output"}
    return None


def status(ident: str) -> dict:
    if not isinstance(ident, str) or not re.fullmatch(r"skylocal_[0-9a-f]{32}", ident):
        raise LocalMediaError("ID de trabajo inválido.")
    with _db() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise LocalMediaError("Trabajo no encontrado.")
        job = dict(row)
    if job["status"] == "completed":
        return {"job_id": ident, "status": "completed", "asset_id": job["asset_id"], "kind": job["kind"]}
    if job["status"] in ("failed", "needs_review"):
        return {"job_id": ident, "status": job["status"], "asset_id": None}
    data = _json("GET", "/history/" + job["comfy_id"])
    history = data.get(job["comfy_id"])
    if not isinstance(history, dict):
        return {"job_id": ident, "status": "processing", "asset_id": None}
    state = history.get("status", {})
    if isinstance(state, dict) and state.get("status_str") == "error":
        with _db() as db:
            db.execute("UPDATE jobs SET status='failed' WHERE id=?", (ident,))
        return {"job_id": ident, "status": "failed", "asset_id": None}
    output = _output(history.get("outputs") or {}, job["kind"])
    if not output:
        return {"job_id": ident, "status": "processing", "asset_id": None}
    query = parse.urlencode(output)
    raw, _ = _call("GET", "/view?" + query, max_size=MAX_OUTPUT)
    from .sky_creative import ingest
    # Validate actual image/video content via SKY's unchanged library.
    asset = ingest(raw, output["filename"])
    with _db() as db:
        db.execute("UPDATE jobs SET status='completed',asset_id=? WHERE id=? AND status='queued'",
                   (asset["id"], ident))
    return {"job_id": ident, "status": "completed", "asset_id": asset["id"],
            "kind": job["kind"], "engine": "ComfyUI local"}
