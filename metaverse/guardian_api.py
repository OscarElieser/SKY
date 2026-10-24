"""Owner-only SKY Guardian civic-safety API.

No streams, credentials, institutional integrations, police calls or person IDs.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_guardian as guardian

router=APIRouter(prefix="/api/sky/guardian",dependencies=[Depends(require_key)])


class NewCamera(BaseModel):
    name: str=Field(min_length=2,max_length=80)
    area: str=Field(min_length=2,max_length=80)
    owner_attested: bool=False


class ManualIncident(BaseModel):
    event_type: str=Field(min_length=3,max_length=55)
    camera_id: str | None=None


@router.get("/capabilities")
def capabilities():
    return guardian.catalogue()


@router.get("/cameras")
def cameras():
    return {"cameras":guardian.cameras()}


@router.post("/cameras",status_code=201)
def register_camera(body: NewCamera):
    try:
        return guardian.register_camera(body.name,body.area,owner_attested=body.owner_attested)
    except PermissionError as exc:
        raise HTTPException(403,str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.delete("/cameras/{camera_id}")
def remove_camera(camera_id: str):
    return {"removed":guardian.remove_camera(camera_id)}


@router.get("/events")
def events():
    return {"events":guardian.recent_events()}


@router.post("/events",status_code=201)
def report_event(body: ManualIncident):
    try:
        return guardian.report_event(body.event_type,body.camera_id)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post("/events/{incident_id}/acknowledge")
def acknowledge_event(incident_id: str):
    return {"acknowledged":guardian.acknowledge(incident_id)}
