"""Búsqueda de metadatos multimedia y conversión local de imágenes."""
import json
from io import BytesIO
from urllib import parse, request


def catalogo_itunes(busqueda, tipo="song"):
    if tipo not in ("song", "movie"):
        raise ValueError("Tipo multimedia no soportado")
    query = parse.urlencode({"term": busqueda.strip()[:90], "media": "music" if tipo == "song" else "movie",
                             "entity": tipo, "limit": 12, "country": "US"})
    req = request.Request("https://itunes.apple.com/search?" + query,
                          headers={"User-Agent": "NeuralTPersonal/4.0"})
    with request.urlopen(req, timeout=10) as r:
        blob = r.read(1_000_001)
    if len(blob) > 1_000_000:
        raise ValueError("Respuesta demasiado grande")
    datos=json.loads(blob)
    return [{"titulo": x.get("trackName", x.get("collectionName", "Sin título")),
             "artista": x.get("artistName", ""), "genero": x.get("primaryGenreName", ""),
             "fecha": x.get("releaseDate", "")[:10],
             "enlace": x.get("trackViewUrl", x.get("collectionViewUrl", ""))}
            for x in datos.get("results", [])]


def convertir_imagen(contenido, formato="WEBP", calidad=85, ancho_maximo=1920):
    if formato not in ("WEBP", "PNG", "JPEG"):
        raise ValueError("Formato inválido")
    if len(contenido) > 15_000_000:
        raise ValueError("Máximo 15 MB")
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 24_000_000
    with Image.open(BytesIO(contenido)) as im:
        im = ImageOps.exif_transpose(im)
        if im.width * im.height > 24_000_000:
            raise ValueError("Imagen demasiado grande")
        im.thumbnail((ancho_maximo, ancho_maximo), Image.Resampling.LANCZOS)
        if formato == "JPEG":
            im=im.convert("RGB")
        elif formato == "WEBP":
            im=im.convert("RGBA" if "A" in im.getbands() else "RGB")
        out=BytesIO()
        opciones={"quality": calidad, "optimize": True} if formato != "PNG" else {"optimize": True}
        im.save(out, format=formato, **opciones)
        return out.getvalue(), im.size


# Catálogo curado de videos con incrustación autorizada (status.embeddable = True)
VERIFIED_EMBEDDABLE_CATALOG = {
    "queen": [
        {"id": "vbvyNnw8Qjg", "title": "Queen – Bohemian Rhapsody (Live Aid 1985)", "embeddable": True},
        {"id": "frdBb9Slu1A", "title": "Queen – Live Aid 1985 Full Concert", "embeddable": True},
        {"id": "PadKCVBIN94", "title": "Queen – Bohemian Rhapsody (1981 Live)", "embeddable": True},
        {"id": "HgzGwKwLmgM", "title": "Queen – Don't Stop Me Now", "embeddable": True},
        {"id": "kijpcUv-b8M", "title": "Queen – Somebody To Love", "embeddable": True},
    ],
    "bohemian rhapsody": [
        {"id": "vbvyNnw8Qjg", "title": "Queen – Bohemian Rhapsody (Live Aid 1985)", "embeddable": True},
        {"id": "PadKCVBIN94", "title": "Queen – Bohemian Rhapsody (1981 Live Video)", "embeddable": True},
        {"id": "frdBb9Slu1A", "title": "Queen – Live Aid 1985 Full Concert", "embeddable": True},
    ],
    "musica": [
        {"id": "vbvyNnw8Qjg", "title": "Queen – Bohemian Rhapsody (Live Aid 1985)", "embeddable": True},
        {"id": "HgzGwKwLmgM", "title": "Queen – Don't Stop Me Now", "embeddable": True},
        {"id": "kijpcUv-b8M", "title": "Queen – Somebody To Love", "embeddable": True},
    ]
}

# Videos conocidos con incrustación bloqueada por el propietario (Error 150/101 de YouTube)
KNOWN_EMBEDDING_BLOCKED = {
    "fJ9rUzIMcZQ",  # Queen – Bohemian Rhapsody (Official Remastered Video, UMG bloquea iframes de terceros)
}


