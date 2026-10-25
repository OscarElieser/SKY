"""Make.com safe scenario trigger. Explicitly approved preset; no dynamic URLs."""
from __future__ import annotations
import json
import os
import re
from urllib.parse import urlsplit
import httpx

class MakeInvalid(ValueError): pass
class MakeUnavailable(RuntimeError): pass

_ALIAS = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
_HOST = re.compile(r"^hook(?:\.[a-z0-9-]{1,16})?\.make\.com$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{8,160}$")

def _local_only():
    return os.getenv("SKY_LOCAL_ONLY","").lower() in ("1","true","yes","si")

def _webhook(alias):
    if not isinstance(alias,str) or not _ALIAS.fullmatch(alias):
        raise MakeInvalid("Alias Make no permitido.")
    raw = os.getenv("SKY_MAKE_WEBHOOK_"+alias.upper(),"").strip()
    if not raw: raise MakeUnavailable("No existe un webhook Make configurado para el alias.")
    p = urlsplit(raw)
    if p.scheme!="https" or p.username or p.password or p.port not in (None,443) or not _HOST.fullmatch(p.hostname or ""):
        raise MakeInvalid("Solo se permiten webhooks oficiales HTTPS de hook.make.com.")
    if not _TOKEN.fullmatch(p.path.strip("/")) or p.query or p.fragment:
        raise MakeInvalid("La ruta Make debe ser un identificador de webhook, sin otros parámetros.")
    return raw

def capabilities():
    names=os.getenv("SKY_MAKE_ALIASES","").split(",")
    good=[x.strip() for x in names if _ALIAS.fullmatch(x.strip())]
    return {"provider":"Make","configured_aliases":[x for x in good
            if os.getenv("SKY_MAKE_WEBHOOK_"+x.upper(),"").strip()],
            "remote":True,"owner_approval_required":True,
            "webhook_ack_is_not_scenario_completed":True}

def trigger(alias, payload, *, approved=False):
    if not approved:
        raise PermissionError("SKY necesita aprobación expresa antes de llamar a Make.")
    if _local_only():
        raise MakeInvalid("SKY_LOCAL_ONLY impide conectar con Make.com.")
    if alias not in capabilities()["configured_aliases"]:
        raise MakeInvalid("El flujo no figura en los alias expresamente habilitados.")
    url=_webhook(alias)
    if not isinstance(payload,dict) or len(payload)>8:
        raise MakeInvalid("Usá un JSON simple de hasta 8 campos.")
    safe={}
    for key,value in payload.items():
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,32}",key):
            raise MakeInvalid("Clave JSON no permitida.")
        if not isinstance(value,(str,int,float,bool)) or isinstance(value,str) and len(value)>800:
            raise MakeInvalid("Solo se admiten datos simples y limitados, no archivos ni secretos.")
        safe[key]=value
    key=os.getenv("SKY_MAKE_API_KEY_"+alias.upper(),"").strip()
    headers={"Content-Type":"application/json"}
    if key:headers["x-make-apikey"]=key
    try:
        with httpx.Client(timeout=8,follow_redirects=False,trust_env=False) as client:
            response=client.post(url,json={"origin":"SKY","intent":alias,"data":safe},headers=headers)
        if response.status_code not in (200,201,202,204):
            raise MakeUnavailable("Make rechazó el webhook. Código HTTP "+str(response.status_code))
        return {"provider":"Make","alias":alias,"http":response.status_code,
                "delivered_to_webhook":True,"scenario_completed":False}
    except httpx.HTTPError as exc:
        raise MakeUnavailable("Make no pudo confirmar recepción: comprobá el escenario y evita repetir a ciegas.") from exc
