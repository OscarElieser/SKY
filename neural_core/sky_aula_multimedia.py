"""SKY Aula multimodal: research-backed resources and bounded teaching scenes.

Enhances existing sky_aula; does not launch videos or claim to have watched them.
No web search without explicit teacher request, no scraping YouTube, no private
student details, no arbitrary URLs or external scripts from search results.
"""
from __future__ import annotations

import os
import re
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
import json

class MediaInputError(ValueError): pass
class MediaUnavailable(RuntimeError): pass

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MediaUnavailable("No se permiten redirecciones a otros destinos.")

def _clean(value,maximum=160):
    if not isinstance(value,str) or not 3<=len(value.strip())<=maximum:
        raise MediaInputError("El tema debe tener entre 3 y "+str(maximum)+" caracteres.")
    if any(ord(c)<32 for c in value):
        raise MediaInputError("No se admiten caracteres de control.")
    return " ".join(value.split())

def _youtube_fetch(url):
    if not url.startswith("https://www.googleapis.com/youtube/v3/search?"):
        raise MediaInputError("API de video no autorizada.")
    req=Request(url,headers={"Accept":"application/json",
         "User-Agent":"SKY-Aula-Educacion/1.0"})
    try:
        with build_opener(_NoRedirect,HTTPSHandler()).open(req,timeout=12) as response:
            data=response.read(180001)
            if len(data)>180000:
                raise MediaUnavailable("Respuesta de videos demasiado grande.")
            return json.loads(data)
    except (OSError,ValueError) as exc:
        raise MediaUnavailable("No se pudo consultar YouTube Data API.") from exc

