"""Historial privado de SKY HUD; protegido con la misma llave de SKY."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_hud_history as history

router=APIRouter(prefix="/api/hud/historial",dependencies=[Depends(require_key)])


class Entry(BaseModel):
    role:str=Field(pattern="^(user|assistant)$")
    source:str=Field(default="chat",pattern="^(chat|voz|hud)$")
    text:str=Field(min_length=1,max_length=4000)


@router.post("",status_code=201)
def record(body:Entry):
    try:
        return history.append(body.role,body.text,body.source)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.get("")
def listing(limit:int=50,before:int|None=None,q:str|None=None):
    try:
        return history.list_entries(limit,before,q)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.get("/count")
def total():
    return {"entries":history.count()}
