"""Protected SKY/Make bridge, without replacing existing n8n or workflows."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_make_bridge as make

router=APIRouter(prefix="/api/sky/make",dependencies=[Depends(require_key)])


class Trigger(BaseModel):
    alias:str=Field(min_length=1,max_length=32)
    payload:dict=Field(default_factory=dict)
    approved:bool=False


@router.get("/capabilities")
def capabilities():
    return make.capabilities()


@router.post("/trigger")
def trigger(body:Trigger,request:Request):
    from .sentinel import exigir_pin
    exigir_pin(request,"iniciar un escenario externo de Make")
    try:
        return make.trigger(body.alias,body.payload,approved=body.approved)
    except PermissionError as exc:
        raise HTTPException(403,str(exc)) from exc
    except make.MakeInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except make.MakeUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc
