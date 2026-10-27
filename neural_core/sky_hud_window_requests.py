"""Comandos de ventanas que el servicio de voz deriva al HUD autenticado.

No navega a sitios, no inicia apps, no sustituye permisos del agente de Windows.
"""
from __future__ import annotations

import re
import sqlite3
import time
from contextlib import closing
import unicodedata
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "local_data" / "sky_window_actions.sqlite3"


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", str(text).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", t)).strip()


def _intencion_youtube(frase: str, mode: str) -> dict | None:
    """Reconoce variantes explícitas de escuchar/ver YouTube; no ejecuta acciones.

    Evita reconocer conversaciones genéricas, órdenes a Spotify u operaciones
    ajenas (volumen, alarmas, archivos) como reproducción de YouTube.
    """
    original = frase.strip()
    t = original
    for _ in range(4):
        limpio = re.sub(
            r"^(?:por favor|porfa|si puedes|si podes|podrias|puedes|podes|"
            r"quiero que|quisiera que|necesito que|me ayudas a|"
            r"te pido que|me gustaria que)\s+", "", t)
        if limpio == t:
            break
        t = limpio.strip()

    # La intención explícita "abre YouTube" no implica una canción particular.
    entrada = re.match(
        r"^(?:abre|abri|abrir|abreme|muestra|mostra|entra a|ve a)\s+"
        r"(?:el\s+)?youtube\b(?:\s+(?:y|para|que)\s+)?", t)
    youtube_explicito = entrada is not None
    if entrada:
        t = t[entrada.end():].strip()
        if not t:
            return {"kind": "search", "provider": "youtube", "mode": mode}

    if re.search(r"\s+(?:en|por|desde)\s+(?:el\s+)?spotify$", t):
        return None
    youtube_explicito |= bool(re.search(r"\s+(?:en|por|desde)\s+(?:el\s+)?youtube(?:\s+music)?$", t))
    t = re.sub(r"\s+(?:en|por|desde)\s+(?:el\s+)?youtube(?:\s+music)?$", "", t).strip()

    accion = re.match(
        r"^(?:pon|pone|ponme|poneme|ponmela|ponmelo|pongas|me pongas|ponga|toca|"
        r"reproduce|reproducir|reproduci|reproducime|reproduceme|reproducirme|me reproduzcas|"
        r"reproduzca|reproduzcas|escucha|escuchar|"
        r"quiero escuchar|quiero oir|quiero ver|quiero poner|"
        r"me gustaria escuchar|me gustaria ver|"
        r"busca|buscar|buscame|busca me|encuentra|"
        r"muestrame|mostrame)\s+(.+)$", t)
    if not accion:
        return None
    resto = accion.group(1)
    verbo = t[:accion.start(1)].strip()
    # Consultas genéricas de búsqueda sólo van a YouTube con contexto explícito.
    if verbo in ("busca", "buscar", "buscame", "encuentra") and not (
        youtube_explicito or re.search(r"\b(?:cancion|tema|musica|video|videoclip)\b", resto)
    ):
        return None

    # Extraer la solicitud sin conservar "la canción", "el video", etc.
    resto = re.sub(
        r"^(?:(?:la|el|un|una|los|las)\s+)?"
        r"(?:(?:cancion|canciones|musica|tema|temas|video|videos|"
        r"videoclip|videoclips|cancioncita)(?:\s+(?:de|del))?\s+)", "", resto).strip()
    resto = re.sub(r"^(?:la|el)\s+de\s+", "", resto).strip()
    sin_articulo = re.sub(r"^(?:(?:la|el|los|las|un|una|mi|mis)\\s+)", "", resto)
    if not resto or re.match(r"^(?:volumen|alarma|recordatorio|temporizador|"
                           r"ajustes|configuracion)\b", sin_articulo):
        return None
    return {"kind": "youtube", "query": resto[:120], "mode": mode}



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
    # "en una miniventana flotante" y "en una ventana flotante"
    # son preferencias de presentación, no parte del título de la canción.
    mini = re.search(
        r"\s+(?:(?:en|a|de)\s+)?(?:(?:una|la)\s+)?"
        r"(?:mini\s*ventana|ventanita|ventana)(?:\s+flotante)?$", t)
    if mini:
        mode = "mini"
        t = t[:mini.start()].strip()
    m = re.match(r"^(minimiza|minimizar|maximiza|maximizar|restaura|restaurar|normaliza|cierra|cerrar) (?:(?:(?:la|el) )?(?:(?:ventana|reproductor|modulo) )?(?:de )?)?(youtube|reproductor|video|buscador|busqueda|buscar)$", t)
    if m:
        verb = m.group(1)
        return {"kind":"window_control", "target":"player" if m.group(2) in ("youtube","reproductor","video") else "search",
                "mode": ("minimized" if verb.startswith("minim") else "max" if verb.startswith("maxim") else "close" if verb.startswith("cierr") else "normal")}
    musica = _intencion_youtube(t, mode)
    if musica:
        return musica
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
    with closing(_connect()) as db, db:
        cursor = db.execute("INSERT INTO requests(kind,target,mode,query,created) VALUES(?,?,?,?,?)",
            (request["kind"],request.get("target",request.get("provider","")),
             request["mode"],request.get("query","")[:120],time.time()))
        db.execute("DELETE FROM requests WHERE created < ?", (time.time() - 3600,))
        return int(cursor.lastrowid)


def latest() -> int:
    with closing(_connect()) as db, db:
        row = db.execute("SELECT COALESCE(MAX(id),0) FROM requests").fetchone()
        return int(row[0])


def since(cursor: int) -> list[dict]:
    with closing(_connect()) as db, db:
        rows = db.execute("SELECT id,kind,target,mode,query FROM requests WHERE id>? AND created>? ORDER BY id LIMIT 20",
            (max(0, cursor),time.time() - 180)).fetchall()
        return [{"id":i,"kind":kind,"target":target,"mode":mode,"query":query} for i,kind,target,mode,query in rows]
