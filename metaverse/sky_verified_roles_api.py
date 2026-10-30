"""API propia autenticada de SKY para ejecución verificable de roles acotados."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_verified_roles

router = APIRouter(prefix="/api/sky/verified-roles", dependencies=[Depends(require_key)])

class Step(BaseModel):
    id: str = Field(min_length=1, max_length=30)
    role: str = Field(min_length=1, max_length=60)
    tool: str = Field(min_length=1, max_length=60)
    args: dict = Field(default_factory=dict)
    depends_on: str | None = None

class Plan(BaseModel):
    steps: list[Step] = Field(min_length=1, max_length=6)
    allow_network: bool = False

@router.get("/catalog")
def catalog():
    return sky_verified_roles.catalogue()

@router.get("/learning")
def learned_tool_failures():
    """Estado de aprendizaje basado en resultados reales, sin entradas privadas."""
    from neural_core.sky_role_lessons import report
    try:
        return report()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(503, detail="Memoria operativa no disponible") from exc


@router.get("/metrics")
def metrics():
    try:
        return sky_verified_roles.metrics()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(503, detail="Métricas no disponibles") from exc

@router.post("/run")
def run(body: Plan):
    try:
        steps = [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in body.steps]
        return sky_verified_roles.run_plan(steps, allow_network=body.allow_network)
    except sky_verified_roles.RoleError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
