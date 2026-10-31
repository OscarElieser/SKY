"""Optional OpenAI-compatible cloud connectors for SKY's SERVER-SIDE API.

No secrets in Android or source control. All endpoints are pinned HTTPS URLs;
no arbitrary user-provided endpoints, redirects, automatic retries or cloud
fallbacks. The caller MUST enforce per-request consent and scoped identity.
This module never invokes phone/device tools.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib import error, request

OPTIONAL_PROVIDERS = ("openrouter", "mistral", "groq", "cloudflare")
_MAX_RESPONSE = 262_144
_MAX_REQUEST = 95_000
_MODEL = re.compile(r"^[a-zA-Z0-9_@./:-]{1,128}$")
_ACCOUNT = re.compile(r"^[a-fA-F0-9]{32}$")


class CloudProviderUnavailable(RuntimeError):
    pass


class CloudProviderRateLimited(CloudProviderUnavailable):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    endpoint: str
    key: str
    model: str


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configuration(provider: str) -> ProviderConfig:
    """Resolve only known endpoints and server-side environment credentials."""
    if provider not in OPTIONAL_PROVIDERS:
        raise CloudProviderUnavailable("Proveedor externo no permitido")
    meta = {
        "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "openrouter/free"),
        "mistral": ("MISTRAL_API_KEY", "MISTRAL_MODEL", "mistral-small-latest"),
        "groq": ("GROQ_API_KEY", "GROQ_MODEL", "openai/gpt-oss-20b"),
        "cloudflare": ("SKY_WORKERS_AI_TOKEN", "CLOUDFLARE_AI_MODEL",
                       "@cf/meta/llama-3.1-8b-instruct"),
    }
    env_key, env_model, default_model = meta[provider]
    key = os.getenv(env_key, "").strip()
    model = os.getenv(env_model, default_model).strip()
    if not key or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise CloudProviderUnavailable("Credenciales de proveedor no configuradas")
    if not _MODEL.fullmatch(model):
        raise CloudProviderUnavailable("Identificador de modelo no admitido")
    if provider == "openrouter":
        # Free-only by default: never accidentally invoke billable models.
        # Operator can consciously change this server-side for paid accounts.
        free_only = os.getenv("SKY_OPENROUTER_FREE_ONLY", "1").lower() not in (
            "0", "false", "off")
        if free_only and model != "openrouter/free" and not model.endswith(":free"):
            raise CloudProviderUnavailable("OpenRouter requiere modelo :free o openrouter/free")
    endpoints = {
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "mistral": "https://api.mistral.ai/v1/chat/completions",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
    }
    if provider == "cloudflare":
        account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        if not _ACCOUNT.fullmatch(account):
            raise CloudProviderUnavailable("Cuenta de Workers AI sin configurar")
        if not model.startswith("@cf/"):
            raise CloudProviderUnavailable("Workers AI requiere un modelo @cf/ permitido")
        endpoint = ("https://api.cloudflare.com/client/v4/accounts/" +
                    account + "/ai/v1/chat/completions")
    else:
        endpoint = endpoints[provider]
    return ProviderConfig(provider, endpoint, key, model)


def ready_names() -> tuple[str, ...]:
    """Configuration alone does NOT prove an account has quota or credit."""
    found: list[str] = []
    for name in OPTIONAL_PROVIDERS:
        try:
            configuration(name)
        except CloudProviderUnavailable:
            continue
        found.append(name)
    return tuple(found)


def _validate_messages(messages: list[dict], max_output_tokens: int) -> None:
    if not isinstance(messages, list) or not 1 <= len(messages) <= 10:
        raise ValueError("Cantidad de mensajes no admitida")
    for msg in messages:
        if (not isinstance(msg, dict) or
                msg.get("role") not in ("system", "user", "assistant") or
                not isinstance(msg.get("content"), str) or
                not 1 <= len(msg["content"]) <= 4000):
            raise ValueError("Mensaje de texto no admitido")
    if messages[-1]["role"] != "user":
        raise ValueError("Falta la consulta del usuario")
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 2048:
        raise ValueError("Límite de tokens no permitido")


def reply(provider: str, messages: list[dict], max_output_tokens: int = 1200) -> str:
    """Single authorized server-side attempt; no opaque fallback or tool calls."""
    _validate_messages(messages, max_output_tokens)
    config = configuration(provider)
    payload = json.dumps({
        "model": config.model, "messages": messages, "max_tokens": max_output_tokens,
        "temperature": 0.2, "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    if len(payload) > _MAX_REQUEST:
        raise ValueError("Solicitud mayor que el presupuesto autorizado")
    req = request.Request(
        config.endpoint, data=payload,
        headers={"Authorization": "Bearer " + config.key,
                 "Content-Type": "application/json",
                 "Accept": "application/json"},
        method="POST")
    opener = request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=45) as response:
            raw = response.read(_MAX_RESPONSE + 1)
            if len(raw) > _MAX_RESPONSE:
                raise CloudProviderUnavailable("Respuesta del proveedor excesiva")
    except error.HTTPError as exc:
        if exc.code == 429:
            raise CloudProviderRateLimited("Proveedor externo sin cuota disponible") from None
        if exc.code in (301, 302, 303, 307, 308):
            raise CloudProviderUnavailable("Redirección externa rechazada") from None
        if exc.code in (401, 403):
            raise CloudProviderUnavailable("Credenciales o permisos externos inválidos") from None
        raise CloudProviderUnavailable("Proveedor externo no disponible") from None
    except (error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise CloudProviderUnavailable("Proveedor externo no disponible") from None
    try:
        response = json.loads(raw)
        choices = response["choices"]
        first = choices[0]["message"]
        # Refuse function calls in a text-only API.
        if first.get("tool_calls") or first.get("function_call"):
            raise ValueError("Acción externa no permitida")
        answer = first["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Respuesta de texto vacía")
        if len(answer) > 60_000:
            raise ValueError("Respuesta excesivamente larga")
        return answer.strip()
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise CloudProviderUnavailable("El proveedor no devolvió texto verificable") from None
