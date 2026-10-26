"""Comandos de ventanas que el servicio de voz deriva al HUD autenticado.

No navega a sitios, no inicia apps, no sustituye permisos del agente de Windows.
"""
from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "local_data" / "sky_window_actions.sqlite3"


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", str(text).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", t)).strip()


def parse_window_request(text: str) -> dict | None:
    t = re.sub(r"^(?:(?:oye|hey|mira) )*(?:sky )?", "", normalize(text))
    mode = "normal"
    m = re.search(r"\s+(?:(?:en|a|de) )?(?:(?:una|la) )?(?:ventana|ventanita) (?:(?:modo|tamano) )?(minimizada|minimizar|maximizada|maximizar|mini|pequena|normal|grande|pantalla completa)$", t)
    if m:
        v = m.group(1)
        mode = ("mini" if v in ("mini", "pequena") else
                "minimized" if v in ("minimizada", "minimizar") else
                "max" if v in ("maximizada", "maximizar", "grande") else
                "fullscreen" if v == "pantalla completa" else "normal")
        t = t[:m.start()].strip()
    m = re.match(r"^(minimiza|minimizar|maximiza|maximizar|restaura|restaurar|normaliza|cierra|cerrar) (?:(?:(?:la|el) )?(?:(?:ventana|reproductor|modulo) )?(?:de )?)?(youtube|reproductor|video|buscador|busqueda|buscar)$", t)
    if m:
        verb = m.group(1)
        return {"kind":"window_control", "target":"player" if m.group(2) in ("youtube","reproductor","video") else "search",
                "mode": ("minimized" if verb.startswith("minim") else "max" if verb.startswith("maxim") else "close" if verb.startswith("cierr") else "normal")}
    m = re.match(r"^(?:(?:abre|abri|abrir|activa|muestra) (?:el )?youtube (?:y )?)?(?:pon|pone|ponme|reproduce|reproducir|reproduci|busca|buscame|quiero escuchar|quiero ver) (?:(?:(?:la|el|un) )?(?:musica|cancion|canciones|tema|temas|video|videos) (?:de )?)?(.+)$", t)
    if m and m.group(1) and (
        re.match(r"^(?:abre|abri|abrir|activa|muestra) (?:el )?youtube\b", t) or
        re.match(r"^(?:pon|pone|ponme|reproduce|reproducir|reproduci|quiero escuchar|quiero ver) (?:la |el |un )?(?:musica|cancion|canciones|tema|temas|video|videos)\b", t)
    ) and not re.match(r"^(?:volumen|alarma|recordatorio|temporizador)\b", m.group(1)):
        return {"kind":"youtube","query":m.group(1)[:120],"mode":mode}
    if re.match(r"^(?:abre|abri|abrir|activa|activar|inicia|iniciar|muestra|mostra)(?: (?:el|la))? (?:(?:modulo|panel|herramienta) (?:de )?)?(?:buscar|buscador|busqueda|search)(?: web)?$", t):
        return {"kind":"search","provider":"web","mode":mode}
    if re.match(r"^(?:abre|abri|abrir|muestra) (?:el )?youtube$", t):
        return {"kind":"search","provider":"youtube","mode":mode}
    return None


def _connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB, timeout=5)
    conn.execute("""CREATE TABLE IF NOT EXISTS requests
        (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, target TEXT NOT NULL,
         mode TEXT NOT NULL, query TEXT NOT NULL, created REAL NOT NULL)""")
    return conn


def publish(request: dict) -> int:
    if request["kind"] not in ("youtube","search","window_control") or request["mode"] not in (
        "mini","normal","max","fullscreen","minimized","close"
    ):
        raise ValueError("Orden HUD no permitida")
    with _connect() as db:
        cursor = db.execute("INSERT INTO requests(kind,target,mode,query,created) VALUES(?,?,?,?,?)",
            (request["kind"],request.get("target",request.get("provider","")),
             request["mode"],request.get("query","")[:120],time.time()))
        db.execute("DELETE FROM requests WHERE created < ?", (time.time() - 3600,))
        return int(cursor.lastrowid)


def latest() -> int:
    with _connect() as db:
        row = db.execute("SELECT COALESCE(MAX(id),0) FROM requests").fetchone()
        return int(row[0])


def since(cursor: int) -> list[dict]:
    with _connect() as db:
        rows = db.execute("SELECT id,kind,target,mode,query FROM requests WHERE id>? AND created>? ORDER BY id LIMIT 20",
            (max(0, cursor),time.time() - 180)).fetchall()
        return [{"id":i,"kind":kind,"target":target,"mode":mode,"query":query} for i,kind,target,mode,query in rows]
