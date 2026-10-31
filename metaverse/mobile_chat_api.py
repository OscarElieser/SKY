"""Mobile chat with per-device limited credentials, no owner token on Android.

The owner's key+MFA is accepted only for invitation/revocation endpoints.
The Android agent's existing token can ONLY exchange a one-time chat invite.
Conversation uses the text-only SKY Home provider route (no tools/memory).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .api import require_key
from .sky_home_api import HomeChat, home_chat
from . import sky_home_api
from neural_core import sky_mobile_chat as mobile_chat

router = APIRouter(prefix="/api/sky/mobile-chat")
owner = APIRouter(dependencies=[Depends(require_key)])
client = APIRouter()


class Device(BaseModel):
    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class ChatPair(Device):
    code: str = Field(min_length=16, max_length=128)


class MobileChatRequest(HomeChat):
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
    return {"service": "SKY API", "chat_authenticated": True,
            "local_ollama_ready": sky_home_api._local_model_ready(),
            "model_output_verified": False,
            "note": "Modelo disponible no equivale a respuesta, velocidad ni calidad comprobadas"}


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
    payload = HomeChat.model_validate(body.model_dump(exclude={"device_id"}))
    return home_chat(payload)


router.include_router(owner)
router.include_router(client)
