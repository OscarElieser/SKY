"""Mobile chat with per-device limited credentials, no owner token on Android.

The owner's key+MFA is accepted only for invitation/revocation endpoints.
The Android agent's existing token can ONLY exchange a one-time chat invite.
Conversation uses the text-only SKY Home provider route (no tools/memory).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from typing import Literal
from pydantic import BaseModel, Field

from .api import require_key
from .sky_home_api import HomeChat, home_chat
from . import sky_home_api
from neural_core import sky_mobile_chat as mobile_chat
from neural_core import sky_inference_gateway as inference
from neural_core import sky_smart_router as smart
from neural_core import sky_answer_quality as answer_quality

router = APIRouter(prefix="/api/sky/mobile-chat")
owner = APIRouter(dependencies=[Depends(require_key)])
client = APIRouter()


class Device(BaseModel):
    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class ChatPair(Device):
    code: str = Field(min_length=16, max_length=128)


class MobileChatTurn(BaseModel):
    """Expanded context only for the paired SKY-local model route."""
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4_000)


class MobileChatRequest(HomeChat):
    # Expanded ONLY for self-hosted inference (the legacy Home API and
    # external cloud adapters retain their lower, separately enforced limits).
    texto: str = Field(min_length=1, max_length=48_000)
    historial: list[MobileChatTurn] = Field(default_factory=list, max_length=8)
    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")


@owner.post("/invite")
def create_invitation(body: Device):
    try:
        return mobile_chat.invite(body.device_id)
    except ValueError as exc:
        raise HTTPException(404, "Teléfono sin emparejamiento activo") from exc


@owner.post("/revoke")
def revoke_mobile_chat(body: Device):
    mobile_chat.revoke(body.device_id)
    return {"revoked": True}


@client.post("/pair")
def exchange_invitation(body: ChatPair, x_sky_mobile_token: str = Header(default="", max_length=128)):
    try:
        return mobile_chat.pair(body.device_id, x_sky_mobile_token, body.code)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(401, "Autorización móvil inválida o caducada") from exc


@client.post("/status")
def mobile_chat_status(body: Device,
                       x_sky_chat_token: str = Header(default="", max_length=128)):
    """Read-only model readiness for authenticated Android chat devices.

    A reachable API does not prove that Ollama is installed or loaded.
    The availability check is loopback-only, with no credentials, URLs,
    files, or cloud-provider list disclosed to the mobile client.
    """
    try:
        mobile_chat.authorize(body.device_id, x_sky_chat_token)
    except PermissionError as exc:
        if str(exc).startswith("Límite"):
            raise HTTPException(429, "Límite de solicitudes de chat",
                                headers={"Retry-After": "60"}) from exc
        raise HTTPException(401, "Sesión móvil inválida o caducada") from exc
    try:
        health = inference.readiness()
    except inference.InferenceUnavailable:
        health = {"local_ollama_ready": False, "ready_workers": 0,
                  "configured_workers": 0, "model_output_verified": False}
    return {"service": "SKY API", "chat_authenticated": True,
            **health,
            "note": "Modelo instalado no implica respuesta, latencia ni calidad comprobadas"}


@client.post("/chat")
def mobile_chat_text(body: MobileChatRequest,
                     x_sky_chat_token: str = Header(default="", max_length=128)):
    try:
        mobile_chat.authorize(body.device_id, x_sky_chat_token)
    except PermissionError as exc:
        if str(exc).startswith("Límite"):
            raise HTTPException(429, "Límite de chat alcanzado", headers={"Retry-After": "60"}) from exc
        raise HTTPException(401, "Sesión móvil inválida o caducada") from exc
    # The owner endpoint is reused as a function only AFTER scope validation.
    # Its body is restricted to text/provider consent and never invokes tools.
    # Avoid revalidating the 16K private request through the legacy HomeChat
    # 4K field. Manual external routes retain their original HomeChat limit.
    if body.proveedor in ("sky_auto", "ollama"):
        payload = body
    else:
        try:
            payload = HomeChat.model_validate(body.model_dump(exclude={"device_id"}))
        except ValueError as exc:
            raise HTTPException(422, "El proveedor externo admite hasta 4000 caracteres") from exc
    if payload.proveedor == "sky_auto":
        messages = [{"role": "system",
                     "content": answer_quality.system_prompt(payload.texto)}]
        messages.extend({"role": turn.role, "content": turn.content}
                        for turn in payload.historial)
        messages.append({"role": "user", "content": payload.texto})
        from neural_core import providers
        try:
            return smart.generate(
                messages,
                cloud_consent=payload.autorizar_nube,
                private_data=(payload.datos == "privados"),
                private_cloud_consent=payload.autorizar_datos_privados,
                local_only=providers.local_only())
        except smart.AutoRouteBusy as exc:
            raise HTTPException(429, "Motor SKY local ocupado; no se enviaron datos externos",
                                headers={"Retry-After": "3"}) from exc
        except smart.AutoRouteUnavailable as exc:
            raise HTTPException(503, "No hay capacidad autorizada en SKY Automático") from exc
        except ValueError as exc:
            raise HTTPException(422, "Consulta de SKY Automático inválida") from exc
    if payload.proveedor == "ollama":
        if payload.autorizar_nube or payload.autorizar_datos_privados:
            raise HTTPException(400, "El motor propio solo admite inferencia privada local")
        messages = [{"role": "system",
                     "content": answer_quality.system_prompt(payload.texto)}]
        messages.extend({"role": turn.role, "content": turn.content}
                        for turn in payload.historial)
        messages.append({"role": "user", "content": payload.texto})
        try:
            return inference.generate(messages, max_output_tokens=(6144 if len(payload.texto) > 32000 else
                4096 if len(payload.texto) > 4000 else 2048))
        except inference.InferenceBusy as exc:
            raise HTTPException(429, "SKY API local ocupada",
                                headers={"Retry-After": "3"}) from exc
        except inference.InferenceUnavailable as exc:
            raise HTTPException(503, "Motor de SKY API sin capacidad disponible") from exc
        except ValueError as exc:
            raise HTTPException(422, "Solicitud de inferencia inválida") from exc
    return home_chat(payload)


@owner.get("/inference/metrics")
def inference_metrics():
    """Owner-only process counters; no prompts, tokens or device identities."""
    return inference.metrics_snapshot()


router.include_router(owner)
router.include_router(client)
