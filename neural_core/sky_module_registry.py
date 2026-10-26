"""Catálogo único de módulos heredados de Streamlit y comandos de activación SKY.

La existencia en el catálogo no implica que las dependencias externas estén configuradas.
Ningún módulo pesado se carga al consultar este archivo.
"""
from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from pathlib import Path

MODULES = [
    ("tablero", "🏠 Tablero general (v8.0)", ("tablero general", "tablero")),
    ("universal-v12", "🌐 SKY IA Universal v12.0", ("sky ia universal", "sky universal")),
    ("ia-universal", "🧠 IA universal", ("ia universal",)),
    ("multi-ia", "🧬 Centro multi-IA", ("centro multi ia", "multi ia")),
    ("vision", "👁️ SKY Visión", ("sky vision", "vision")),
    ("studio-3d", "🎨 SKY Studio 3D", ("sky studio 3d", "studio 3d")),
    ("office", "📁 SKY Office Studio", ("sky office studio", "office studio", "office")),
    ("evolucion", "🧬 SKY Evolución", ("sky evolucion", "evolucion")),
    ("herramientas", "🧰 Herramientas SKY", ("herramientas sky", "herramientas")),
    ("live", "🔔 SKY Live", ("sky live",)),
    ("metaverso", "🌐 SKY Metaverso y API", ("sky metaverso", "metaverso y api", "metaverso")),
    ("dispositivos", "🎙️ SKY y dispositivos", ("sky y dispositivos", "dispositivos")),
    ("finanzas", "💰 Finanzas personales", ("finanzas personales", "finanzas")),
    ("ingresos", "🚀 Generar ingresos", ("generar ingresos", "ingresos")),
    ("bolsa", "📈 Bolsa y Bitcoin", ("bolsa y bitcoin", "bolsa", "bitcoin")),
    ("noticias", "📰 Noticias e Internet", ("noticias e internet", "noticias")),
    ("redes", "📣 Redes sociales", ("redes sociales", "sociales")),
    ("musica", "🎵 Música y películas", ("musica y peliculas", "musica", "peliculas")),
    ("imagenes", "🎞️ Imágenes y videos", ("imagenes y videos", "imagenes", "videos")),
    ("seguridad", "🔐 Antivirus y hacking ético", ("antivirus y hacking etico", "antivirus", "hacking etico")),
    ("educacion", "🎓 Educación e investigación", ("educacion e investigacion", "educacion", "investigacion")),
    ("biblioteca", "📚 Biblioteca y memoria", ("biblioteca y memoria", "biblioteca", "memoria")),
    ("baqueano", "🧭 BAQUEANO Control Center", ("baqueano control center", "baqueano")),
    ("transacciones", "🧾 Transacciones", ("transacciones",)),
    ("sensor", "📡 Engine Sensor MLP + GRU", ("engine sensor mlp gru", "engine sensor", "sensor")),
    ("proyectos", "✅ Proyectos y tareas", ("proyectos y tareas", "proyectos", "tareas")),
    ("sports", "⚽ SKY Sports Madridista", ("sky sports madridista", "sports madridista", "madridista")),
]

# Estas vistas ya existen en FastAPI. Las otras conservan de momento la lógica de app.py.
NATIVE_PATHS = {
    "universal-v12": "/sky",
    "studio-3d": "/studio",
    "office": "/office",
    "metaverso": "/world",
}

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()

def all_modules() -> list[dict]:
    return [
        {"id": slug, "label": label, "title": re.sub(r"^[^A-Za-zÁÉÍÓÚÑ0-9]+", "", label), "aliases": list(aa),
         "backend": "hud" if slug in NATIVE_PATHS else "streamlit_on_demand",
         "url": NATIVE_PATHS.get(slug)}
        for slug, label, _ in MODULES
    ]

def lookup(module_id: str) -> dict | None:
    return next((m for m in all_modules() if m["id"] == module_id), None)

def match_activation(frase: str) -> dict | None:
    """Sólo órdenes explícitas de abrir/activar, nunca conversaciones incidentales."""
    phrase = _norm(frase)
    phrase = re.sub(r"^(?:oye |mira |hey )?(?:sky )?", "", phrase)
    if not re.match(r"^(?:activa|activar|abre|abri|abrir|inicia|iniciar|muestra|mostra|mostrame|mostrame|pon|pone|ejecuta)\b", phrase):
        return None
    rest = re.sub(r"^(?:activa|activar|abre|abri|abrir|inicia|iniciar|muestra|mostra|mostrame|pon|pone|ejecuta)\b", "", phrase).strip()
    rest = re.sub(r"^(?:el |la |los |las |modulo |modulos |seccion |secciones |apartado |panel |de |del )+", "", rest)
    aliases = sorted(
        ((len(_norm(a)), _norm(a), slug) for slug, label, aa in MODULES for a in (*aa, label)),
        reverse=True)
    for _, alias, slug in aliases:
        if rest == alias or rest == "modulo " + alias or rest.startswith(alias + " "):
            return lookup(slug)
    return None

DB = Path(__file__).resolve().parent.parent / "local_data" / "sky_module_activation.sqlite3"

def _connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=5)
    con.execute("CREATE TABLE IF NOT EXISTS activations (id INTEGER PRIMARY KEY, module_id TEXT NOT NULL, created REAL NOT NULL)")
    return con

def publish_activation(module_id: str) -> int:
    if lookup(module_id) is None:
        raise ValueError("Módulo desconocido")
    with _connect() as db:
        cur = db.execute("INSERT INTO activations(module_id,created) VALUES(?,?)", (module_id, time.time()))
        db.execute("DELETE FROM activations WHERE created < ?", (time.time() - 3600,))
        return cur.lastrowid

def latest_activation_id() -> int:
    with _connect() as db:
        row = db.execute("SELECT COALESCE(MAX(id),0) FROM activations").fetchone()
        return int(row[0])

def activations_after(cursor: int) -> list[dict]:
    with _connect() as db:
        return [
            {"id": i, "module_id": mid}
            for i, mid in db.execute(
                "SELECT id,module_id FROM activations WHERE id > ? AND created >= ? ORDER BY id LIMIT 20",
                (max(0, cursor), time.time() - 180))
        ]
