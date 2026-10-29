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
