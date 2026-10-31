"""Owner-only, text-only SKY Home endpoint using the existing provider API.

No device control, mobile master key sharing, memory export or silent cloud
fallback. Future mobile clients require a separate scoped auth/session design.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .api import require_key
from neural_core.sky_home_routing import CLOUD_ORDER, choose_home_route

router = APIRouter(prefix="/api/sky/home", dependencies=[Depends(require_key)])


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class HomeChat(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    historial: list[Turn] = Field(default_factory=list, max_length=8)
    proveedor: Literal["auto", "ollama", "gemini", "openai", "anthropic", "mistral", "groq", "deepseek", "openrouter", "cloudflare"] = "auto"
    datos: Literal["privados", "generales"] = "privados"
    autorizar_nube: bool = False
    autorizar_datos_privados: bool = False


def _local_model_ready() -> bool:
    """Check the exact Ollama model configured for the existing SKY provider."""
    import json
    from urllib import request
    from neural_core import providers

    model = providers.choose_provider("ollama")[1]
    try:
        with request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.8) as response:
            models = json.load(response).get("models", [])
        accepted = {model, model + ":latest"} if ":" not in model else {model}
        return any(item.get("name") in accepted for item in models)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _availability() -> tuple[bool, tuple[str, ...], bool]:
    from neural_core import providers
    from neural_core import sky_optional_cloud_providers as optional
    configured = set(optional.ready_names())
    cloud = tuple(name for name in CLOUD_ORDER if
                  name in configured or providers.provider_ready(name))
    local = _local_model_ready()  # loopback-only; never downloads a model
    return local, cloud, providers.local_only()


@router.get("/status")
def home_status():
    local, cloud, only = _availability()
    return {
        "service": "SKY Home", "role": "home_server", "local_ollama_ready": local,
        "cloud_configured": list(cloud), "local_only": only,
        "mobile_client_scope": "not_issued", "remote_access_verified": False,
        "note": "Configurado no significa conectado ni probado en el equipo físico",
    }


@router.post("/chat")
def home_chat(body: HomeChat):
    # Cálculos locales de solo lectura: no necesitan un LLM ni autorización
    # de nube; el token móvil limitado jamás obtiene acciones del propietario.
    from neural_core.sky_conversation_tools import maybe_answer as _verified_answer
    checked = _verified_answer(body.texto, mode="chat")
    if checked is not None:
        return {"respuesta": checked["mensaje"], "proveedor": checked["proveedor"],
                "nube": False, "motivo": "Cálculo local comprobado",
                "respaldo_local": False, "acciones_ejecutadas": False,
                "verificacion": checked["verificacion"]}
    from neural_core import providers
    local, cloud, only = _availability()
    route = choose_home_route(
        requested=body.proveedor, configured_cloud=cloud,
        local_available=local, cloud_consent=body.autorizar_nube,
        private_data=(body.datos == "privados"),
        private_cloud_consent=body.autorizar_datos_privados,
        local_only=only,
    )
    if route.provider is None:
        raise HTTPException(status_code=409, detail=route.reason)
    messages = [{"role": "system", "content": (
        "Eres SKY IA, asistente nicaragüense. Habla de tú (quieres, puedes, dime) "
        "con tono natural y cercano, nunca de usted ni de vos. Organiza bien "
        "las respuestas escritas y no leas en voz alta los signos de puntuación. "
        "Responde claramente sin inventar fuentes ni afirmar que ejecutaste "
        "acciones. Esta ruta sólo conversa: no controla dispositivos, no lee "
        "archivos y no usa memoria privada."
    )}]
    messages.extend({"role": item.role, "content": item.content} for item in body.historial)
    messages.append({"role": "user", "content": body.texto})
    from neural_core import sky_optional_cloud_providers as optional
    try:
        if route.provider in optional.OPTIONAL_PROVIDERS:
            # Enforce consent through choose_home_route BEFORE entering any
            # HTTP adapter. Never hand external providers device-action scopes.
            result = optional.reply(route.provider, messages, max_output_tokens=1200)
        else:
            result = providers.reply(messages, provider=route.provider,
                                     max_output_tokens=1200)
    except optional.CloudProviderRateLimited as exc:
        # No automatic retry or hidden paid-provider fallback on a free quota.
        raise HTTPException(status_code=429,
                            detail="El proveedor externo alcanzó su cuota o límite.",
                            headers={"Retry-After": "60"}) from exc
    except (providers.ProviderError, optional.CloudProviderUnavailable, ValueError) as exc:
        # Only an AUTO cloud request may fall back to a verified local model.
        # Never change silently to a different cloud service (cost/privacy).
        if body.proveedor == "auto" and route.remote and local:
            try:
                result = providers.reply(messages, provider="ollama", max_output_tokens=1200)
            except (providers.ProviderError, ValueError) as local_exc:
                raise HTTPException(status_code=503, detail="Nube y respaldo local no disponibles") from local_exc
            return {"respuesta": result, "proveedor": "ollama", "nube": False,
                    "motivo": "La nube falló; se utilizó el respaldo local autorizado",
                    "respaldo_local": True, "acciones_ejecutadas": False}
        # Do not return SDK exceptions, credentials, prompt text or raw responses.
        raise HTTPException(status_code=503, detail="Motor seleccionado no disponible; no se cambió a otro proveedor remoto") from exc
    return {"respuesta": result, "proveedor": route.provider,
            "nube": route.remote, "motivo": route.reason,
            "respaldo_local": False, "acciones_ejecutadas": False}
