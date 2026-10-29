"""Owner-authenticated academic project planning endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core.sky_academic_projects import plan_academico

router = APIRouter(prefix="/api/academic", tags=["SKY Academic"],
                   dependencies=[Depends(require_key)])


class AcademicRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=500)
    instructions: str = Field(min_length=10, max_length=10000)
    degree: str = "licenciatura"
    citation_style: str = "APA 7"
    language: str = "es"


@router.post("/plan")
def academic_plan(body: AcademicRequest):
    try:
        return plan_academico(body.topic, body.instructions, degree=body.degree,
                             citation_style=body.citation_style, language=body.language)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class AcademicDraftRequest(AcademicRequest):
    section: str = Field(min_length=3, max_length=50)
    provider: str = Field(default="auto", max_length=30)
    evidence: list[str] = Field(default_factory=list, max_length=30)
    preceding: str | None = Field(default=None, max_length=5000)


@router.post("/draft-section")
def academic_draft(body: AcademicDraftRequest):
    from neural_core.sky_academic_writer import draft_section
    from neural_core.providers import ProviderError
    try:
        return draft_section(body.topic, body.instructions, body.section,
                             degree=body.degree, citation_style=body.citation_style,
                             language=body.language, provider=body.provider,
                             evidence=body.evidence, preceding=body.preceding)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(503, "El motor de IA seleccionado no está disponible") from exc
