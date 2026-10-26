"""Read-only public news verification for time-sensitive SKY questions.

Uses SKY's already integrated Google News RSS provider (actualidad.noticias).
Does not pretend RSS headlines are live vote totals or full-text articles.
No arbitrary URL fetching, model calls, installed dependencies or device actions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import os
import re
import unicodedata

PUBLIC_TOPICS = re.compile(
    r"\b(balon de oro|ballon d.or|votacion(?:es)?|resultado(?:s)?|"
    r"eleccion(?:es)?|noticia(?:s)?|premio(?:s)?|partido(?:s)?|"
    r"mundial|liga|futbol|champions|deporte(?:s)?)\b", re.I
)
RECENCY = re.compile(
    r"\b(hoy|ahora|actualmente|ultimo(?:s|a|as)?|ultima(?:s)?|"
    r"en vivo|en directo|tiempo real|reciente(?:s)?|"
    r"esta tarde|este dia|esta semana|como van|que paso)\b", re.I
)
OPEN_OR_PRIVATE = re.compile(
    r"^(?:abre|abri|abrir|busca en|reproduce|envia|manda|llama|"
    r"borra|escribe|guarda|instala|programa|edita|publica)\b", re.I
)
SENSITIVE = re.compile(
    r"\b(mi correo|mis correos|mis datos|mi cuenta|mi perfil|"
    r"mi telefono|mi numero|mi ubicacion|mis mensajes|mi contrasena)\b", re.I
)


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(c for c in value if not unicodedata.combining(c))


def is_current_public_question(text: str) -> bool:
    if not isinstance(text, str) or not (10 <= len(text.strip()) <= 260):
        return False
    q = _fold(text)
    if SENSITIVE.search(q) or OPEN_OR_PRIVATE.search(q):
        return False
    return bool(PUBLIC_TOPICS.search(q) and RECENCY.search(q))


def _internet_enabled() -> bool:
    from .providers import local_only
    # SKY_INTERNET is the existing internet permission; SKY_LOCAL_ONLY
    # is stricter and forbids all external lookups.
    return not local_only() and os.getenv("SKY_INTERNET", "1").strip() != "0"


def _rss_date(raw: str):
    try:
        dt = parsedate_to_datetime(str(raw))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def _topic(text: str) -> tuple[str, bool]:
    q = _fold(text)
    if "balon de oro" in q or "ballon d" in q:
        year = re.search(r"\b20\d{2}\b", q)
        return "Balón de Oro " + (year.group() if year else str(datetime.now().year)) + " hoy votaciones resultados ceremonia", True
    # News provider already caps length; no names/contact data beyond the
    # constrained public question classifier.
    return " ".join(str(text).split())[:95], False


def _render(items: list[dict], *, topic: str, voting: bool, now: datetime) -> dict:
    recents = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = " ".join(str(item.get("titular") or "").split())[:220]
        link = str(item.get("enlace") or "")
        date = _rss_date(item.get("fecha", ""))
        if not title or not link.startswith("https://") or not date:
            continue
        if date > now + timedelta(minutes=10) or now - date > timedelta(days=7):
            continue
        recents.append((date, title, link, str(item.get("fuente") or "fuente de noticias")[:80]))
    recents.sort(key=lambda v: v[0], reverse=True)
    lines = [
        "Consulté noticias públicas para verificar la actualidad de esta pregunta.",
        "Estos son TITULARES y fechas aportados por Google News RSS; no he leído ni comprobado el texto completo de los artículos.",
    ]
    if recents:
        lines.append("Últimos titulares fechados (hora UTC):")
        for dt, title, link, source in recents[:5]:
            lines.append(f"- {dt.strftime('%Y-%m-%d %H:%M')} UTC · {source}: {title}. Fuente: {link}")
    else:
        lines.append("La consulta no devolvió titulares fechados y verificables de los últimos siete días.")
    if voting:
        lines.append(
            "IMPORTANTE: noticias, encuestas de aficionados y filtraciones NO equivalen al "
            "recuento oficial del jurado del Balón de Oro. No tengo un total de votos "
            "oficial verificado y no voy a inventar posiciones ni porcentajes. "
            "Consultá además https://ballondor.com/ y https://www.uefa.com/ballondor/ "
            "para los resultados oficiales del premio."
        )
    return {
        "tipo": "respuesta",
        "mensaje": "\n\n".join(lines),
        "proveedor": "sky-actualidad-rss",
        "fuentes": [{"titulo": title, "enlace": link,
                     "fecha": dt.isoformat(), "fuente": source}
                    for dt, title, link, source in recents[:5]],
        "consulta_externa": True,
        "contenido_verificado": "solo_metadatos_rss",
    }


def maybe_answer(text: str) -> dict | None:
    """Return a grounded answer for explicit *public*, time-sensitive news.

    Return None when an unrelated question should follow SKY's usual route.
    Fail closed with a visible limitation when Internet is disabled/unavailable.
    """
    if not is_current_public_question(text):
        return None
    if not _internet_enabled():
        return {
            "tipo": "respuesta", "proveedor": "sky-actualidad",
            "mensaje": ("Esta pregunta requiere información actual. No consulté "
                        "Internet porque SKY_LOCAL_ONLY=1 o SKY_INTERNET=0 impide "
                        "las conexiones externas. No puedo confirmar los resultados "
                        "actuales sin una fuente autorizada."),
            "consulta_externa": False,
        }
    query, voting = _topic(text)
    try:
        from .actualidad import noticias
        items = noticias(query, limite=8)
    except (OSError, ValueError, TimeoutError, ConnectionError, Exception) as exc:
        # Do not pass network errors into the model as an alleged answer,
        # and do not silently fall back to stale training-time knowledge.
        return {
            "tipo": "respuesta", "proveedor": "sky-actualidad",
            "mensaje": ("Intenté consultar los titulares actuales, pero la fuente "
                        "no respondió. No puedo verificar la información de hoy; "
                        "revisá la conexión de Internet. "
                        "Fuentes oficiales: https://ballondor.com/ "
                        "y https://www.uefa.com/ballondor/."
                        if voting else
                        "Intenté consultar noticias actuales, pero la fuente no respondió. "
                        "No puedo verificar esta noticia ahora."),
            "consulta_externa": False,
            "error_tipo": type(exc).__name__,
        }
    return _render(items, topic=query, voting=voting,
                   now=datetime.now(timezone.utc))