def youtube(topic:str,level:str="tecnico",limit:int=4)->dict:
    topic=_clean(topic)
    if not isinstance(level,str) or len(level)>30 or type(limit) is not int or not 1<=limit<=6:
        raise MediaInputError("Nivel o límite inválido.")
    search_query=topic+" explicación educativa "+level
    public_search="https://www.youtube.com/results?"+urlencode({"search_query":search_query})
    if os.getenv("SKY_LOCAL_ONLY","").lower() in {"1","true","yes"}:
        return {"status":"offline","videos":[],"fallback_search_url":public_search,
                "searched_live":False,"message":"SKY_LOCAL_ONLY bloquea YouTube."}
    key=os.getenv("SKY_YOUTUBE_API_KEY","").strip()
    if not key:
        return {"status":"needs_configuration","videos":[],"fallback_search_url":public_search,
                "searched_live":False,"message":"Configurá SKY_YOUTUBE_API_KEY para resultados verificados."}
    params={"part":"snippet","q":search_query,"key":key,"maxResults":limit,
            "type":"video","videoEmbeddable":"true","safeSearch":"strict",
            "relevanceLanguage":"es"}
    raw=_youtube_fetch("https://www.googleapis.com/youtube/v3/search?"+urlencode(params))
    if not isinstance(raw,dict) or not isinstance(raw.get("items"),list):
        raise MediaUnavailable("YouTube no devolvió una lista válida.")
    results=[]
    for row in raw["items"][:limit]:
        if not isinstance(row,dict):continue
        ident=(row.get("id") or {}).get("videoId","")
        if not isinstance(ident,str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",ident):
            continue
        snippet=row.get("snippet") or {}
        results.append({"id":ident,"title":str(snippet.get("title") or "")[:180],
            "channel":str(snippet.get("channelTitle") or "")[:100],
            "published_at":str(snippet.get("publishedAt") or "")[:35],
            "watch_url":"https://www.youtube.com/watch?v="+ident,
            "embed_url":"https://www.youtube-nocookie.com/embed/"+ident,
            "source":"youtube_data_api","watched_by_sky":False,
            "transcript_read":False,"content_facts_verified":False})
    return {"status":"live_results","searched_live":True,"videos":results,
            "fallback_search_url":public_search,
            "message":"Resultados buscados en YouTube; SKY aún no ha visto el video ni comprobado su contenido.",
            "student_data_transmitted":False}

def bibliography(topic:str,limit:int=5)->dict:
    topic=_clean(topic,200)
    if type(limit) is not int or not 1<=limit<=8:
        raise MediaInputError("Límite académico inválido.")
    if os.getenv("SKY_LOCAL_ONLY","").lower() in {"1","true","yes"}:
        return {"status":"offline","items":[],"verified_article_contents":False}
    from .sky_scholarly import search_papers
    try:
        result=search_papers(topic,provider="openalex",limit=limit)
    except (ValueError,RuntimeError,OSError) as exc:
        raise MediaUnavailable("No se pudo consultar la bibliografía.") from exc
    return {"status":"live_metadata","items":result.get("items",[]),
            "provider":"openalex","verified_article_contents":False,
            "note":"Se recuperaron metadatos, no el artículo completo. Revisá pertinencia y fiabilidad."}

COMPUTER_PARTS=[
    {"id":"case","label":"Gabinete","function":"Protege y organiza los componentes; dirige el flujo de aire",
     "relation":"Aloja la placa madre, almacenamiento y ventiladores",
     "safety":"Apagar y desconectar antes de abrir","size":[3.6,2.6,1.7],"position":[0,0,0],"color":"#22344a"},
    {"id":"motherboard","label":"Placa madre","function":"Interconecta el procesador, memoria, almacenamiento y periféricos",
     "relation":"Distribuye señales y conexiones entre las piezas","safety":"Evitar descargas electrostáticas",
     "size":[2.1,1.65,.08],"position":[0,0.1,0.15],"color":"#167764"},
    {"id":"cpu","label":"Procesador CPU","function":"Ejecuta instrucciones y cálculos",
     "relation":"Trabaja con la RAM y otros dispositivos a través de la placa madre","safety":"No retirar el disipador de un equipo encendido",
     "size":[.65,.65,.14],"position":[-.35,.3,.4],"color":"#c4d7e9"},
    {"id":"ram","label":"Memoria RAM","function":"Mantiene temporalmente los datos de las tareas activas",
     "relation":"Entrega información de trabajo al procesador","safety":"Manipular los módulos sin energía",
     "size":[.13,.9,.12],"position":[.65,.4,.4],"color":"#22b18e"},
    {"id":"ssd","label":"Almacenamiento SSD","function":"Conserva archivos y programas incluso al apagar",
     "relation":"Suministra datos para cargar programas en RAM","safety":"No retirar unidades durante escrituras",
     "size":[.85,.2,.55],"position":[.5,-.6,.4],"color":"#dfb266"},
    {"id":"psu","label":"Fuente de alimentación","function":"Convierte y suministra energía eléctrica a los componentes",
     "relation":"Alimenta placa, discos y tarjetas","safety":"Nunca abrir internamente una fuente por riesgo eléctrico",
     "size":[.9,.65,.9],"position":[-1.05,-.7,.35],"color":"#56687e"},
    {"id":"gpu","label":"Tarjeta gráfica","function":"Procesa gráficos cuando el equipo dispone de GPU dedicada",
     "relation":"Usa memoria y se conecta a la placa base","safety":"No extraer la tarjeta bajo tensión",
     "size":[1.3,.25,.44],"position":[.05,-.25,.65],"color":"#4e86d7"},
    {"id":"cooling","label":"Refrigeración","function":"Disipa el calor para mantener temperaturas seguras",
     "relation":"Enfría el procesador y ayuda a mover aire","safety":"No acercar dedos a ventiladores en marcha",
     "size":[.78,.78,.25],"position":[-.35,.3,.72],"color":"#81b6d9"},
]

def scene(name:str)->dict:
    if not isinstance(name,str) or not re.fullmatch(r"[a-z0-9_-]{1,40}",name):
        raise MediaInputError("Escena inválida.")
    if name not in {"computer","computadora","pc"}:
        return {"available":False,"scene_id":name,"components":[],
                "note":"No existe un modelo 3D revisado para ese tema. SKY debe utilizar material visual verificado antes de explicar piezas."}
    return {"available":True,"scene_id":"computer","title":"Computadora: despiece 3D didáctico",
        "model_kind":"schematic_3d_geometry_not_photorealistic",
        "component_count":len(COMPUTER_PARTS),"components":[dict(p) for p in COMPUTER_PARTS],
        "viewer_url":"/aula/3d/computadora",
        "lesson_sequence":["Identificar el equipo completo","Separar gabinete y partes",
           "Seleccionar cada pieza y escuchar su función","Relacionar las piezas",
           "Reconstruir la computadora","Resolver un caso práctico"],
        "safety":"Demostración virtual. No abrir fuentes ni manipular equipo energizado.",
        "hardware_specific_model_verified":False}

def teaching_support(topic:str,level:str="tecnico")->dict:
    topic=_clean(topic)
    is_pc=bool(re.search(r"\b(computadora|ordenador|computador|hardware|partes del pc)\b",topic,re.I))
    return {"topic":topic,"level":level,"source_strategy":"material_docente_y_fuentes_verificadas",
        "resource_search_available":True,"youtube_search_requires_api_key":True,
        "3d_scene":scene("computer") if is_pc else {"available":False,
                "note":"No se ha validado un modelo tridimensional para este tema."},
        "teaching_cycle":["diagnóstico","explicación","demostración","práctica",
                          "evaluación formativa","refuerzo","evaluación sumativa","cierre"],
        "teacher_control_required":True}
