"""Owner-only SKY Knowledge Library API.

Uploaded documents are searchable locally only after explicit opt-in. No model
training, hidden web fetches, arbitrary path access, or automatic truth claims.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from pydantic import BaseModel, Field

from .api import require_key
from .multimodal_api import _bounded_read
from neural_core import sky_knowledge_library as knowledge

router=APIRouter(prefix="/api/sky/knowledge",dependencies=[Depends(require_key)])


class SearchQuery(BaseModel):
    query: str=Field(min_length=3,max_length=500)
    limit: int=Field(default=5,ge=1,le=10)


@router.get("/capabilities")
def capabilities():
    return knowledge.catalogue()


@router.post("/documents",status_code=201)
async def ingest(file: UploadFile=File(...),
                 owner_attested: bool=Form(default=False),
                 consent_to_index: bool=Form(default=False)):
    if not owner_attested or not consent_to_index:
        raise HTTPException(403,"Debés autorizar expresamente que SKY guarde el documento.")
    try:
        data=await _bounded_read(file)
        return knowledge.ingest(file.filename or "",data,
                                owner_attested=owner_attested,
                                consent_to_index=consent_to_index)
    except PermissionError as exc:
        raise HTTPException(403,str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422,str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)[:200]) from exc
    finally:
        await file.close()


@router.get("/documents")
def list_documents():
    try:
        return {"documents":knowledge.documents()}
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)[:200]) from exc


@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    return {"deleted":knowledge.delete(document_id)}


@router.post("/search")
def search(body: SearchQuery):
    try:
        return knowledge.search(body.query,body.limit)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)[:200]) from exc
