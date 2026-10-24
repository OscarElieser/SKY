"""Explicit, read-only research voice and chat commands for SKY.

Invoked AFTER emergency stop/SENTINEL. External queries happen only when the
person explicitly names the provider; never from inferred intent. No n8n
side effects can be triggered by a spoken phrase.
"""
from __future__ import annotations
import re


def interpretar(texto: str)->dict|None:
    if not isinstance(texto,str) or not 7<=len(texto)<=1200:return None
    t=re.sub(r"^(?:oye\s+|hey\s+)?sky[\s,:]+","",texto.strip(),flags=re.I)
    match=re.fullmatch(r"(?:investiga|busca|buscar)\s+(?:art[ií]culos\s+)?(?:en\s+)?semantic\s+scholar\s+(?:sobre\s+)?(.{3,220})",t,flags=re.I)
    provider="semantic_scholar" if match else None
    if not match:
        match=re.fullmatch(r"(?:busca|buscar|consulta)\s+(?:mis\s+)?(?:referencias\s+)?(?:en\s+)?zotero(?:\s+sobre)?\s+(.{3,160})",t,flags=re.I)
        if match:provider="zotero"
    if not match:
        match=re.fullmatch(r"(?:consulta|pregunta|calcula|calcular)\s+(?:a\s+)?wolfram(?:\s+alpha)?\s+(.{3,180})",t,flags=re.I)
        if match:provider="wolfram"
    if not match:return None
    from . import sky_research_connectors as research
    try:
        if provider=="semantic_scholar":
            result=research.semantic_scholar(match.group(1),limit=5)
            rows=result["items"]
            if not rows:body="La búsqueda no devolvió publicaciones."
            else:
                body="\n".join(f"{i}. {x['title']} ({x['year'] or 'sin año'}). "+
                         (f"DOI: {x['doi']}. " if x["doi"] else "")+
                         (f"Fuente: {x['url']}" if x["url"] else "")
                         for i,x in enumerate(rows,1))
            body+="\nSolo metadatos; no afirmo haber revisado el texto completo."
        elif provider=="zotero":
            result=research.zotero_items(match.group(1),limit=8)
            body="\n".join(f"{i}. {x['title']} ({x['date'] or 'sin fecha'}). DOI: {x['DOI'] or 'no registrado'}"
                           for i,x in enumerate(result["items"],1)) or "No encontré referencias."
            body+="\nEstas referencias proceden de tu biblioteca autorizada; no se compartieron ni publicaron."
        else:
            result=research.wolfram_short_answer(match.group(1))
            body="Wolfram Alpha respondió: "+result["answer"]+"\nComprobá supuestos y unidades según el ejercicio."
        return {"tipo":"respuesta","mensaje":body[:5000],"proveedor":"sky-research-"+provider,
                "external_live_lookup":True}
    except (research.ResearchInputError,research.ResearchConnectorError) as exc:
        return {"tipo":"error","proveedor":"sky-research-"+str(provider),
                "mensaje":str(exc)[:220]}
