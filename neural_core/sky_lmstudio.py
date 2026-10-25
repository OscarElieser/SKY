"""Motor LLM local opcional para SKY utilizando el servidor LM Studio.

Nunca toma URL arbitraria; solo http://127.0.0.1:puerto configurado.
No instala LM Studio ni modelos. No proporciona herramientas externas.
"""
from __future__ import annotations
import json
import os
from urllib import request, error


class LMStudioError(RuntimeError):
    pass


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configured():
    return os.getenv("SKY_LMSTUDIO_ENABLED", "0") == "1" and bool(
        os.getenv("SKY_LMSTUDIO_MODEL", "").strip())


def _base():
    port = os.getenv("SKY_LMSTUDIO_PORT", "1234")
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise LMStudioError("Puerto LM Studio inválido.")
    return "http://127.0.0.1:" + port


def _request(method, endpoint, payload=None):
    if endpoint not in ("/v1/models", "/v1/chat/completions"):
        raise LMStudioError("Endpoint prohibido.")
    data = json.dumps(payload).encode() if payload is not None else None
    req = request.Request(_base() + endpoint, method=method, data=data,
                          headers={"Content-Type": "application/json"})
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=90 if method == "POST" else 4) as resp:
            contents = resp.read(100_001)
        if len(contents) > 100_000:
            raise LMStudioError("Respuesta demasiado grande.")
        return json.loads(contents)
    except (error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise LMStudioError("LM Studio local no está disponible o devolvió una respuesta inválida.") from exc


def status():
    if not configured():
        return {"configured": False, "online": False}
    try:
        data = _request("GET", "/v1/models")
        models = [x["id"] for x in data.get("data", [])
                  if isinstance(x, dict) and isinstance(x.get("id"), str)][:35]
        return {"configured": True, "online": True, "models": models}
    except (LMStudioError, TypeError, AttributeError):
        return {"configured": True, "online": False}


def chat(messages, model, max_tokens=1000):
    if not configured():
        raise LMStudioError("Configurá SKY_LMSTUDIO_ENABLED=1 y SKY_LMSTUDIO_MODEL.")
    if not isinstance(model, str) or not model.strip() or len(model) > 150:
        raise LMStudioError("Modelo local inválido.")
    rows = []
    for row in messages:
        if not isinstance(row, dict) or row.get("role") not in ("system", "user", "assistant"):
            raise LMStudioError("Rol de conversación inválido.")
        content = row.get("content")
        if not isinstance(content, str) or len(content) > 16000:
            raise LMStudioError("Contenido de conversación inválido.")
        rows.append({"role": row["role"], "content": content})
    if not rows or rows[-1]["role"] != "user":
        raise LMStudioError("Se requiere solicitud final.")
    result = _request("POST", "/v1/chat/completions", {
        "model": model, "messages": rows, "max_tokens": max_tokens,
        "temperature": 0.35, "stream": False
    })
    try:
        answer = result["choices"][0]["message"]["content"]
    except (TypeError, IndexError, KeyError) as exc:
        raise LMStudioError("El modelo no entregó una respuesta.") from exc
    if not isinstance(answer, str) or not answer.strip():
        raise LMStudioError("El modelo no generó texto.")
    return answer.strip()
