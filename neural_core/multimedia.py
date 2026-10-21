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


def resolve_youtube_video(busqueda: str) -> dict:
    """Resuelve la consulta a un video real de YouTube con su video_id y URL lista para reproducir."""
    busqueda = (busqueda or "").strip()
    if not busqueda:
        return {
            "url": "https://www.youtube.com",
            "video_id": "",
            "embed_url": "https://www.youtube.com/embed/fJ9rUzIMcZQ",
            "titulo": "YouTube"
        }
    import re
    query_codificada = parse.quote_plus(busqueda)
    search_url = f"https://www.youtube.com/results?search_query={query_codificada}"
    video_id = ""
    try:
        req = request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        with request.urlopen(req, timeout=4) as r:
            html = r.read(300_000).decode("utf-8", errors="ignore")
            ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
            if ids:
                video_id = ids[0]
    except Exception:
        pass

    if video_id:
        return {
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "video_id": video_id,
            "embed_url": f"https://www.youtube.com/embed/{video_id}?autoplay=1",
            "titulo": busqueda
        }
    return {
        "url": search_url,
        "video_id": "",
        "embed_url": "",
        "titulo": busqueda
    }