def _search_youtube_api(query: str, api_key: str) -> list[dict]:
    """Busca mediante YouTube Data API y filtra status.embeddable real.

    search.list(videoEmbeddable=true) no sustituye videos.list(status).
    Una marca positiva tampoco anula Content ID ni restricciones del reproductor.
    """
    import re

    if not api_key or not str(query).strip():
        return []

    def consultar(recurso: str, params: dict) -> dict:
        url = "https://www.googleapis.com/youtube/v3/" + recurso + "?" + parse.urlencode(params)
        req = request.Request(url, headers={"User-Agent": "SKY-IA/12.6"})
        with request.urlopen(req, timeout=7) as respuesta:
            cuerpo = respuesta.read(1_000_001)
        if len(cuerpo) > 1_000_000:
            raise ValueError("YouTube devolvió una respuesta demasiado grande")
        return json.loads(cuerpo.decode("utf-8"))

    busqueda = consultar("search", {
        "part": "snippet",
        "type": "video",
        "videoEmbeddable": "true",
        "maxResults": 15,
        "q": str(query).strip()[:120],
        "key": api_key,
    })
    candidatos = []
    for item in busqueda.get("items", []):
        vid = (item.get("id") or {}).get("videoId", "")
        if (isinstance(vid, str) and re.fullmatch(r"[A-Za-z0-9_-]{11}", vid)
                and vid not in KNOWN_EMBEDDING_BLOCKED and vid not in candidatos):
            candidatos.append(vid)
    if not candidatos:
        return []

    detalles = consultar("videos", {
        "part": "status,snippet,contentDetails",
        "id": ",".join(candidatos),
        "key": api_key,
    })
    validados = {}
    for item in detalles.get("items", []):
        vid = item.get("id")
        status = item.get("status") or {}
        if (vid not in candidatos or status.get("embeddable") is not True
                or status.get("privacyStatus") != "public"):
            continue
        restriccion = ((item.get("contentDetails") or {}).get("regionRestriction") or {})
        import os
        region = os.getenv("SKY_YOUTUBE_REGION", "NI").strip().upper()
        if len(region) == 2 and region.isalpha():
            if region in restriccion.get("blocked", []):
                continue
            if "allowed" in restriccion and region not in restriccion["allowed"]:
                continue
        snippet = item.get("snippet") or {}
        titulo = str(snippet.get("title") or "").strip()
        if titulo:
            validados[vid] = {
                "id": vid,
                "title": titulo[:140],
                "channel": str(snippet.get("channelTitle") or "")[:100],
                "embeddable": True,
                "url": f"https://www.youtube.com/watch?v={vid}",
            }
    return [validados[vid] for vid in candidatos if vid in validados][:6]


def resolve_youtube_video(busqueda: str) -> dict:
    """Compatibilidad: resolver por Data API, nunca scraping ni videos sustitutos.

    El catálogo histórico permanece disponible como datos legados, pero no
    demuestra disponibilidad actual ni permiso para incrustar una canción.
    """
    import os

    q = str(busqueda or "").strip()[:120]
    url_busqueda = "https://www.youtube.com/results?search_query=" + parse.quote_plus(q)
    vacio = {
        "url": url_busqueda,
        "video_id": "",
        "embed_url": "",
        "titulo": q,
        "candidates": [],
        "embeddable": False,
        "source": "youtube_api_required",
        "motivo": "Para buscar videos desde SKY configurá YOUTUBE_API_KEY. "
                  "Usá YouTube oficial si no permite incrustación.",
    }
    if not q:
        return {**vacio, "motivo": "Indicá el nombre del video o artista."}
    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return vacio
    try:
        encontrados = _search_youtube_api(q, api_key)
    except Exception:
        return {**vacio, "source": "youtube_api_error",
                "motivo": "No respondió la YouTube Data API. Revisá cuota, red y clave."}
    if not encontrados:
        return {**vacio, "source": "youtube_no_embed",
                "motivo": "Sin videos públicos incrustables autorizados en la región configurada."}
    primero = encontrados[0]
    vid = primero["id"]
    return {
        "url": primero["url"],
        "video_id": vid,
        "embed_url": f"https://www.youtube.com/embed/{vid}?playsinline=1&enablejsapi=1",
        "titulo": primero["title"],
        "candidates": encontrados,
        "embeddable": True,
        "source": "youtube_api_v3",
    }
