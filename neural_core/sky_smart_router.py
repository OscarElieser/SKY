"""SKY Automático: own-model first, bounded and consent-aware fallback.

Only text generation. Compatible with existing mobile-chat authentication, but
does not modify legacy 'auto' or manually selected provider semantics.
No unapproved transfer, prompt logging, device tools, or fabricated responses.
"""
from __future__ import annotations

import os
import re
import threading
import time

from neural_core import sky_inference_gateway as local
from neural_core import sky_optional_cloud_providers as optional

# Administrative allowlist. Configuring a key is NOT budget approval.
# The optional list is explicit at deployment; default is LOCAL ONLY.
SUPPORTED_CLOUD = ("groq", "openrouter", "mistral", "cloudflare", "gemini")
_LOCK = threading.RLock()
_COOLDOWN: dict[str, float] = {}
# Automatic routing must never forward apparent credentials. This guard
# catches common explicit secret formats; it is not a full DLP scanner.
_CREDENTIAL = re.compile(
    r"(?i)(?:\bsk-[a-z0-9_-]{16,}\b|\bbearer\s+[a-z0-9_.-]{16,}\b|"
    r"\b(?:api[_ -]?key|access[_ -]?token|password|contrasena|contraseña|"
    r"secret[_ -]?key)\s*[:=]\s*[^\s]{8,})"
)


class AutoRouteUnavailable(RuntimeError):
    pass


class AutoRouteBusy(AutoRouteUnavailable):
    pass


def approved_cloud_order() -> tuple[str, ...]:
    value = os.getenv("SKY_AUTO_CLOUD_ORDER", "").strip().lower()
    if not value:
        return ()
    items = tuple(part.strip() for part in value.split(","))
    if not items or any(part not in SUPPORTED_CLOUD for part in items):
        raise AutoRouteUnavailable("Lista de respaldo no permitida")
    return tuple(dict.fromkeys(items))


def _configured(name: str) -> bool:
    if name == "gemini":
        from neural_core import providers
        return providers.provider_ready("gemini")
    return name in optional.ready_names()


def _try_cloud(name: str, messages: list[dict]) -> str:
    if name == "gemini":
        from neural_core import providers
        return providers.reply(messages, provider="gemini", max_output_tokens=1200)
    return optional.reply(name, messages, max_output_tokens=1200)


def _cooldown(name: str) -> bool:
    with _LOCK:
        return time.monotonic() < _COOLDOWN.get(name, 0.0)


def _mark_limited(name: str, duration: float = 60.0) -> None:
    with _LOCK:
        _COOLDOWN[name] = time.monotonic() + duration


def _validate(messages: list[dict]) -> None:
    if not isinstance(messages, list) or not 1 <= len(messages) <= 10:
        raise ValueError("Historial de SKY fuera de límites")
    for item in messages:
        if (not isinstance(item, dict) or
                item.get("role") not in ("system", "user", "assistant") or
                not isinstance(item.get("content"), str) or
                not 1 <= len(item["content"]) <= (
                    48_000 if item["role"] == "user" else 4000)):
            raise ValueError("Mensaje de SKY fuera de límites")
    if messages[-1]["role"] != "user":
        raise ValueError("Falta el mensaje de usuario")


def generate(messages: list[dict], *, cloud_consent: bool = False,
             private_data: bool = True,
             private_cloud_consent: bool = False,
             local_only: bool = False) -> dict:
    """Prefer own Ollama; use only pre-approved external routes with consent.

    At most two distinct external attempts, no retry of the same provider,
    and no external calls unless BOTH client authorization and a server-side
    allowlist enable them. Failed own model is not assumed to mean success.
    """
    _validate(messages)
    contains_credential = any(_CREDENTIAL.search(item["content"]) for item in messages)
    # The remote adapters were deliberately capped to 4K. Long research
    # prompts remain local rather than being silently truncated or leaked.
    long_or_sensitive = contains_credential or any(
        len(item["content"]) > 4000 for item in messages
    ) or any(
        item["role"] != "system" and item is not messages[-1] and
        len(item["content"]) > 2000 for item in messages
    )
    permitted = (cloud_consent and not local_only and not long_or_sensitive and
                 (not private_data or private_cloud_consent))
    local_busy = False
    try:
        local_budget = (6144 if len(messages[-1]["content"]) > 32000 else
                        4096 if len(messages[-1]["content"]) > 4000 else 2048)
        result = local.generate(messages, max_output_tokens=local_budget)
        # Provenance must reflect reality, not a self-reported chat message.
        return dict(result, ruta="SKY_AUTO_LOCAL", alternativa=False)
    except local.InferenceBusy:
        local_busy = True
    except local.InferenceUnavailable:
        pass
    # Never turn a long or credential-bearing prompt into cloud data.
    if not permitted:
        if local_busy:
            raise AutoRouteBusy("SKY está atendiendo otras consultas; no se enviaron datos externos")
        raise AutoRouteUnavailable("El modelo local no está disponible; no se enviaron datos externos")
    names = approved_cloud_order()
    if not names:
        raise AutoRouteUnavailable("No se configuraron respaldos externos aprobados")
    attempted = 0
    for name in names:
        if attempted >= 2:
            break
        if _cooldown(name) or not _configured(name):
            continue
        attempted += 1
        try:
            answer = _try_cloud(name, messages)
            if not isinstance(answer, str) or not answer.strip():
                raise optional.CloudProviderUnavailable("Respuesta vacía")
            return {
                "respuesta": answer.strip(), "proveedor": name,
                "nube": True, "respaldo_local": False,
                "alternativa": True, "ruta": "SKY_AUTO_EXTERNO_AUTORIZADO",
                "acciones_ejecutadas": False,
            }
        except optional.CloudProviderRateLimited:
            _mark_limited(name, 60.0)
        except (optional.CloudProviderUnavailable, RuntimeError, ValueError):
            # External provider errors must not expose raw requests/credentials.
            _mark_limited(name, 20.0)
    raise AutoRouteUnavailable("Los motores autorizados no respondieron; no se sustituyó el contenido")


def readiness_summary() -> dict:
    """Readiness, not live throughput or quality guarantee."""
    own = local.readiness()
    try:
        configured = list(approved_cloud_order())
    except AutoRouteUnavailable:
        configured = []
    return {
        "local_ollama_ready": own.get("local_ollama_ready", False),
        "automatic_mode": True,
        "external_configured_count": sum(1 for n in configured if _configured(n)),
        "external_auto_default": False,
        "model_output_verified": False,
    }
