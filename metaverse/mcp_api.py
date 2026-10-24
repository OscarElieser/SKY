"""Rutas MCP dentro de la API propia de SKY; consentimiento granular y PIN."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .api import require_key
from .sentinel import exigir_pin
from neural_core import sentinel_identidad, sky_mcp_hub
from neural_core.sky_approvals import approvals


router = APIRouter(prefix="/api/sky/mcp", tags=["SKY MCP Hub"],
                   dependencies=[Depends(require_key)])


class ServerSelection(BaseModel):
    server: str = Field(min_length=2, max_length=40, pattern=r"^[a-z_]+$")


class ToolProposal(ServerSelection):
    tool: str = Field(min_length=2, max_length=90, pattern=r"^[A-Za-z0-9_-]+$")
    arguments: dict = Field(default_factory=dict)


class ToolConfirmation(ToolProposal):
    approval_token: str = Field(min_length=32, max_length=100)


def _enabled():
    if not sky_mcp_hub._active():
        raise HTTPException(503, "Los servidores MCP están desactivados en este equipo.")


def _require_pin(request: Request):
    # No permitir que una sesión con la llave de API y SIN PIN arranque procesos.
    if not sentinel_identidad.pin_configurado():
        raise HTTPException(409, "Configurá primero el PIN de SKY SENTINEL para usar servidores MCP.")
    exigir_pin(request, "conectar o ejecutar una herramienta MCP")


def _validated(server: str, tool: str | None = None):
    try:
        return (sky_mcp_hub.tool_policy(server, tool) if tool is not None
                else sky_mcp_hub._server_spec(server))
    except sky_mcp_hub.MCPDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    except sky_mcp_hub.MCPUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/catalogue")
def catalogue():
    # Sin iniciar procesos, sin datos de credenciales.
    return sky_mcp_hub.catalogue()


@router.get("/servers")
def servers():
    _enabled()
    return sky_mcp_hub.catalogue()


@router.post("/discover")
async def discover(body: ServerSelection, request: Request):
    _enabled()
    _require_pin(request)
    _validated(body.server)
    try:
        return await sky_mcp_hub.discover(body.server)
    except sky_mcp_hub.MCPUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/prepare")
def prepare(body: ToolProposal, request: Request):
    _enabled()
    policy = _validated(body.server, body.tool)
    try:
        args_json = json.dumps(body.arguments, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError):
        raise HTTPException(422, "Argumentos inválidos.")
    if len(args_json) > 12_000:
        raise HTTPException(413, "Argumentos demasiado grandes.")
    snapshot = body.model_dump()
    try:
        token = approvals.issue("sky_mcp_tool", snapshot, request)
    except RuntimeError as exc:
        raise HTTPException(429, str(exc)) from exc
    return {
        "server": body.server, "tool": body.tool, "arguments": body.arguments,
        "risk": "read_data_exposure" if policy["read_only_classified"] else "external_effect",
        "approval_token": token,
        "expires_in_seconds": approvals.ttl,
        "executed": False,
        "approval": "Revisá servidor, argumentos y alcance; para confirmar se requiere PIN en otra solicitud.",
    }


@router.post("/execute")
async def execute(body: ToolConfirmation, request: Request):
    _enabled()
    policy = _validated(body.server, body.tool)
    _require_pin(request)
    proposed = {"server": body.server, "tool": body.tool, "arguments": body.arguments}
    if not approvals.consume(body.approval_token, "sky_mcp_tool", proposed, request):
        raise HTTPException(403, "Aprobación MCP inexistente, vencida, de otro dueño o ya consumida.")
    try:
        result = await sky_mcp_hub.call(body.server, body.tool, body.arguments)
    except sky_mcp_hub.MCPDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    except sky_mcp_hub.MCPUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    # Registrar petición y latencia, NO sumar acciones verificadas por un efecto externo.
    try:
        from neural_core.sky_metricas import registrar
        registrar("servicio", "mcp_result_reported", not result.get("tool_reported_error", True),
                 ms=result.get("elapsed_ms"),
                 detalle=f"{body.server}:{body.tool}"[:100])
    except Exception:
        pass
    return {**result, "approved_by_owner_pin": True,
            "approval_consumed": True, "classified_as_read_only": policy["read_only_classified"]}
