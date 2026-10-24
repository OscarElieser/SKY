"""SKY Secure Device Hub routes.

All routes require the existing owner's SKY key and optional MFA.
Discovery is explicit and transient; control uses existing approved action APIs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from .api import require_key
from neural_core import sky_secure_connectivity as hub

router = APIRouter(prefix="/api/sky/device-hub", dependencies=[Depends(require_key)])


class NewDevice(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    device_type: str = Field(min_length=2, max_length=20)
    transport: str = Field(min_length=3, max_length=30)
    connector: str = Field(min_length=3, max_length=50)
    connection_ref: str = Field(default="", max_length=150)
    owner_attested: bool = False


class Discovery(BaseModel):
    owner_network_confirmed: bool = False
    seconds: float = Field(default=3.0, ge=2, le=6)


class AuditRequest(BaseModel):
    asset_type: str = Field(min_length=3, max_length=30)
    owner_attested: bool = False


@router.get("/capabilities")
def capabilities():
    return hub.catalogue()


@router.get("/devices")
def devices():
    return {"devices": hub.devices()}


@router.post("/devices", status_code=201)
def register_device(body: NewDevice):
    try:
        return hub.register(
            body.name, body.device_type, body.transport,
            body.connector, body.connection_ref, body.owner_attested,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.delete("/devices/{ident}")
def unregister_device(ident: str):
    return {"removed": hub.unregister(ident)}


@router.get("/devices/{ident}/probe")
def probe_device(ident: str, x_sky_device_token: str = Header(default="", max_length=256)):
    try:
        return hub.probe(ident, device_token=x_sky_device_token)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(409, str(exc)[:180]) from exc


@router.post("/discover/bluetooth")
async def discover_ble(body: Discovery):
    try:
        return await hub.discover_ble(owner_network_confirmed=body.owner_network_confirmed,
                                      seconds=body.seconds)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(503, "Bluetooth no está disponible o el permiso local fue rechazado.") from exc


@router.post("/discover/wifi")
async def discover_wifi(body: Discovery):
    try:
        return await hub.discover_wifi(owner_network_confirmed=body.owner_network_confirmed,
                                        seconds=body.seconds)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(503, "mDNS no está disponible en la red local.") from exc


@router.post("/security/audit-plan")
def security_audit_plan(body: AuditRequest):
    try:
        return hub.security_audit_plan(
            asset_type=body.asset_type, owner_attested=body.owner_attested)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
