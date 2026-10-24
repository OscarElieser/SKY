"""SKY Research Connectors: fixed-origin read-only academic lookups.

Semantic Scholar, Zotero and Wolfram Alpha complement, never replace,
existing SKY Scholar (OpenAlex/Crossref) and SKY Aula.
Retrieved contents are DATA, never commands, prompts, or verified conclusions.
No background network calls and no external credentials in result objects.
"""
from __future__ import annotations

import os
import re
from urllib.parse import urlencode

import httpx

_HOSTS={
    "semantic_scholar":"api.semanticscholar.org",
    "zotero":"api.zotero.org",
    "wolfram":"api.wolframalpha.com",
}
_TIMEOUT=12.0
_MAX_BYTES=220_000

class ResearchConnectorError(RuntimeError): pass
class ResearchInputError(ValueError): pass


def _query(value: str, maxlen:int=220)->str:
    if not isinstance(value,str) or not 3<=len(value.strip())<=maxlen or "\x00" in value:
        raise ResearchInputError("Consulta inválida o demasiado larga.")
    return value.strip()


def _get(host:str, path:str, params:dict, *, headers:dict|None=None, plain:bool=False):
    if host not in _HOSTS.values() or not path.startswith("/") or "//" in path or ".." in path:
        raise ResearchInputError("Destino fuera del catálogo de proveedores.")
    url="https://"+host+path
    base={"Accept":"text/plain" if plain else "application/json",
          "User-Agent":"SKY-IA-Research/1.0"}
    base.update(headers or {})
    try:
        with httpx.Client(timeout=_TIMEOUT,follow_redirects=False,trust_env=False) as client:
            response=client.get(url,params=params,headers=base)
            if response.status_code!=200:
                raise ResearchConnectorError("Proveedor devolvió HTTP "+str(response.status_code))
            if len(response.content)>_MAX_BYTES:
                raise ResearchConnectorError("Respuesta académica excede tamaño permitido.")
            if plain:
                content=response.text.strip()
                if not content or len(content)>4000:
                    raise ResearchConnectorError("Respuesta computacional vacía o demasiado extensa.")
                return content
            output=response.json()
            if not isinstance(output,(dict,list)):
                raise ResearchConnectorError("Formato de respuesta desconocido.")
            return output
    except (httpx.RequestError,ValueError) as exc:
        raise ResearchConnectorError("No pudo establecerse una conexión académica segura.") from exc


def semantic_scholar(query:str,limit:int=5)->dict:
    query=_query(query)
    if type(limit) is not int or not 1<=limit<=10:
        raise ResearchInputError("Límite 1 a 10.")
    token=os.getenv("SEMANTIC_SCHOLAR_API_KEY","").strip()
    headers={"x-api-key":token} if token else {}
    fields="title,year,authors,url,venue,externalIds,citationCount,abstract"
    data=_get(_HOSTS["semantic_scholar"],"/graph/v1/paper/search",
              {"query":query,"limit":limit,"fields":fields},headers=headers)
    if not isinstance(data,dict) or not isinstance(data.get("data"),list):
        raise ResearchConnectorError("No hay una lista válida de publicaciones.")
    items=[]
    for item in data["data"][:limit]:
        if not isinstance(item,dict):continue
        ext=item.get("externalIds") or {}
        doi=ext.get("DOI","") if isinstance(ext,dict) else ""
        people=item.get("authors") or []
        items.append({"title":str(item.get("title") or "")[:350],
                      "year":item.get("year"),"doi":str(doi)[:160],
                      "authors":[str(x.get("name") or "")[:120] for x in people[:12] if isinstance(x,dict)],
                      "venue":str(item.get("venue") or "")[:200],
                      "url":str(item.get("url") or "")[:650] if str(item.get("url") or "").startswith("https://") else "",
                      "abstract_excerpt":str(item.get("abstract") or "")[:1300],
                      "citations_reported":item.get("citationCount"),
                      "provider":"semantic_scholar","evidence_level":"metadata_and_optional_abstract_only",
                      "peer_review_verified":False,"full_text_read":False})
    return {"ok":True,"provider":"semantic_scholar","query":query,
            "items":items,"results_observed":len(items),"live_lookup":True,
            "source":"https://api.semanticscholar.org/graph/v1/paper/search",
            "warning":"Resumen y metadatos no verifican las conclusiones del artículo."}


