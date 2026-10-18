"""Noticias RSS públicas bajo solicitud, sin raspado masivo ni fuentes inventadas."""
from urllib import request, parse
from xml.etree import ElementTree as ET
from datetime import datetime, timezone


def noticias(tema="inteligencia artificial", limite=12):
    termino = tema.strip()[:100]
    if not termino:
        raise ValueError("Escribe un tema")
    query = parse.urlencode({"q": termino, "hl": "es-419", "gl": "NI", "ceid": "NI:es-419"})
    url = "https://news.google.com/rss/search?" + query
    req = request.Request(url, headers={"User-Agent": "Mozilla/5.0 (NeuralT/4.0; RSS reader)"})
    with request.urlopen(req, timeout=12) as r:
        b = r.read(1_000_001)
    if len(b) > 1_000_000:
        raise ValueError("El RSS de noticias supera el máximo permitido")
    raiz = ET.fromstring(b)
    items = []
    for item in raiz.findall(".//channel/item")[:min(limite, 20)]:
        titulo = item.findtext("title", default="Sin título")
        enlace = item.findtext("link", default="")
        fecha = item.findtext("pubDate", default="Fecha no proporcionada")
        fuente = item.find("source")
        if not enlace.startswith("https://"):
            continue
        items.append({"titular": titulo, "enlace": enlace, "fecha": fecha,
                      "fuente": fuente.text if fuente is not None else "Google News RSS"})
    return items
