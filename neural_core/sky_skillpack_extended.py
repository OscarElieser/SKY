"""Seven missing SKY Skillpack adapters. Explicitly bounded, no hidden automation.

External calls require owner-provisioned credentials. No call is live-verified by
mere presence of environment variables. Risks and side effects are explicit.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
_POLL = {}
_LOCK = threading.RLock()
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sky-bounded-skill")
_NAMES = {"aws-workflow-deploy","loki-mode","supermemory","google-workspace-connector",
          "slack-communicator","remotion","claude-d3js-skill"}

class Unavailable(RuntimeError): pass
class Invalid(ValueError): pass

def _string(body, key, limit=300, required=True):
    x=body.get(key,"")
    if not isinstance(x,str) or len(x)>limit or (required and not x.strip()):
        raise Invalid("Parámetro inválido: "+key)
    return x.strip()

def _bool_yes(body):
    if body.get("approved") is not True:
        raise Invalid("Se requiere approved=true por acción explícita del propietario.")

def configured(name):
    if name=="supermemory": return True
    if name=="loki-mode": return True
    if name=="aws-workflow-deploy": return bool(shutil.which("aws"))
    if name=="google-workspace-connector": return bool(os.getenv("SKY_GOOGLE_OAUTH_ACCESS_TOKEN"))
    if name=="slack-communicator": return bool(os.getenv("SKY_SLACK_BOT_TOKEN"))
    if name=="remotion":
        return bool(shutil.which("node") and (_ROOT/"sky_remotion"/"node_modules"/".bin"/("remotion.cmd" if os.name=="nt" else "remotion")).exists())
    if name=="claude-d3js-skill":
        return bool(shutil.which("node") and (_ROOT/"sky_d3"/"node_modules"/"d3").is_dir())
    return False

def _http(method, url, token, *, payload=None):
    allowed=("https://www.googleapis.com/drive/v3/files",
             "https://gmail.googleapis.com/gmail/v1/users/me/messages",
             "https://www.googleapis.com/calendar/v3/calendars/primary/events",
             "https://slack.com/api/conversations.history",
             "https://slack.com/api/chat.postMessage",
             "https://slack.com/api/auth.test")
    from urllib.parse import urlsplit
    p=urlsplit(url)
    if p.scheme!="https" or p.username or p.password or p.fragment or not any(url.startswith(u) and p.hostname==urlsplit(u).hostname and p.path==urlsplit(u).path for u in allowed):
        raise Invalid("Endpoint fuera del registro fijo.")
    try:
        with httpx.Client(timeout=12,follow_redirects=False) as cli:
            res=cli.request(method,url,headers={"Authorization":"Bearer "+token,
                        "Accept":"application/json"},json=payload)
            res.raise_for_status()
            data=res.json()
            if not isinstance(data,dict):
                raise Unavailable("El proveedor devolvió un formato desconocido.")
            if data.get("ok") is False or data.get("error") or data.get("errors"):
                raise Unavailable("El proveedor rechazó la operación.")
            payload=json.dumps(data,ensure_ascii=False)
            return {"ok":True,"provider_http_status":res.status_code,
                    "data":data if len(payload)<=12000 else {"excerpt":payload[:12000],"truncated":True}}
    except (httpx.HTTPError,ValueError) as exc:
        raise Unavailable("La API externa no respondió correctamente.") from exc

def _aws(body):
    if not configured("aws-workflow-deploy"): raise Unavailable("Instalá AWS CLI y configurá credenciales con permisos mínimos.")
    cmd=_string(body,"operation",30)
    if cmd=="identity":
        args=["aws","sts","get-caller-identity","--output","json"]
    elif cmd=="validate-template":
        ident=_string(body,"template",90)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(?:json|ya?ml)",ident): raise Invalid("Plantilla inválida.")
        # Relative to the fixed repository directory, not arbitrary filesystem paths.
        folder=(_ROOT/"cloud_templates").resolve()
        target=(folder/ident).resolve()
        if not target.is_relative_to(folder) or not target.is_file(): raise Invalid("Plantilla local no encontrada.")
        args=["aws","cloudformation","validate-template","--template-body","file://"+str(target),"--output","json"]
    else:
        raise Invalid("Solo se admiten identidad y validación segura de CloudFormation.")
    try:
        out=subprocess.run(args,cwd=str(_ROOT),capture_output=True,text=True,timeout=20,check=True)
        return {"ok":True,"data":json.loads(out.stdout[:20000]),"live_verified":True}
    except (OSError,subprocess.SubprocessError,ValueError) as exc:
        raise Unavailable("AWS CLI no completó la operación.") from exc

def _memory(body):
    from .smart_memory import get_smart_memory_manager
    db=get_smart_memory_manager()
    action=_string(body,"operation",12)
    category=_string(body,"category",20,required=False) or "proyecto"
    if category not in {"proyecto","preferencia","documental"}: raise Invalid("Categoría desconocida.")
    if action=="list":
        items=db.consultar_memorias(categoria=category)[:30]
        return {"ok":True,"items":[{"id":x.id,"category":x.categoria,"key":x.clave,"value":x.valor} for x in items]}
    key=_string(body,"key",80)
    if not re.fullmatch(r"[\w.-]{1,80}",key):raise Invalid("Clave inválida.")
    ident="default_user:"+category+":"+key
    if action=="get":
        items=db.consultar_memorias(categoria=category)
        return {"ok":True,"found":any(x.id==ident for x in items),
                "item":next((x.valor for x in items if x.id==ident),None)}
    if action=="set":
        _bool_yes(body)
        value=_string(body,"value",2000)
        if re.search(r"(?i)\b(password|api[_-]?key|private[_-]?key|token)\s*[:=]",value):
            raise Invalid("No se deben guardar secretos como memorias.")
        x=db.guardar_memoria(category,key,value,es_privado=True)
        return {"ok":True,"saved":x.id}
    if action=="delete":
        _bool_yes(body)
        return {"ok":True,"deleted":db.eliminar_memoria(ident)}
    raise Invalid("Operación no soportada.")

def _google(body):
    token=os.getenv("SKY_GOOGLE_OAUTH_ACCESS_TOKEN","").strip()
    if not token: raise Unavailable("Falta OAuth de Google: SKY_GOOGLE_OAUTH_ACCESS_TOKEN.")
    service=_string(body,"service",18)
    urls={"drive":"https://www.googleapis.com/drive/v3/files?pageSize=10&fields=files(id,name,mimeType),nextPageToken",
          "gmail":"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=10",
          "calendar":"https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=10&singleEvents=true"}
    if service not in urls:raise Invalid("Solo lectura Drive, Gmail y Calendar.")
    return _http("GET",urls[service],token)

def _slack(body):
    token=os.getenv("SKY_SLACK_BOT_TOKEN","").strip()
    if not token:raise Unavailable("Falta SKY_SLACK_BOT_TOKEN.")
    action=_string(body,"operation",20)
    if action=="whoami":return _http("GET","https://slack.com/api/auth.test",token)
    channel=_string(body,"channel",64)
    allowed={x.strip() for x in os.getenv("SKY_SLACK_ALLOWED_CHANNELS","").split(",") if x.strip()}
    if not re.fullmatch(r"[CGD][A-Z0-9]{8,20}",channel) or channel not in allowed:
        raise Invalid("Canal no permitido: SKY_SLACK_ALLOWED_CHANNELS.")
    if action=="history":
        return _http("GET","https://slack.com/api/conversations.history?channel="+channel+"&limit=10",token)
    if action=="send":
        _bool_yes(body)
        text=_string(body,"text",1700)
        return _http("POST","https://slack.com/api/chat.postMessage",token,
                     payload={"channel":channel,"text":text,"unfurl_links":False})
    raise Invalid("Acción Slack no autorizada.")

def _remotion(body):
    if not configured("remotion"):raise Unavailable("Remotion CLI no está instalado localmente en sky_remotion.")
    composition=_string(body,"composition",70)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,69}",composition):raise Invalid("Composición inválida.")
    _bool_yes(body)
    project=(_ROOT/"sky_remotion").resolve()
    output=(project/"out"/(composition+".mp4")).resolve()
    if not output.is_relative_to(project):raise Invalid("Ruta no permitida.")
    output.parent.mkdir(parents=True,exist_ok=True)
    cli=project/"node_modules"/".bin"/("remotion.cmd" if os.name=="nt" else "remotion")
    try:
        out=subprocess.run([str(cli),"render",composition,str(output),"--overwrite=false"],
                           cwd=str(project),capture_output=True,text=True,timeout=120,check=True)
        if not output.is_file() or output.stat().st_size==0:raise Unavailable("Render sin archivo de salida.")
        return {"ok":True,"output":str(output.relative_to(_ROOT)),"bytes":output.stat().st_size,"live_verified":True}
    except (OSError,subprocess.SubprocessError) as exc:raise Unavailable("Remotion no completó el render.") from exc

def _d3(body):
    if not configured("claude-d3js-skill"):raise Unavailable("Instalá d3 en sky_d3 con npm y Node.js.")
    values=body.get("values")
    if not isinstance(values,list) or not 2<=len(values)<=60 or any(type(x) not in (int,float) or not -1e8<=x<=1e8 for x in values):
        raise Invalid("values debe contener de 2 a 60 números finitos.")
    script=_ROOT/"sky_d3"/"render.mjs"
    try:
        p=subprocess.run(["node",str(script)],input=json.dumps(values),text=True,
                         capture_output=True,cwd=str(script.parent),timeout=12,check=True)
        svg=p.stdout.strip()
        if not svg.startswith("<svg") or "</svg>" not in svg:raise Unavailable("D3 no devolvió un SVG.")
        return {"ok":True,"mime":"image/svg+xml","content":svg[:18000],"live_verified":True}
    except (OSError,subprocess.SubprocessError) as exc:raise Unavailable("D3 no pudo renderizar los datos.") from exc

def _loki(body):
    """Bounded parallel tasks: only dry-run SEO and deterministic SVG."""
    operation=_string(body,"operation",20)
    with _LOCK:
        for k in list(_POLL):
            if time.monotonic()-_POLL[k]["created"]>1800:_POLL.pop(k,None)
        if operation=="poll":
            ident=_string(body,"job_id",80)
            job=_POLL.get(ident)
            if job is None: raise Invalid("Trabajo inexistente o expirado.")
            task=job["future"]
            return {"ok":True,"job_id":ident,"state":"COMPLETED" if task.done() and not task.exception() else
                    ("FAILED" if task.done() else "RUNNING"),
                    "result":task.result() if task.done() and not task.exception() else None}
        if operation!="submit":raise Invalid("Operación Loki desconocida.")
        _bool_yes(body)
        kind=_string(body,"skill",30)
        if kind not in ("seo-audit","algorithmic-art"):raise Invalid("Skill fuera del conjunto acotado.")
        if len(_POLL)>=24:raise Unavailable("Máximo de trabajos en segundo plano.")
        parameters=body.get("parameters",{})
        if not isinstance(parameters,dict):raise Invalid("Parámetros inválidos.")
        from .sky_skillpack import execute
        ident=secrets.token_urlsafe(16)
        future=_POOL.submit(execute,kind,parameters)
        _POLL[ident]={"future":future,"created":time.monotonic()}
        return {"ok":True,"job_id":ident,"state":"RUNNING"}

def execute(name, body):
    if name not in _NAMES:raise Invalid("Integración desconocida.")
    if not isinstance(body,dict):raise Invalid("Se esperaba un objeto JSON.")
    operations={"aws-workflow-deploy":_aws,"loki-mode":_loki,"supermemory":_memory,
       "google-workspace-connector":_google,"slack-communicator":_slack,
       "remotion":_remotion,"claude-d3js-skill":_d3}
    return operations[name](body)
