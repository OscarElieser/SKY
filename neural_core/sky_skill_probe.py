"""Explicit, owner-initiated live probes for SKY integrations.

No probes run on startup or from the catalogue. Each probe executes a bounded
read-only operation against the actual provider and records ONLY status,
latency, timestamp and a generic failure code (never tokens or response data).
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from . import sky_skillpack as skills

_LEDGER=Path.home()/".neuralt"/"sky_skill_live_checks.json"
_READONLY={
    "aws-workflow-deploy":{"operation":"identity"},
    "google-workspace-connector":{"service":"drive"},
    "slack-communicator":{"operation":"whoami"},
    "notion-workspace":{},
    "linear-sync":{},
    "hubspot-crm":{},
    "vercel-plugin":{},
    "typefully":{},
    "github-connector":{"repository":"OscarElieser/SKY"},
    "docker-manager":{},
    "scientific-researcher":{"query":"mathematics education"},
    "claude-d3js-skill":{"values":[1,2,3,4]},
}
_LOCAL_ARTIFACTS={"pdf-pro":"pdf","xlsx-advanced":"xlsx",
                 "docx-coauthoring":"docx","pptx-generator":"pptx"}

def _load():
    try:
        data=json.loads(_LEDGER.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except (ValueError,OSError):
        return {}

def _save(data):
    _LEDGER.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    target=_LEDGER.with_suffix(".tmp")
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    try:target.chmod(0o600)
    except OSError:pass
    target.replace(_LEDGER)
    try:_LEDGER.chmod(0o600)
    except OSError:pass

def read():
    return {
       "results":_load(),
       "definition":"Solo pruebas explícitas; un éxito pasado no demuestra disponibilidad presente.",
       "tested_hardware":False,
       "probes_do_not_deploy_publish_or_change_accounts":True,
    }

def probe(skill_id:str):
    if skill_id not in {x["id"] for x in skills.catalogue()["skills"]}:
        raise ValueError("Skill fuera del catálogo.")
    start=time.perf_counter()
    at=datetime.now(timezone.utc).isoformat()
    # Purposefully skip providers that require chargeable search/scrape requests,
    # new OAuth setup or a read resource chosen by the user.
    payload=_READONLY.get(skill_id)
    local=_LOCAL_ARTIFACTS.get(skill_id)
    if payload is None and not local:
        raise ValueError("Esta skill requiere una prueba explícita con sus parámetros o recursos de usuario.")
    try:
        if local:
            from .sky_office import create_document
            spec={"kind":local,"title":"Prueba controlada SKY","content":"Prueba de creación local SKY",
                  "headers":["Dato","Valor"],"rows":[["SKY",1]]} if local=="xlsx" else {
                  "kind":local,"title":"Prueba controlada SKY","content":"Prueba de creación local SKY"}
            generated=create_document(spec)
            ok=bool(generated.data and len(generated.data)>10)
            observed={"artifact_bytes":len(generated.data)}
        else:
            response=skills.execute(skill_id,payload)
            ok=bool(isinstance(response,dict) and response.get("ok") is not False)
            observed={"provider_http_status":response.get("provider_http_status")}
        state="verified" if ok else "failed"
    except (skills.SkillInvalid,skills.SkillUnavailable,ValueError,RuntimeError,ImportError,OSError) as exc:
        state="failed"
        observed={"failure_type":type(exc).__name__}
    duration=round((time.perf_counter()-start)*1000,2)
    record={"skill_id":skill_id,"checked_at_utc":at,"result":state,
            "latency_ms":duration,"scope":"read_only_live_probe_or_local_artifact",**observed}
    ledger=_load()
    ledger[skill_id]=record
    _save(ledger)
    return record
