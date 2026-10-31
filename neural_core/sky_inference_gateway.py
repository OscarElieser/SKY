"""SKY-owned, Ollama-only inference gateway for authenticated mobile chat.

This is the SERVER execution engine, not a foundation model trained by SKY.
It makes no cloud requests, never executes tools and stores no prompt text.
Each configured worker is restricted to loopback; public Ollama ports and
arbitrary user-supplied URLs are deliberately unsupported.
"""
from __future__ import annotations

from collections import deque
import json
import os
import threading
import time
import uuid
from urllib import error, parse, request

_MAX_RESPONSE_BYTES = 262_144
_MAX_WORKERS = 8
_LOCK = threading.RLock()
_GATE_LOCK = threading.Lock()
_GATE_LIMIT = 2
_GATE = threading.BoundedSemaphore(_GATE_LIMIT)
_FAILURES: dict[str, tuple[int, float]] = {}
_WORKER_CURSOR = 0
_SAMPLES: deque[float] = deque(maxlen=300)
_TOTAL = {"ok": 0, "failed": 0, "busy": 0}
_TOTAL_TOKENS = {"input": 0, "output": 0}


class InferenceUnavailable(RuntimeError):
    pass


class InferenceBusy(RuntimeError):
    pass


def _workers() -> tuple[str, ...]:
    raw = os.getenv("SKY_INFERENCE_WORKERS", "http://127.0.0.1:11434")
    entries = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    if not entries or len(entries) > _MAX_WORKERS:
        raise InferenceUnavailable("Configuración de workers inválida")
    out: list[str] = []
    for base in entries:
        parsed = parse.urlsplit(base)
        # Only local workers; do not expose Ollama, accept credentials or
        # permit an accidental SSRF through the model worker configuration.
        if (parsed.scheme != "http" or
                parsed.hostname not in ("localhost", "127.0.0.1", "::1") or
                parsed.username is not None or parsed.password is not None or
                parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise InferenceUnavailable("Los workers Ollama deben usar loopback HTTP")
        try:
            port = parsed.port
        except ValueError as exc:
            raise InferenceUnavailable("Puerto de worker inválido") from exc
        if not port or port < 1024:
            raise InferenceUnavailable("Puerto de worker no admitido")
        if base not in out:
            out.append(base)
    return tuple(out)


def _model() -> str:
    # Compatible with the existing owner's selected model but still pinned
    # to a server-side variable, never arbitrary text supplied by Android.
    name = os.getenv("SKY_INFERENCE_MODEL") or os.getenv("OLLAMA_MODEL", "llama3.2")
    name = name.strip()
    if not name or len(name) > 128 or not all(
            c.isalnum() or c in "._:-/" for c in name):
        raise InferenceUnavailable("Modelo local configurado inválido")
    return name


def _context_window() -> int:
    """Server operator chooses the actual KV-cache budget; never trust Android."""
    raw = os.getenv("SKY_INFERENCE_NUM_CTX", "16384")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise InferenceUnavailable("Contexto Ollama mal configurado") from exc
    if value not in (8192, 16384, 32768):
        raise InferenceUnavailable("Contexto Ollama debe ser 8192, 16384 o 32768")
    return value


def _read_limited(response) -> dict:
    raw = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise InferenceUnavailable("Respuesta de inferencia excesivamente grande")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise InferenceUnavailable("El motor devolvió JSON inválido") from exc
    if not isinstance(value, dict):
        raise InferenceUnavailable("Respuesta del motor inválida")
    return value


def _active_worker() -> str:
    global _WORKER_CURSOR
    bases = _workers()
    with _LOCK:
        now = time.monotonic()
        for offset in range(len(bases)):
            idx = (_WORKER_CURSOR + offset) % len(bases)
            worker = bases[idx]
            count, until = _FAILURES.get(worker, (0, 0.0))
            if count < 3 or now >= until:
                _WORKER_CURSOR = idx + 1
                return worker
    raise InferenceUnavailable("Todos los workers locales están en recuperación")


def _record(ok: bool, duration_ms: float, prompt_tokens: int = 0,
            output_tokens: int = 0, busy: bool = False) -> None:
    with _LOCK:
        _TOTAL["busy" if busy else "ok" if ok else "failed"] += 1
        if not busy:
            _SAMPLES.append(round(duration_ms, 1))
        if ok:
            _TOTAL_TOKENS["input"] += max(0, prompt_tokens)
            _TOTAL_TOKENS["output"] += max(0, output_tokens)


def _worker_result(worker: str, success: bool) -> None:
    with _LOCK:
        if success:
            _FAILURES.pop(worker, None)
        else:
            failed, _ = _FAILURES.get(worker, (0, 0))
            failed += 1
            _FAILURES[worker] = (failed, time.monotonic() + 30 if failed >= 3 else 0.0)


def readiness() -> dict:
    """Read-only health. A model in /api/tags is NOT proof of generation."""
    model = _model()
    workers = _workers()
    healthy = 0
    for worker in workers:
        try:
            with request.urlopen(worker + "/api/tags", timeout=1.5) as response:
                if response.status != 200:
                    continue
                tags = _read_limited(response).get("models", [])
            if isinstance(tags, list) and any(
                    isinstance(m, dict) and
                    (m.get("name") == model or
                     (":" not in model and m.get("name") == model + ":latest"))
                    for m in tags):
                healthy += 1
        except (OSError, ValueError, InferenceUnavailable, TypeError):
            continue
    return {"local_ollama_ready": healthy > 0,
            "ready_workers": healthy, "configured_workers": len(workers),
            "model_output_verified": False}


def generate(messages: list[dict], *, max_output_tokens: int = 1200) -> dict:
    """One bounded request against a local Ollama worker, no cloud fallback.

    Does not retry on timeout/disconnect because the first worker may already
    have generated a response and a retry could double server load/cost.
    """
    if not isinstance(messages, list) or len(messages) not in range(1, 11):
        raise ValueError("Historial del chat fuera de límites")
    for message in messages:
        if (not isinstance(message, dict) or
                message.get("role") not in ("system", "user", "assistant") or
                not isinstance(message.get("content"), str) or
                not 1 <= len(message["content"]) <= (
                    32_000 if message["role"] == "user" else 4000)):
            raise ValueError("Mensaje de inferencia inválido")
    if not isinstance(max_output_tokens, int) or not 1 <= max_output_tokens <= 4096:
        raise ValueError("Presupuesto de respuesta inválido")
    context_window = _context_window()
    # Conservative byte-based preflight. Exact tokenization depends on model;
    # this never claims a long prompt fits a smaller physical context.
    if any(len(m["content"]) > 16_000 for m in messages if m["role"] == "user") and context_window < 32768:
        raise ValueError("Consulta superior a 16K requiere SKY_INFERENCE_NUM_CTX=32768")
    estimated_tokens = sum((len(m["content"].encode("utf-8")) + 1) // 2 for m in messages)
    if estimated_tokens + max_output_tokens + 512 > context_window:
        raise ValueError("Texto e historial exceden el contexto configurado; dividí la consulta")
    extended = max_output_tokens > 2048 or any(
        len(m["content"]) > 16_000 for m in messages if m["role"] == "user")
    # A process-local bound; production must add a shared cluster admission
    # controller or each replica may exceed the physical GPU's capacity.
    if not _GATE.acquire(blocking=False):
        _record(False, 0.0, busy=True)
        raise InferenceBusy("SKY API está atendiendo otras consultas; reintentá luego")
    worker = ""
    started = time.monotonic()
    try:
        worker = _active_worker()
        payload = json.dumps({
            "model": _model(), "messages": messages, "stream": False,
            "options": {"num_predict": max_output_tokens, "num_ctx": context_window},
            "keep_alive": "5m",
        }, ensure_ascii=False).encode("utf-8")
        if len(payload) > 150_000:
            raise ValueError("La solicitud supera el presupuesto seguro de entrada")
        req = request.Request(worker + "/api/chat", data=payload, method="POST",
                              headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=190.0 if extended else 68.0) as response:
                data = _read_limited(response)
        except (error.HTTPError, error.URLError, TimeoutError, OSError) as exc:
            _worker_result(worker, False)
            raise InferenceUnavailable("Modelo Ollama no disponible o demasiado lento") from exc
        answer = data.get("message", {})
        answer = answer.get("content") if isinstance(answer, dict) else None
        if data.get("done") is not True or not isinstance(answer, str) or not answer.strip():
            _worker_result(worker, False)
            raise InferenceUnavailable("El modelo no produjo una respuesta válida")
        if len(answer) > 60_000:
            _worker_result(worker, False)
            raise InferenceUnavailable("La respuesta supera el límite seguro")
        _worker_result(worker, True)
        input_tokens = max(0, int(data.get("prompt_eval_count", 0) or 0))
        output_tokens = max(0, int(data.get("eval_count", 0) or 0))
        duration = round((time.monotonic() - started) * 1000, 1)
        _record(True, duration, input_tokens, output_tokens)
        return {
            "respuesta": answer.strip(), "proveedor": "ollama", "nube": False,
            "acciones_ejecutadas": False, "respaldo_local": False,
            "respuesta_incompleta": data.get("done_reason") == "length",
            "operacion": uuid.uuid4().hex,
            "metricas": {"duracion_ms": duration,
                         "tokens_entrada": input_tokens,
                         "tokens_salida": output_tokens,
                         "contexto_tokens": context_window},
        }
    except (InferenceBusy, InferenceUnavailable, ValueError):
        _record(False, (time.monotonic() - started) * 1000)
        raise
    finally:
        _GATE.release()


def metrics_snapshot() -> dict:
    """Aggregates only; no raw prompts, IPs, tokens or user identifiers."""
    with _LOCK:
        series = sorted(_SAMPLES)
        p95 = series[max(0, (95 * len(series) + 99) // 100 - 1)] if series else None
        return {"requests": dict(_TOTAL),
                "tokens": dict(_TOTAL_TOKENS),
                "latencia_p95_ms": p95,
                "latency_samples": len(series),
                "scope": "one process only; not cluster SLO"}
