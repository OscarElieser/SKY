"""Interpretación limitada de peticiones de borrador social por voz y texto.

Nunca publica desde el chat, ni ejecuta likes. Solo prepara texto generado
por SKY con el modelo elegido y lo devuelve como borrador para aprobación.
"""
import re
import unicodedata

ALIASES = {
    "x": "x", "twitter": "x", "facebook": "facebook",
    "instagram": "instagram", "tiktok": "tiktok", "tik tok": "tiktok",
    "threads": "threads", "snapchat": "snapchat",
}


def parse(text: str) -> dict | None:
    if not isinstance(text, str) or len(text) > 1600:
        return None
    simple = unicodedata.normalize("NFKD", text)
    simple = "".join(c for c in simple if not unicodedata.combining(c)).casefold()
    pattern = (r"^\s*(?:(?:oye|hola|hey)\s+)?(?:sky[\s,:-]+)?"
               r"(?:prepara|redacta|escribe|crea)\s+(?:una?\s+)?"
               r"(?:publicacion|post|borrador)\s+(?:para|en)\s+"
               r"(x|twitter|facebook|instagram|tiktok|tik tok|threads|snapchat)"
               r"\s+(?:sobre|acerca de|de|:)\s+(.{8,1200})\s*$")
    match = re.fullmatch(pattern, simple, flags=re.I | re.S)
    if not match:
        return None
    # Use original text's subject when possible; accents and capitalization
    # may be lost in normalized parsing, but instructions remain semantic.
    original_match = re.search(r"\s(?:sobre|acerca de|de|:)\s+(.{8,1200})\s*$",
                               text, flags=re.I | re.S)
    topic = original_match.group(1).strip() if original_match else match.group(2).strip()
    return {"platform": ALIASES[match.group(1)], "topic": topic}


def prepare(text: str, provider: str = "auto") -> dict | None:
    intent = parse(text)
    if intent is None:
        return None
    try:
        from metaverse.social_hub_api import generate_draft
        result = generate_draft(intent["platform"], intent["topic"],
                                "natural, cercano, original y apropiado para la audiencia",
                                provider=provider)
        return {
            "tipo": "respuesta", "proveedor": "sky-social",
            "mensaje": "Este es el borrador preparado por SKY; aún no se ha publicado:\n\n"
                       + result["body"],
            "social_draft_id": result["id"],
            "publicado": False, "requiere_aprobacion": True,
        }
    except Exception:
        return {"tipo": "error", "proveedor": "sky-social",
                "mensaje": "No se pudo generar el borrador con el motor de IA configurado. "
                           "Revisá el modelo o su conexión; no se publicó nada."}
