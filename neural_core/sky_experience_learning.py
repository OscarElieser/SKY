"""SKY Experience Learning: learn ONLY from verified action cycles.

No LLM self-report, arbitrary shell, browser URL, dictated text, files, secrets,
cloud side-effects, or skill code is ever saved or replayed. Replaying only
CREATES an owner-confirmed SKY cycle; the agent still controls every step.
"""
from __future__ import annotations

import copy
import json
import re
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

_LOCK=threading.RLock()
_STORE=Path.home()/".neuralt"/"sky_verified_procedures.json"
_LIMIT=40
_MAX_BYTES=120_000

class LearningInvalid(ValueError):pass
class LearningUnavailable(RuntimeError):pass


def _slug(label:str)->str:
    if not isinstance(label,str) or not 3<=len(label.strip())<=60:
        raise LearningInvalid("Nombre de procedimiento inválido (3–60 caracteres).")
    norm=unicodedata.normalize("NFKD",label.strip())
    norm="".join(c for c in norm if not unicodedata.combining(c))
    norm=re.sub(r"[^a-z0-9]+","-",norm.lower()).strip("-")[:45]
    if len(norm)<3:raise LearningInvalid("Utilizá un nombre descriptivo con letras.")
    return norm


def _valid_replay(steps:list)->list:
    from .windows_controller import AUTHORIZED_APPS
    if not isinstance(steps,list) or not 1<=len(steps)<=6:
        raise LearningInvalid("El procedimiento debe tener entre uno y seis pasos.")
    clean=[]
    for x in steps:
        if not isinstance(x,dict) or set(x)!={"action","params","label"}:
            raise LearningInvalid("El paso no tiene un formato aprobado.")
        action=x.get("action")
        params=x.get("params")
        if action=="status" and params=={}:
            label="Comprobar estado del agente"
        elif action=="launch_app" and isinstance(params,dict) and set(params)=={"app"}:
            app=params["app"]
            if not isinstance(app,str) or app not in AUTHORIZED_APPS:
                raise LearningInvalid("Aplicación no autorizada.")
            label="Abrir "+AUTHORIZED_APPS[app]["desc"][:65]
        else:
            raise LearningInvalid("Solo se memorizan estado y aplicaciones autorizadas.")
        clean.append({"action":action,"params":copy.deepcopy(params),"label":label})
    return clean


def _read()->dict:
    try:
        if not _STORE.exists():return {}
        if _STORE.stat().st_size>_MAX_BYTES:raise LearningUnavailable("Registro de procedimientos excesivo.")
        value=json.loads(_STORE.read_text(encoding="utf-8"))
        if not isinstance(value,dict) or not isinstance(value.get("procedures",{}),dict):
            raise LearningUnavailable("Registro local no reconocido.")
        return value.get("procedures",{})
    except (OSError,ValueError) as exc:
        raise LearningUnavailable("No puedo leer los procedimientos locales.") from exc


def _save(data:dict):
    _STORE.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    raw=json.dumps({"schema":1,"procedures":data},ensure_ascii=False,indent=2)
    if len(raw.encode("utf-8"))>_MAX_BYTES:
        raise LearningUnavailable("No hay espacio en el registro de procedimientos.")
    import secrets
    tmp=_STORE.with_name(_STORE.name+"."+secrets.token_hex(6)+".tmp")
    try:
        with tmp.open("x",encoding="utf-8") as fh:
            fh.write(raw)
        try:tmp.chmod(0o600)
        except OSError:pass
        tmp.replace(_STORE)
        try:_STORE.chmod(0o600)
        except OSError:pass
    finally:
        try:tmp.unlink(missing_ok=True)
        except OSError:pass


