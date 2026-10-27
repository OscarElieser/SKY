"""Búsqueda de metadatos de YouTube para el HUD de SKY.

Usa exclusivamente la API oficial para buscar en tiempo de ejecución.
Sin clave ofrece opciones manuales; el parser de HTML se conserva para pruebas
heredadas, pero nunca se invoca automáticamente. No descarga videos.
"""
from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
INITIAL_DATA = re.compile(r"(?:var\s+)?ytInitialData\s*=\s*")


def _texto(valor: object) -> str:
    if not isinstance(valor, dict):
        return ""
    if isinstance(valor.get("simpleText"), str):
        return unescape(valor["simpleText"])
    partes = valor.get("runs", [])
    if isinstance(partes, list):
        return unescape("".join(p.get("text", "") for p in partes if isinstance(p, dict)))
    return ""


def extraer_resultados_web(pagina: str, limite: int = 6) -> list[dict]:
    """Extrae solo videoRenderer reales; jamás inventa títulos o identificadores."""
    coincidencia = INITIAL_DATA.search(pagina)
    if not coincidencia:
        return []
    try:
        datos, _ = json.JSONDecoder().raw_decode(pagina[coincidencia.end():].lstrip())
    except (ValueError, TypeError):
        return []

    encontrados: list[dict] = []
    vistos: set[str] = set()
    pila = [datos]
    nodos = 0
    while pila and len(encontrados) < limite and nodos < 60_000:
        nodo = pila.pop()
        nodos += 1
        if isinstance(nodo, list):
            pila.extend(reversed(nodo))
            continue
        if not isinstance(nodo, dict):
            continue
        video = nodo.get("videoRenderer")
        if isinstance(video, dict):
            identificador = video.get("videoId", "")
            titulo = _texto(video.get("title"))[:140]
            if isinstance(identificador, str) and VIDEO_ID.fullmatch(identificador) and titulo and identificador not in vistos:
                autor = _texto(video.get("ownerText") or video.get("longBylineText"))[:100]
                encontrados.append({"id": identificador, "title": titulo, "channel": autor})
                vistos.add(identificador)
        pila.extend(reversed(list(nodo.values())))
    return encontrados


def buscar_web_publica(consulta: str, limite: int = 6) -> list[dict]:
    """Alternativa sin clave: lee metadatos públicos, sin descargas ni credenciales."""
    url = "https://www.youtube.com/results?" + urlencode({
        "search_query": consulta, "hl": "es"
    })
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
    })
    with urlopen(req, timeout=7) as respuesta:
        contenido = respuesta.read(1_500_001)
    if len(contenido) > 1_500_000:
        raise ValueError("La búsqueda de YouTube excedió el tamaño permitido.")
    return extraer_resultados_web(contenido.decode("utf-8", errors="replace"), limite)


def buscar_videos(consulta: str, clave: str = "", limite: int = 6) -> dict:
    """Devuelve resultados auténticos y distingue videos verificados/no verificados."""
    consulta = " ".join(consulta.split())[:120]
    if not consulta:
        return {"videos": [], "origen": "vacio", "verificado": False,
                "motivo": "Escribí una canción, artista o tema para buscar."}
    # La política oficial de YouTube prohíbe extraer sus páginas mediante scraping.
    # Se conserva el parser antiguo sólo para pruebas/compatibilidad, pero la
    # ejecución de SKY ya no consulta páginas HTML públicas automáticamente.
    if not clave:
        return {"videos": [], "origen": "sin_api_oficial", "verificado": False,
                "motivo": "Para buscar y filtrar videos reproducibles dentro de SKY configurá YOUTUBE_API_KEY "
                          "(YouTube Data API v3) en tu .env. Mientras tanto, podés pegar un enlace "
                          "de YouTube en el reproductor o abrir la búsqueda oficial."}
    try:
        from neural_core.multimedia import _search_youtube_api
        datos = _search_youtube_api(consulta, clave)
        videos = [v for v in datos if isinstance(v, dict) and
                  VIDEO_ID.fullmatch(str(v.get("id", ""))) and v.get("title")
                  and v.get("embeddable") is True][:limite]
        if videos:
            return {"videos": videos, "origen": "youtube_data_api", "verificado": True}
        return {"videos": [], "origen": "sin_resultados", "verificado": False,
                "motivo": "YouTube no devolvió videos públicos incrustables para esta búsqueda. "
                          "Probá otra versión o utilizá el enlace oficial de YouTube."}
    except Exception:
        return {"videos": [], "origen": "error_api_oficial", "verificado": False,
                "motivo": "La YouTube Data API no respondió correctamente. Revisá su habilitación, "
                          "cuota y clave local; podés abrir la búsqueda oficial mientras tanto."}
