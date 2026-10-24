"""SKY -> owner-controlled n8n bridge; no agent, API or UI replacement.

Reads fixed n8n API paths and redacts workflow definitions/credentials.
A configured, explicitly approved webhook dispatch does NOT prove completion.
No arbitrary domains, paths, redirects, or text->workflow execution.
"""
from __future__ import annotations

import ipaddress
import os
import re
from urllib.parse import urlsplit

import httpx


class N8NInvalid(ValueError):pass
class N8NUnavailable(RuntimeError):pass


def _base()->str:
    raw=os.getenv("SKY_N8N_URL","").strip().rstrip("/")
    if not raw:raise N8NUnavailable("Configurá SKY_N8N_URL para una instancia n8n controlada.")
    parts=urlsplit(raw)
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("","/"):
        raise N8NInvalid("La dirección n8n no debe contener rutas, secretos o consultas.")
    host=(parts.hostname or "").lower()
    allow={h.strip().lower() for h in os.getenv("SKY_N8N_ALLOWED_HOSTS","").split(",") if h.strip()}
    is_local=(parts.scheme=="http" and host=="127.0.0.1" and parts.port==5678
              and os.getenv("SKY_N8N_ALLOW_LOCAL")=="1")
    if not is_local:
        if parts.scheme!="https" or host not in allow or not host or parts.port not in (None,443):
            raise N8NInvalid("Solo HTTPS y hosts expresamente permitidos; localhost requiere autorización separada.")
        if host=="localhost" or host.endswith((".local",".internal")):
            raise N8NInvalid("No se aceptan hosts privados en la configuración remota.")
        try:
            ipaddress.ip_address(host)
        except ValueError:pass
        else:raise N8NInvalid("No se aceptan IP remotas.")
    return raw


def _network(method:str,endpoint:str,headers:dict,body:dict|None=None)->dict:
    if not endpoint.startswith(("/api/v1/workflows?limit=","/api/v1/executions?limit=","/webhook/")):
        raise N8NInvalid("Ruta n8n no permitida.")
    try:
        with httpx.Client(timeout=10.0,follow_redirects=False,trust_env=False) as client:
            res=client.request(method,_base()+endpoint,headers=headers,json=body)
            if res.status_code not in (200,201,202,204):
                raise N8NUnavailable("n8n rechazó la operación: HTTP "+str(res.status_code))
            if len(res.content)>250000:raise N8NUnavailable("Respuesta n8n demasiado grande.")
            if not res.content:return {}
            data=res.json()
            if not isinstance(data,dict):
                raise N8NUnavailable("Formato n8n no reconocido.")
            return data
    except (httpx.RequestError,ValueError) as exc:
        raise N8NUnavailable("No se pudo conectar con n8n de forma segura.") from exc


def list_workflows(limit:int=10)->dict:
    if type(limit) is not int or not 1<=limit<=20:raise N8NInvalid("Límite inválido.")
    key=os.getenv("SKY_N8N_API_KEY","").strip()
    if not key:raise N8NUnavailable("Falta SKY_N8N_API_KEY.")
    data=_network("GET",f"/api/v1/workflows?limit={limit}",{"X-N8N-API-KEY":key})
    items=data.get("data")
    if not isinstance(items,list):raise N8NUnavailable("n8n no devolvió workflows.")
    return {"ok":True,"action":"list_workflows","items":[{
        "id":str(x.get("id") or "")[:100],
        "name":str(x.get("name") or "")[:140],
        "active":bool(x.get("active",False)),
        "updatedAt":str(x.get("updatedAt") or "")[:60]}
        for x in items[:limit] if isinstance(x,dict)],"live_read":True,
        "workflow_content_exposed":False}


def recent_executions(limit:int=10)->dict:
    if type(limit) is not int or not 1<=limit<=20:raise N8NInvalid("Límite inválido.")
    key=os.getenv("SKY_N8N_API_KEY","").strip()
    if not key:raise N8NUnavailable("Falta SKY_N8N_API_KEY.")
    data=_network("GET",f"/api/v1/executions?limit={limit}",{"X-N8N-API-KEY":key})
    rows=data.get("data")
    if not isinstance(rows,list):raise N8NUnavailable("n8n no devolvió ejecuciones.")
    return {"ok":True,"action":"recent_executions","items":[{
        "id":str(x.get("id") or "")[:100],
        "workflowId":str(x.get("workflowId") or "")[:100],
        "status":str(x.get("status") or "")[:60],
        "finished":x.get("finished") is True,
        "startedAt":str(x.get("startedAt") or "")[:60],
        "stoppedAt":str(x.get("stoppedAt") or "")[:60]}
        for x in rows[:limit] if isinstance(x,dict)],"live_read":True,
        "execution_data_exposed":False}


def dispatch_webhook(alias:str, *, approved:bool=False)->dict:
    """Single fixed alias, explicit owner authorization required by SKY API.

    Calling a production webhook may incur costs/send data in n8n; returns
    DISPATCHED_UNVERIFIED even on HTTP 200. No user-provided webhook URL/data.
    """
    if approved is not True:raise N8NInvalid("Confirmación explícita requerida.")
    if os.getenv("SKY_N8N_ALLOW_DISPATCH")!="1":
        raise N8NInvalid("SKY_N8N_ALLOW_DISPATCH debe habilitarse por el propietario.")
    if not isinstance(alias,str) or not re.fullmatch(r"[a-z][a-z0-9_-]{1,50}",alias):
        raise N8NInvalid("Alias de automatización inválido.")
    allowed={x.strip() for x in os.getenv("SKY_N8N_ALLOWED_WEBHOOKS","").split(",") if x.strip()}
    if alias not in allowed:raise N8NInvalid("Este flujo no está autorizado.")
    secret=os.getenv("SKY_N8N_WEBHOOK_SECRET","").strip()
    if len(secret)<24:raise N8NUnavailable("Configurá un secreto de webhook con longitud suficiente.")
    _network("POST","/webhook/"+alias,
             {"X-SKY-WEBHOOK-SECRET":secret,"Content-Type":"application/json"},
             {"source":"SKY","alias":alias})
    return {"ok":True,"workflow":alias,"status":"DISPATCHED_UNVERIFIED",
            "verified":False,"note":"La recepción de un webhook no demuestra que el flujo terminó."}


def readiness()->dict:
    return {"configured":bool(os.getenv("SKY_N8N_URL") and os.getenv("SKY_N8N_API_KEY")),
            "dispatch_enabled":os.getenv("SKY_N8N_ALLOW_DISPATCH")=="1",
            "live_verified":False,"independent_server_required":True}
