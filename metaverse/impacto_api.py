"""Extensión autenticada de la API existente de SKY para docencia e innovación."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from neural_core import sky_impacto as engine

# La autenticación se aplica al registrar el router en metaverse.api.
router = APIRouter(prefix="/api/impacto", tags=["SKY Impacto"])


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    kind: str = Field(default="informe", max_length=30)
    category: str = Field(default="", max_length=30)


class LessonRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    level: str = Field(default="", max_length=40)
    minutes: int = Field(default=45, ge=10, le=240)
    objective: str = Field(default="", max_length=500)


class LessonTurn(BaseModel):
    plan: dict
    step: int = Field(ge=1, le=6)
    student_response: str = Field(default="", max_length=1500)


class ProjectRequest(BaseModel):
    challenge: str = Field(min_length=1, max_length=500)
    competition: str = Field(default="", max_length=120)
    audience: str = Field(default="", max_length=120)


class JudgeRequest(BaseModel):
    scores: dict
    rubric: dict


class ReferenceRequest(BaseModel):
    references: list[dict] = Field(default_factory=list, max_length=50)


def _run(func, *args, **kwargs):
    try:
        return {"ok": True, "result": func(*args, **kwargs)}
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)[:260]) from exc


@router.get("/status")
def status():
    return {"ok": True, "module": "SKY Impacto", "version": "1.0",
            "catalogued_sources": len(engine.SOURCES),
            "external_services_connected": False,
            "model_required_for_freeform_reasoning": True,
            "voice_uses_existing_sky_engine": True}


@router.get("/sources")
def sources(category: str = ""):
    return _run(engine.list_sources, category)


@router.post("/sources/{source_id}/consult")
def consult(source_id: str):
    # Petición explícita; sin capacidad de introducir URLs arbitrarias.
    return _run(engine.consult_source, source_id)


@router.post("/research/plan")
def research(body: ResearchRequest):
    return _run(engine.research_plan, body.topic, body.kind, body.category)


@router.post("/lesson/plan")
def lesson(body: LessonRequest):
    return _run(engine.lesson_plan, body.topic, body.level, body.minutes, body.objective)


@router.post("/lesson/step")
def lesson_turn(body: LessonTurn):
    return _run(engine.lesson_step, body.plan, body.step, body.student_response)


@router.post("/innovation/project")
def project(body: ProjectRequest):
    return _run(engine.innovation_project, body.challenge, body.competition, body.audience)


@router.post("/competition/review")
def judge(body: JudgeRequest):
    return _run(engine.judge_project, body.scores, body.rubric)


@router.post("/references/audit")
def references(body: ReferenceRequest):
    return _run(engine.verify_references, body.references)
