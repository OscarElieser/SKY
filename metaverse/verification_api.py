"""SKY Verification Lab — rutas privadas montadas sobre la API existente."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .api import require_key
from neural_core import sky_verification_lab as lab

router = APIRouter(prefix="/api/sky/verification",
                   tags=["SKY Verification Lab"], dependencies=[Depends(require_key)])


class EvidenceItem(BaseModel):
    source_sha256: str = Field(min_length=64, max_length=64)
    page: int | None = Field(default=None, ge=1, le=50000)
    quote: str = Field(min_length=8, max_length=450)
    source_text: str = Field(default="", max_length=32000)


class ClaimRequest(BaseModel):
    claim: str = Field(min_length=8, max_length=1200)
    sources: list[EvidenceItem] = Field(min_length=1, max_length=8)


class FeedbackRequest(BaseModel):
    objective: str = Field(min_length=5, max_length=300)
    criteria: list[str] = Field(min_length=1, max_length=6)
    student_response: str = Field(min_length=2, max_length=800)


class SubagentPreview(BaseModel):
    task: str = Field(min_length=1, max_length=2500)
    selected_skills: list[str] | None = Field(default=None, max_length=8)


def _checked(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)[:220]) from exc


@router.get("/capabilities")
def capabilities():
    return lab.capability_catalogue()


@router.get("/runtime")
def runtime(probe_ollama: bool = False):
    return lab.runtime_readiness(probe_ollama=probe_ollama)


@router.get("/connectors")
def connectors():
    return lab.connector_catalogue()


@router.get("/authorization")
def authorization():
    return {
        "existing_api_owner_key_required": True,
        "optional_owner_mfa": True,
        "sentinel_present": True,
        "local_agent_has_independent_policy": True,
        "read_only_verification_lab": True,
        "cross_device_action_permission_fully_harmonized": False,
        "note": "La compatibilidad entre HUD, agente y dispositivos requiere pruebas integrales Windows.",
    }


@router.post("/documents/extract")
async def extract_document(file: UploadFile = File(...)):
    filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    raw = await file.read(lab.MAX_DOC_BYTES + 1)
    if not raw or len(raw) > lab.MAX_DOC_BYTES:
        raise HTTPException(413, "Documento vacío o mayor a 5 MB.")
    return _checked(lab.extract_document, filename, raw)


@router.post("/evidence/crosscheck")
def crosscheck(body: ClaimRequest):
    return _checked(lab.crosscheck_claim, body.claim, [s.model_dump() for s in body.sources])


@router.post("/education/formative-review")
def formative_review(body: FeedbackRequest):
    return _checked(lab.formative_review, body.objective, body.criteria, body.student_response)


@router.get("/kpis")
def kpis(period: str = "hoy"):
    return _checked(lab.kpi_snapshot, period)


@router.post("/orchestration/preview")
def preview(body: SubagentPreview):
    return _checked(lab.subagent_preview, body.task, body.selected_skills)
