"""Recuperación semántica opcional de temas de experiencias mediante Ollama LOCAL.

Nunca envía pedidos del usuario, textos privados, archivos, código ni errores al
modelo: sólo las DESCRIPCIONES ESTÁTICAS de categorías definidas por SKY.
Sin Ollama o sin activación explícita, retorna None y se usa recuperación
determinista existente. No actualiza modelos ni concede permisos.
"""
from __future__ import annotations

import ipaddress
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache

TOPIC_DESCRIPTIONS = {
    "calculo": "aritmética matemáticas ecuaciones porcentajes cálculos numéricos",
    "texto": "redacción corrección lingüística traducción resúmenes de textos",
    "fechas": "agenda planificación temporal calendarios horarios y fechas",
    "formato": "formato estructurado JSON CSV tablas y listas",
    "datos": "análisis de datos estadísticas indicadores y promedios",
    "general": "otras solicitudes generales sin especialidad identificada",
}
MAX_BYTES = 150_000
MAX_DIMENSIONS = 2048


def _endpoint() -> str:
    value = os.getenv("SKY_REFLECTIVE_OLLAMA_URL", "http://127.0.0.1:11434")
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "http" or parsed.username or parsed.password or
            parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("Sólo se admite un origen HTTP local sin credenciales.")
    host = parsed.hostname
    if host != "localhost":
        try:
            if not host or not ipaddress.ip_address(host).is_loopback:
                raise ValueError("El motor semántico debe ejecutarse localmente.")
        except ValueError as exc:
            raise ValueError("El motor semántico debe ejecutarse localmente.") from exc
    port = parsed.port or 11434
    if not (1 <= port <= 65535):
        raise ValueError("Puerto no válido.")
    return f"http://127.0.0.1:{port}"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def enabled() -> bool:
    return os.getenv("SKY_REFLECTIVE_SEMANTIC", "0").strip().lower() in ("1", "true", "yes")


def _normalize(values: object) -> list[list[float]]:
    if not isinstance(values, list) or len(values) != len(TOPIC_DESCRIPTIONS):
        raise ValueError("Cantidad inesperada de embeddings.")
    parsed = []
    dimension = None
    for value in values:
        if not isinstance(value, list) or not (8 <= len(value) <= MAX_DIMENSIONS):
            raise ValueError("Dimensiones inválidas.")
        if dimension is None:
            dimension = len(value)
        if len(value) != dimension:
            raise ValueError("Dimensiones incompatibles.")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
            raise ValueError("Embeddings no numéricos.")
        length = math.sqrt(sum(v*v for v in value))
        if length <= 1e-12:
            raise ValueError("Embedding vacío.")
        parsed.append([v/length for v in value])
    return parsed


@lru_cache(maxsize=2)
def _vectors(endpoint: str, model: str) -> dict[str, list[float]]:
    # Las únicas cadenas enviadas a Ollama están definidas en código propio.
    payload = json.dumps({
        "model": model, "input": list(TOPIC_DESCRIPTIONS.values()),
        "truncate": True,
    }).encode("utf-8")
    request = urllib.request.Request(endpoint + "/api/embed", data=payload,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
    # Sin proxy ni redirecciones; el host validado es loopback.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    with opener.open(request, timeout=2.5) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Respuesta de embeddings excesiva.")
    data = json.loads(raw)
    vectors = _normalize(data.get("embeddings") if isinstance(data, dict) else None)
    return dict(zip(TOPIC_DESCRIPTIONS, vectors))


def related_topics(topic: str) -> dict[str, float] | None:
    """Retorna similitud consultiva entre categorías sin tocar solicitudes privadas."""
    if topic not in TOPIC_DESCRIPTIONS:
        raise ValueError("Categoría no reconocida.")
    if not enabled():
        return None
    model = os.getenv("SKY_REFLECTIVE_EMBED_MODEL", "nomic-embed-text").strip()
    if not re.fullmatch(r"[a-zA-Z0-9_./:-]{1,100}", model):
        return None
    try:
        vectors = _vectors(_endpoint(), model)
    except (OSError, ValueError, TypeError, urllib.error.HTTPError, json.JSONDecodeError):
        return None
    reference = vectors[topic]
    return {name: round(sum(a*b for a,b in zip(reference, vec)), 6)
            for name, vec in vectors.items()}


def capabilities() -> dict:
    return {
        "enabled": enabled(), "provider": "ollama_local_optional",
        "raw_user_text_sent": False, "static_category_descriptions_only": True,
        "embeddings_persisted": False, "external_cloud": False,
        "fallback": "deterministic_feature_hashing",
        "requires_installed_embedding_model": True,
    }