def zotero_items(query:str="",limit:int=10)->dict:
    if not isinstance(query,str) or len(query)>160:raise ResearchInputError("Consulta Zotero inválida.")
    if type(limit) is not int or not 1<=limit<=30:raise ResearchInputError("Límite 1 a 30.")
    user_id=os.getenv("SKY_ZOTERO_USER_ID","").strip()
    key=os.getenv("SKY_ZOTERO_API_KEY","").strip()
    if not re.fullmatch(r"[1-9][0-9]{0,14}",user_id):
        raise ResearchConnectorError("Configurá SKY_ZOTERO_USER_ID.")
    if not key:
        raise ResearchConnectorError("Configurá SKY_ZOTERO_API_KEY de solo lectura para tu biblioteca.")
    data=_get(_HOSTS["zotero"],"/users/"+user_id+"/items",
              {"limit":limit,"q":query.strip(),"format":"json"},
              headers={"Zotero-API-Key":key,"Zotero-API-Version":"3"})
    if not isinstance(data,list):raise ResearchConnectorError("Zotero no devolvió lista de referencias.")
    items=[]
    for row in data[:limit]:
        if not isinstance(row,dict):continue
        d=row.get("data") or {}
        if not isinstance(d,dict):continue
        creators=d.get("creators") or []
        items.append({"key":str(row.get("key") or "")[:40],
                      "title":str(d.get("title") or "")[:350],
                      "date":str(d.get("date") or "")[:80],
                      "itemType":str(d.get("itemType") or "")[:60],
                      "DOI":str(d.get("DOI") or "")[:180],
                      "creators":[str(a.get("lastName") or a.get("name") or "")[:120]
                                  for a in creators[:12] if isinstance(a,dict)],
                      "url":str(d.get("url") or "")[:600]})
    return {"ok":True,"provider":"zotero","items":items,"results_observed":len(items),
            "metadata_only":True,"private_library":True,"not_published":True}


def wolfram_short_answer(question:str,units:str="metric")->dict:
    question=_query(question,maxlen=180)
    if units not in {"metric","imperial"}:
        raise ResearchInputError("Unidades desconocidas.")
    app_id=os.getenv("SKY_WOLFRAM_APP_ID","").strip()
    if not app_id:raise ResearchConnectorError("Configurá SKY_WOLFRAM_APP_ID.")
    # Wolfram's Short Answers endpoint requires appid as a query parameter.
    # Never print, persist or return the URL including this credential.
    text=_get(_HOSTS["wolfram"],"/v1/result",{"appid":app_id,"i":question,
              "units":units},plain=True)
    return {"ok":True,"provider":"wolfram_short_answers","question":question,
            "answer":text,"units":units,"live_lookup":True,
            "source":"https://products.wolframalpha.com/short-answers-api/documentation",
            "warning":"El resultado computacional debe revisarse según la materia y el contexto."}


def readiness()->dict:
    return {"semantic_scholar":{"endpoint_defined":True,"api_key_present":bool(os.getenv("SEMANTIC_SCHOLAR_API_KEY")),
                                  "key_optional":True,"live_verified":False},
            "zotero":{"endpoint_defined":True,"configured":bool(os.getenv("SKY_ZOTERO_API_KEY") and os.getenv("SKY_ZOTERO_USER_ID")),"live_verified":False},
            "wolfram":{"endpoint_defined":True,"configured":bool(os.getenv("SKY_WOLFRAM_APP_ID")),"live_verified":False},
            "existing_openalex_crossref_preserved":True}
