"""Comandos creativos de SKY por texto/voz, sin publicar ni ejecutar software.

No intercepta las órdenes genéricas, solo peticiones editoriales claras o
composiciones instrumentales explícitas. Imagen y cine requieren autorización
explícita en el Estudio Creativo y no se autoejecutan desde aquí.
"""
from __future__ import annotations
import re
import unicodedata

LANG = {
    "espanol":"es","ingles":"en","frances":"fr","portugues":"pt",
    "italiano":"it","coreano":"ko","chino":"zh",
    "japones":"ja","aleman":"de"
}
KIND = {
    "cuento":"cuento","historia":"historia","novela":"novela",
    "guion":"guion","pelicula":"pelicula","cancion":"cancion"
}
_PATTERN = re.compile(
    r"^\s*(?:(?:oye|hola)\s+)?(?:sky[,: -]+)?"
    r"(?:escribe|redacta|inventa|crea|creame|haz)\s+"
    r"(?:un|una)?\s*(cuento|historia|novela|guion|pelicula|cancion)"
    r"(?:\s+en\s+(espanol|ingles|frances|portugues|italiano|coreano|chino|japones|aleman))?"
    r"\s+(?:sobre|acerca de|de|que trate sobre)\s+(?P<topic>.{12,1200})\s*$",
    re.I | re.S)
_MUSIC = re.compile(
    r"^\s*(?:(?:oye|hola)\s+)?(?:sky[,: -]+)?"
    r"(?:compone|crea|genera)\s+(?:una?\s+)?"
    r"(?:musica|pista)\s+instrumental\s+(?:sobre|inspirada en|de)\s+"
    r"(?P<topic>.{5,140})\s*$",re.I|re.S)


def normalize(text):
    d=unicodedata.normalize("NFKD",text)
    return "".join(c for c in d if not unicodedata.combining(c)).lower()


def parse(text):
    if not isinstance(text,str) or not 15<=len(text)<=1800:
        return None
    converted=normalize(text)
    match=_PATTERN.fullmatch(converted)
    if match:
        topic=text[match.start("topic"):match.end("topic")].strip()
        return {"action":"writing","kind":KIND[match.group(1)],
                "locale":LANG.get(match.group(2),"es"),"topic":topic}
    music=_MUSIC.fullmatch(converted)
    if music:
        topic=text[music.start("topic"):music.end("topic")].strip()
        return {"action":"instrumental","topic":topic}
    return None


def handle(text,provider="auto"):
    intent=parse(text)
    if intent is None:
        return None
    try:
        from . import sky_creative_evolution as studio
        if intent["action"]=="writing":
            title=intent["topic"][:90]
            work=studio.create_writing(intent["kind"],title,intent["topic"],
                                       locale=intent["locale"],provider=provider)
            return {"tipo":"respuesta","proveedor":"sky-creative-evolution",
                    "mensaje":work["text"],"creative_work_id":work["id"],
                    "creative_version":work["version"],
                    "creative_locale":work["locale"],
                    "created":True,"generated_media":False}
        music=studio.save_music(seed_text=intent["topic"])
        return {"tipo":"respuesta","proveedor":"sky-creative-evolution",
                "mensaje":"Compuse una pista instrumental WAV original y la guardé "
                          "en la biblioteca privada del Estudio Creativo de SKY. "
                          "Podés escucharla y descargarla allí.",
                "creative_asset_id":music["asset"]["id"],"created":True,
                "generated_media":True,"sung_vocals":False}
    except Exception:
        # No afirmar creación si el proveedor falla; no exponer secretos.
        return {"tipo":"error","proveedor":"sky-creative-evolution",
                "mensaje":"No pude terminar la creación con los motores disponibles. "
                          "Revisá el modelo, la biblioteca y su diagnóstico; "
                          "no se confirmó un nuevo archivo."}
