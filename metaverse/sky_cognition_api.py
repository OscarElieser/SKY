"""API cognitiva aditiva para SKY, protegida por X-SKY-KEY y MFA existente."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .api import require_key
from neural_core import sky_cognition as brain

router = APIRouter(
    prefix="/api/sky/cognition",
    tags=["SKY Cognitive Bridge"],
    dependencies=[Depends(require_key)],
)


class QueryInput(BaseModel):
    query: str = Field(min_length=1, max_length=2500)


class PlanInput(QueryInput):
    device: str = Field(default="unknown", pattern="^(unknown|windows|android)$")


class ContextInput(QueryInput):
    execution: str = Field(default="cloud", pattern="^(local|cloud)$")
    include_personal: bool = False
    include_public: bool = True


class ResearchInput(QueryInput):
    provider: str = Field(default="openalex", pattern="^(openalex|crossref)$")
    external_search: bool = False


class VoiceInput(BaseModel):
    text: str = Field(min_length=1, max_length=12000)


def _respond(call):
    try:
        return call()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)[:200]) from exc


@router.get("/capabilities")
def get_capabilities():
    return brain.capabilities()


@router.post("/plan")
def propose_plan(body: PlanInput):
    return _respond(lambda: brain.plan(body.query, device=body.device))


@router.post("/context")
def get_context(body: ContextInput):
    return _respond(lambda: brain.context(
        body.query, execution=body.execution,
        include_personal=body.include_personal,
        include_public=body.include_public,
    ))


@router.post("/research")
def academic_research(body: ResearchInput):
    try:
        return brain.academic_research(body.query, provider=body.provider,
                                       external_search=body.external_search)
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from exc
    except (OSError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(503, "Fuente académica no disponible; reintentá luego.") from exc


@router.post("/personality")
def get_personality(body: QueryInput):
    return _respond(lambda: brain.emotion_style(body.query))


@router.post("/speech")
def prepare_speech(body: VoiceInput):
    return {"spoken_text": _respond(lambda: brain.spoken_text(body.text)),
            "original_preserved": True, "audio_generated": False}


@router.get("/execution-metrics")
def verified_execution_metrics():
    from neural_core.sky_neural_memory import execution_report
    return execution_report()