def list_procedures()->dict:
    with _LOCK:
        data=_read()
        entries=[]
        for slug,item in sorted(data.items()):
            if not isinstance(item,dict):continue
            try:
                steps=_valid_replay(item.get("steps"))
            except LearningInvalid:
                continue
            entries.append({"id":slug,"name":str(item.get("name",""))[:60],
                            "steps":len(steps),"evidence_count":int(item.get("evidence_count",1)),
                            "verified_source":item.get("source")=="verified_sky_cycle",
                            "last_verified_at":item.get("last_verified_at",""),
                            "requires_approval_each_step":True})
        return {"procedures":entries,"total":len(entries),
                "auto_execute":False,"approval_required":True,
                "note":"Son procedimientos locales explícitamente autorizados, no reentrenamiento del modelo."}


def capture_verified(cycle_id:str,label:str,*,approved:bool)->dict:
    if approved is not True:
        raise LearningInvalid("No se guarda ninguna experiencia sin consentimiento explícito.")
    slug=_slug(label)
    from . import sky_execution_cycle as cycles
    try:
        evidence=cycles.export_verified_replay(cycle_id)
    except (cycles.CycleInvalid,cycles.CycleConflict) as exc:
        raise LearningInvalid(str(exc)) from exc
    steps=_valid_replay(evidence["steps"])
    now=datetime.now(timezone.utc).isoformat()
    with _LOCK:
        data=_read()
        old=data.get(slug)
        if old is not None:
            if _valid_replay(old.get("steps"))!=steps:
                raise LearningInvalid("Ese nombre ya corresponde a otro procedimiento.")
            count=int(old.get("evidence_count",1))+1
        else:
            if len(data)>=_LIMIT:raise LearningUnavailable("Máximo de procedimientos alcanzado.")
            count=1
        data[slug]={"name":label.strip(),"steps":steps,
                    "source":"verified_sky_cycle","last_verified_at":now,
                    "evidence_count":count}
        _save(data)
    return {"id":slug,"name":label.strip(),"state":"learned_from_verified_cycle",
            "verified":True,"evidence_count":count,"steps":len(steps),
            "auto_executed":False}


def plan_replay(slug:str,*,device:str="local",origin:str="chat")->dict:
    if not isinstance(slug,str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug) or len(slug)>45:
        raise LearningInvalid("Identificador inválido.")
    with _LOCK:
        item=_read().get(slug)
    if not isinstance(item,dict) or item.get("source")!="verified_sky_cycle":
        raise LearningInvalid("Procedimiento no encontrado o sin evidencia.")
    steps=_valid_replay(item.get("steps"))
    from . import sky_execution_cycle as cycles
    if cycles.caps.parada_activa():
        raise LearningUnavailable("Parada de emergencia activa.")
    try:
        return cycles.create(steps,dispositivo=device,origin=origin)
    except (cycles.CycleInvalid,cycles.CycleConflict) as exc:
        raise LearningUnavailable(str(exc)) from exc


def delete(slug:str,*,approved:bool)->bool:
    if approved is not True:raise LearningInvalid("Debés confirmar la eliminación.")
    if not isinstance(slug,str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug) or len(slug)>45:
        raise LearningInvalid("Identificador inválido.")
    with _LOCK:
        data=_read()
        if slug not in data:return False
        del data[slug]
        _save(data)
        return True


def interpretar(texto:str,*,device:str="local",modo:str="chat")->dict|None:
    """Voice/text recall; creates a plan, NEVER executes or approves its steps."""
    if not isinstance(texto,str) or len(texto)>200:return None
    match=re.fullmatch(r"(?:oye\s+)?(?:sky[\s,:]+)?(?:repite|repet[ií]|prepara|prepar[aá])\s+"
                       r"(?:el\s+)?procedimiento\s+([a-zA-ZÀ-ÿ0-9][a-zA-ZÀ-ÿ0-9 -]{2,60})",
                       texto.strip(),re.I)
    if not match:return None
    try:
        slug=_slug(match.group(1))
        plan=plan_replay(slug,device=device,origin=modo)
        return {"tipo":"ciclo","mensaje":"Recuperé un procedimiento comprobado. Confirmá cada paso.",
                "ciclo":plan,"proveedor":"sky-experience-learning"}
    except (LearningInvalid,LearningUnavailable) as exc:
        return {"tipo":"error","mensaje":"No pude recuperar ese procedimiento: "+str(exc)[:160]}
