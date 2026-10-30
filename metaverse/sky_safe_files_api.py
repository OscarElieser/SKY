"""Rutas de operaciones documentales SKY: propietario, recibo efímero y PIN."""
from __future__ import annotations

import mimetypes
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .api import require_key
from .sentinel import exigir_pin
from neural_core import sky_safe_workspace as workspace
from neural_core.sky_approvals import approvals

router = APIRouter(prefix="/api/sky/safe-files", dependencies=[Depends(require_key)])


class Operation(BaseModel):
    spec: dict = Field(default_factory=dict)


class Approval(Operation):
    approval_token: str = Field(min_length=32, max_length=100)
    expected_sha: str = Field(max_length=64)
    destination_state: str | None = Field(default=None, max_length=64)


def _failure(exc):
    if isinstance(exc, (workspace.WorkspaceConflict, FileExistsError)):
        raise HTTPException(409, str(exc)[:180]) from exc
    if isinstance(exc, (workspace.WorkspaceError, ValueError, UnicodeError)):
        raise HTTPException(422, str(exc)[:180]) from exc
    if isinstance(exc, (OSError, ImportError, RuntimeError)):
        raise HTTPException(503, "No está disponible el espacio de archivos.") from exc
    raise exc


@router.get("/capabilities")
def capabilities():
    return {"operations": sorted(workspace.OPS), "extensions": sorted(workspace.EXTS),
            "workspace_only": True, "requires_preview": True,
            "single_use_approval": True, "configured_pin_for_modifications": True,
            "permanent_delete": False, "mobile_chat_token_can_edit": False,
            "physical_devices_verified": False}


@router.get("/list")
def list_items():
    try:
        return workspace.files()
    except (OSError, ValueError, RuntimeError) as exc:
        _failure(exc)


@router.get("/trash")
def trash_items():
    try:
        return workspace.trash_items()
    except (OSError, ValueError, RuntimeError) as exc:
        _failure(exc)


@router.get("/audit")
def audit_items():
    try:
        return workspace.audit()
    except (OSError, ValueError, RuntimeError) as exc:
        _failure(exc)


@router.get("/text/{name}")
def inspect_text(name: str):
    # Lectura de texto acotada y autenticada para edición en el HUD.
    try:
        from pathlib import Path
        if Path(name).suffix.lower() not in workspace.TEXT_EXT:
            raise workspace.WorkspaceError("Este formato se edita regenerando el documento.")
        data = workspace.file_bytes(name)
        if len(data) > workspace.MAX_TEXT:
            raise workspace.WorkspaceError("Archivo demasiado extenso para editar en el HUD.")
        text = data.decode("utf-8")
        import hashlib
        return {"name":name,"text":text,"sha256":hashlib.sha256(data).hexdigest(),
                "read_only_preview":True,"executed":False}
    except FileNotFoundError as exc:
        raise HTTPException(404, "Archivo no encontrado.") from exc
    except (UnicodeDecodeError, OSError, ValueError) as exc:
        _failure(workspace.WorkspaceError("No se puede editar como texto UTF-8.") if isinstance(exc,UnicodeDecodeError) else exc)


@router.get("/download/{name}")
def download(name: str):
    try:
        data = workspace.file_bytes(name)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Archivo no encontrado.") from exc
    except (OSError, ValueError) as exc:
        _failure(exc)
    return Response(data, media_type=mimetypes.guess_type(name)[0] or "application/octet-stream",
                    headers={"Content-Disposition":"attachment; filename*=UTF-8''"+quote(name),
                             "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})


@router.post("/prepare")
def prepare(body: Operation, request: Request):
    try:
        spec = workspace._validate(body.spec)
        with workspace._LOCK:
            plan = workspace.preview(spec)
            receipt = {"spec":spec,"expected_sha":plan["expected_sha"],
                       "destination_state":plan["destination_state"]}
            token = approvals.issue("sky_safe_files_v1", receipt, request)
        return {"preview":plan,"approval_token":token,
                "expires_in_seconds":approvals.ttl,"committed":False}
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        _failure(exc)


@router.post("/commit")
def commit(body: Approval, request: Request):
    try:
        spec = workspace._validate(body.spec)
        if spec["op"] in ("replace","append","rename","trash","restore"):
            exigir_pin(request, "modificar archivos del espacio seguro")
        receipt = {"spec":spec,"expected_sha":body.expected_sha,
                   "destination_state":body.destination_state}
        with workspace._LOCK:
            if not approvals.consume(body.approval_token, "sky_safe_files_v1", receipt, request):
                raise HTTPException(409,"Aprobación inválida, usada o caducada.")
            return workspace.commit(spec,body.expected_sha,body.destination_state)
    except HTTPException:
        raise
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        _failure(exc)
