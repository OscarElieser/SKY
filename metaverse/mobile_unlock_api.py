"""SKY Mobile Unlock API — owner-only authorized carrier assistance.

No unlocking secret, IMEI rewrite, firmware flashing, PIN/activation bypass,
or direct carrier account access. The USB diagnostics are read-only.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_mobile_unlock as mobile

router = APIRouter(prefix="/api/sky/mobile-unlock", dependencies=[Depends(require_key)])


class AuthorizedUSB(BaseModel):
    owner_attested: bool = False


class CarrierPlan(BaseModel):
    owner_attested: bool = False
    source_carrier: str = Field(min_length=3, max_length=30)
    target_carrier: str = Field(min_length=3, max_length=30)
    os_family: str = Field(default="android", max_length=10)
    observed_state: str = Field(default="unknown", max_length=40)


@router.get("/capabilities")
def capabilities():
    return mobile.catalogue()


@router.post("/diagnose-usb")
def diagnose_usb(body: AuthorizedUSB):
    try:
        return mobile.diagnose_usb(owner_attested=body.owner_attested)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/plan")
def plan(body: CarrierPlan):
    try:
        return mobile.plan(
            owner_attested=body.owner_attested,
            source_carrier=body.source_carrier,
            target_carrier=body.target_carrier,
            os_family=body.os_family,
            observed_state=body.observed_state,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
