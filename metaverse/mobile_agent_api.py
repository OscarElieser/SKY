"""Rutas Android: creación de órdenes sólo con SKY Owner+MFA; dispositivo con token separado."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_mobile_agent as mobile

router = APIRouter(prefix="/api/sky/mobile-agent")
owner = APIRouter(dependencies=[Depends(require_key)])
agent = APIRouter()


class Pairing(BaseModel):
    code: str = Field(min_length=8, max_length=128)
    label: str = Field(min_length=3, max_length=60)


class Command(BaseModel):
    target: str = Field(min_length=2, max_length=24)


class Completion(BaseModel):
    state: str = Field(pattern="^(SENT|FAILED|REJECTED)$")
    message: str = Field(default="", max_length=180)


def _bad(exc: Exception):
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    raise HTTPException(status_code=422, detail=str(exc)) from exc


@owner.post("/pair/start")
def start_pairing():
    return mobile.pairing_code()


@agent.post("/pair/complete")
def finish_pairing(body: Pairing):
    try:
        return mobile.pair(body.code, body.label)
    except (ValueError, PermissionError) as exc:
        _bad(exc)


@owner.get("/devices")
def list_devices():
    return {"devices": mobile.devices(), "allowed_apps": mobile.TARGETS}


@owner.delete("/devices/{device_id}")
def revoke_device(device_id: str):
    try:
        mobile.revoke(device_id)
        return {"revoked": True}
    except ValueError as exc:
        _bad(exc)


@agent.get("/devices/{device_id}/home-status")
def device_home_status(device_id: str, x_sky_mobile_token: str = Header(default="", max_length=128)):
    """Minimal health for a paired Android device, without SKY owner access."""
    try:
        mobile.device_status(device_id, x_sky_mobile_token)
    except PermissionError as exc:
        _bad(exc)
    from .sky_home_api import _availability
    local, cloud, only = _availability()
    return {
        "service": "SKY Home", "server_online": True,
        "local_ollama_ready": local, "cloud_configured": bool(cloud),
        "local_only": only, "chat_authorized": False,
        "device_actions_authorized": False,
        "note": "El token del agente solo permite funciones limitadas, no el chat del propietario.",
    }


@agent.post("/devices/{device_id}/revoke-self")
def revoke_self(device_id: str, x_sky_mobile_token: str = Header(default="", max_length=128)):
    try:
        mobile.revoke(device_id, token=x_sky_mobile_token)
        return {"revoked": True}
    except (ValueError, PermissionError) as exc:
        _bad(exc)


@owner.post("/devices/{device_id}/commands")
def create_command(device_id: str, body: Command):
    try:
        return mobile.queue(device_id, body.target)
    except ValueError as exc:
        _bad(exc)


@owner.get("/devices/{device_id}/commands/{command_id}")
def get_command(device_id: str, command_id: str):
    try:
        return mobile.command_status(device_id, command_id)
    except ValueError as exc:
        _bad(exc)


@agent.get("/devices/{device_id}/next")
def next_command(device_id: str, x_sky_mobile_token: str = Header(default="", max_length=128)):
    try:
        return mobile.poll(device_id, x_sky_mobile_token)
    except PermissionError as exc:
        _bad(exc)


@agent.post("/devices/{device_id}/commands/{command_id}/complete")
def complete_command(device_id: str, command_id: str, body: Completion,
                     x_sky_mobile_token: str = Header(default="", max_length=128)):
    try:
        return mobile.complete(device_id, x_sky_mobile_token, command_id, body.state, body.message)
    except (ValueError, PermissionError) as exc:
        _bad(exc)


router.include_router(owner)
router.include_router(agent)
