"""API social unificada de SKY. Autenticación y SENTINEL existentes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_social_hub as hub

router = APIRouter(prefix="/api/sky/social", dependencies=[Depends(require_key)])


class Draft(BaseModel):
    platform: str = Field(max_length=24)
    text: str = Field(min_length=1, max_length=5000)
    kind: str = Field(default="post", max_length=12)
    target_id: str = Field(default="", max_length=100)


class AiDraft(BaseModel):
    platform: str = Field(max_length=24)
    topic: str = Field(min_length=8, max_length=1200)
    style: str = Field(default="natural y profesional", max_length=80)
    audience: str = Field(default="", max_length=150)
    provider: str = Field(default="auto", max_length=25)


class Approval(BaseModel):
    approved: bool
    scheduled_at: str | None = Field(default=None, max_length=64)


class Metrics(BaseModel):
    views: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    followers: int | None = Field(default=None, ge=0)


def _fail(exc: Exception):
    if isinstance(exc, PermissionError):
        raise HTTPException(403, detail=str(exc)) from exc
    if isinstance(exc, hub.SocialUnavailable):
        raise HTTPException(409, detail=str(exc)) from exc
    if isinstance(exc, hub.SocialError):
        raise HTTPException(422, detail=str(exc)) from exc
    raise exc


@router.get("/capabilities")
def capabilities():
    return hub.capabilities()


@router.get("/queue")
def queue(limit: int = 40):
    return {"items": hub.list_items(limit), "controller": "SKY"}


@router.get("/insights")
def insights():
    return hub.insights()


@router.post("/drafts", status_code=201)
def draft(body: Draft):
    try:
        return hub.draft(body.platform, body.text, body.kind, body.target_id)
    except (hub.SocialError, hub.SocialUnavailable, PermissionError) as exc:
        _fail(exc)


def generate_draft(platform: str, topic: str, style: str, audience: str = "",
                   provider: str = "auto") -> dict:
    """Cada texto lo genera el cerebro de SKY; nunca se publica automáticamente."""
    from neural_core.providers import reply, choose_provider
    platform = hub._valid_platform(platform)
    # Historial real/introducido manualmente, claramente indicado como tal.
    insights = hub.insights()
    messages = [
        {"role": "system", "content":
         "Eres el equipo editorial de SKY. Redacta UNA publicación ORIGINAL en español, "
         "humana, contextual y útil; no uses respuestas prefabricadas. "
         "Adapta el lenguaje a la red social indicada, audiencia y estilo. "
         "No prometas hacerse viral, multiplicar seguidores, vender resultados "
         "ni inventes fuentes, estadísticas o experiencias. "
         "Los datos de rendimiento son aportados manualmente, NO verificados. "
         "Sin hashtags excesivos, engagement bait ni suplantación. "
         "Devuelve SOLO el texto de la publicación, sin encabezados ni comillas. "
         f"Longitud máxima: {hub.MAX_TEXT[platform]} caracteres."},
        {"role": "user", "content": __import__("json").dumps({
            "network": platform, "topic": topic[:1200], "style": style[:80],
            "audience": audience[:150], "owner_supplied_insights": insights,
        }, ensure_ascii=False)},
    ]
    selected, model = choose_provider(provider or "auto", "marketing")
    generated = reply(messages, selected, model, max_output_tokens=800).strip()
    if len(generated) > hub.MAX_TEXT[platform]:
        # No publicar ni truncar texto potencialmente engañoso.
        raise hub.SocialError("La IA excedió el límite; ajustá el tema o el estilo.")
    return hub.draft(platform, generated)


@router.post("/ai-draft", status_code=201)
def ai_draft(body: AiDraft):
    try:
        return generate_draft(body.platform, body.topic, body.style, body.audience, body.provider)
    except (hub.SocialError, hub.SocialUnavailable, PermissionError) as exc:
        _fail(exc)
    except Exception as exc:
        # Mensajes de SDKs de IA pueden incluir secretos; no devolverlos.
        raise HTTPException(503, detail="El modelo de SKY no pudo generar el borrador. Revisá su configuración.") from exc


@router.post("/drafts/{ident}/approve")
def approve(ident: str, body: Approval, request: Request):
    from .sentinel import exigir_pin
    exigir_pin(request, "aprobar una publicación en redes sociales")
    try:
        return hub.approve(ident, owner_approved=body.approved, scheduled_at=body.scheduled_at)
    except (hub.SocialError, hub.SocialUnavailable, PermissionError) as exc:
        _fail(exc)


@router.post("/drafts/{ident}/publish")
def publish(ident: str, request: Request):
    from .sentinel import exigir_pin
    exigir_pin(request, "publicar en una cuenta externa")
    result = hub.publish_approved(ident)
    if not result:
        raise HTTPException(409, detail="No hay publicación aprobada y vencida con ese identificador.")
    return result


@router.post("/drafts/{ident}/cancel")
def cancel(ident: str):
    try:
        return hub.cancel(ident)
    except (hub.SocialError, hub.SocialUnavailable, PermissionError) as exc:
        _fail(exc)


@router.post("/drafts/{ident}/metrics")
def metrics(ident: str, body: Metrics):
    try:
        return hub.record_metrics(ident, **body.model_dump())
    except (hub.SocialError, hub.SocialUnavailable, PermissionError) as exc:
        _fail(exc)
