"""Owner-only review/curation of SKY Neural Memory."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_neural_memory as memory

router=APIRouter(prefix="/api/sky/neural-memory",dependencies=[Depends(require_key)])


class Fact(BaseModel):
    category: str = Field(min_length=3, max_length=30)
    text: str = Field(min_length=5, max_length=1500)


@router.get("/status")
def status():
    stats=memory.execution_report()
    try:
        memory._key()
        encrypted=True
    except RuntimeError:
        encrypted=False
    return {**stats,"personal_memory_encryption_configured":encrypted,
            "no_unreviewed_auto_personal_memory":True}


@router.post("/facts",status_code=201)
def save(body: Fact):
    try:
        return memory.save_fact("owner",body.category,body.text)
    except ValueError as exc:
        raise HTTPException(422,str(exc)[:180]) from exc
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)[:180]) from exc


@router.get("/facts")
def list_facts(category: str | None = None):
    try:
        return {"facts": memory.facts("owner",category)}
    except ValueError as exc:
        raise HTTPException(422,str(exc)[:180]) from exc
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)[:180]) from exc


@router.delete("/facts/{memory_id}")
def delete(memory_id: str):
    return {"deleted":memory.delete_fact(memory_id)}


@router.get("/execution")
def history():
    return memory.execution_report()
