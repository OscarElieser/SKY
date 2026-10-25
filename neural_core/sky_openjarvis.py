"""Puente opcional de SOLO CONVERSACION con OpenJarvis local.

SKY conserva el enrutamiento, la memoria y los permisos. No se exponen
herramientas de SKY ni se ejecutan acciones de OpenJarvis desde este modulo.
OpenJarvis debe iniciarse por separado con --agent simple.
"""
from __future__ import annotations

import json
import os
import time
from urllib import request


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def enabled() -> bool:
    return os.getenv("SKY_OPENJARVIS_ENABLED", "0").strip().lower() in ("1", "true", "yes", "si", "sí")


def configured() -> bool:
    return enabled() and bool(os.getenv("SKY_OPENJARVIS_MODEL", "").strip())


def _base_url() -> str:
    # Destino fijo de loopback: no aceptar hosts arbitrarios ni proxies.
    raw = os.getenv("SKY_OPENJARVIS_PORT", "8000").strip()
    if not raw.isdecimal() or not 1024 <= int(raw) <= 65535:
        raise ValueError("SKY_OPENJARVIS_PORT debe estar entre 1024 y 65535.")
    return "http://127.0.0.1:" + raw


def _request_json(path: str, payload: dict | None = None, timeout: float = 3.0) -> dict:
    base = _base_url()
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        base + path,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if body is not None else "GET",
    )
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    with opener.open(req, timeout=timeout) as response:
        # No almacenar ni imprimir mensajes; limitar el tamaño de respuesta.
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("La respuesta de OpenJarvis supera el límite permitido.")
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError("OpenJarvis devolvió una respuesta inválida.")
    return parsed


_LOCAL_ENGINES = frozenset(("ollama", "llamacpp", "vllm", "sglang", "mlx", "lemonade"))


class ServerPolicyError(RuntimeError):
    """El proceso OpenJarvis no cumple la politica local requerida por SKY."""


def _verify_server_policy() -> dict:
    # OpenJarvis publica su configuración efectiva en /v1/info.
    # Una configuración agent=orchestrator podría ejecutar herramientas
    # de OpenJarvis sin pasar por SKY Sentinel: prohibirla aquí.
    info = _request_json("/v1/info", timeout=3.0)
    if info.get("agent") != "simple":
        raise ServerPolicyError("OpenJarvis debe iniciarse con --agent simple.")
    if info.get("engine") not in _LOCAL_ENGINES:
        raise ServerPolicyError("OpenJarvis debe usar un motor local, por ejemplo --engine ollama.")
    return info


def status() -> dict:
    """Diagnóstico consultable de forma explícita, sin activar OpenJarvis."""
    model = os.getenv("SKY_OPENJARVIS_MODEL", "").strip()
    result = {"enabled": enabled(), "configured": configured(),
              "healthy": False, "model_available": False, "model": model}
    if not enabled():
        result["detail"] = "Integración opcional desactivada."
        return result
    if not model:
        result["detail"] = "Falta SKY_OPENJARVIS_MODEL en .env."
        return result
    try:
        health = _request_json("/health", timeout=2.0)
        if health.get("status") != "ok":
            raise RuntimeError("Estado de salud de OpenJarvis no válido.")
        result["healthy"] = True
        info = _verify_server_policy()
        result["agent"] = info["agent"]
        result["engine"] = info["engine"]
        models = _request_json("/v1/models", timeout=3.0).get("data", [])
        result["model_available"] = isinstance(models, list) and any(
            isinstance(item, dict) and item.get("id") == model for item in models
        )
        result["detail"] = "Modelo disponible." if result["model_available"] else "Modelo no anunciado por /v1/models."
    except ServerPolicyError as exc:
        result["detail"] = str(exc)
    except Exception as exc:
        result["detail"] = "OpenJarvis no responde correctamente (" + type(exc).__name__ + ")."
    return result


def chat(messages: list[dict], model: str, max_tokens: int = 2500) -> str:
    """Envía únicamente mensajes de texto al endpoint OpenAI-compatible local."""
    if not configured():
        raise RuntimeError("OpenJarvis no está habilitado y configurado en SKY.")
    if not model or len(model) > 150 or not 1 <= max_tokens <= 8192:
        raise ValueError("Modelo o límite de tokens inválido.")
    safe_messages = []
    for message in messages:
        if message.get("role") not in ("system", "user", "assistant"):
            raise ValueError("Rol de mensaje no permitido.")
        if not isinstance(message.get("content"), str):
            raise ValueError("Solo se admiten mensajes de texto.")
        safe_messages.append({"role": message["role"], "content": message["content"]})
    if not safe_messages or safe_messages[-1]["role"] != "user":
        raise ValueError("Falta el mensaje del usuario.")
    started = time.monotonic()
    success = False
    token_count = None
    try:
        _verify_server_policy()
        result = _request_json(
            "/v1/chat/completions",
            {"model": model, "messages": safe_messages,
             "max_tokens": max_tokens, "stream": False},
            timeout=120,
        )
        choices = result.get("choices") or []
        content = choices[0].get("message", {}).get("content") if choices else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenJarvis no devolvió una respuesta de texto.")
        usage = result.get("usage") or {}
        tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
        if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0:
            token_count = tokens
        success = True
        return content.strip()
    finally:
        # Los KPI existentes son independientes: su fallo no afecta la conversacion.
        try:
            from .sky_metricas import registrar
            registrar("modelo", "openjarvis", success,
                     ms=(time.monotonic() - started) * 1000,
                     origen="openjarvis", tokens=token_count)
        except Exception:
            pass


if __name__ == "__main__":
    # Solo el chequeo lanzado desde terminal carga las variables locales de SKY.
    try:
        from pathlib import Path
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except ImportError:
        pass
    print(json.dumps(status(), ensure_ascii=False, indent=2))
