"""SKY specialist frameworks: text-only consultations with original SKY authentication."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_framework_agents as agents

router=APIRouter(prefix="/api/sky/frameworks",dependencies=[Depends(require_key)])


class Consult(BaseModel):
    framework:str=Field(pattern="^(crewai|autogen|langchain)$")
    question:str=Field(min_length=12,max_length=1600)


@router.get("/capabilities")
def capabilities():
    return agents.configured_frameworks()


@router.post("/consult")
def consult(body:Consult):
    try:
        return agents.consult(body.framework,body.question)
    except agents.FrameworkInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except agents.FrameworkUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc
