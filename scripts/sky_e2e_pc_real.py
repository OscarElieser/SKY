"""Authorized Windows end-to-end smoke test for SKY. NOT an offline mock.

Run ONLY on your own Windows session with the SKY desktop agent already active:
    python scripts/sky_e2e_pc_real.py --confirm --app calculator
This test does not install apps, send email, delete files or alter permissions.
Every result carries its actual status (SENT is NOT VERIFIED).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from neural_core.dispositivos import validate_endpoint

PORT=int(os.getenv("SKY_DEVICE_PORT","8766"))
BASE=validate_endpoint("http://127.0.0.1:"+str(PORT))
TOKEN=Path.home()/".neuralt"/"device_agent.token"
APPS=("calculator","word","excel","powerpoint","text_editor")

def _agent(token:str,path:str,body:dict|None=None):
    if not token or len(token)<32:raise RuntimeError("El token local del agente no está configurado.")
    data=json.dumps(body).encode("utf-8") if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},
        method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req,timeout=18) as res:
            return json.loads(res.read(120000))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Agente devolvió HTTP "+str(exc.code)+" (comprobá política y permisos).") from exc

def _execute(token,action,params,observed):
    start=time.perf_counter()
    try:
        r=_agent(token,"/action",{"action":action,"params":params})
        status=str(r.get("status","UNVERIFIED")).upper()
        record={"action":action,"status":status,"result_ok":r.get("ok") is True,
                "latency_ms":round((time.perf_counter()-start)*1000,1)}
        cid=r.get("command_id")
        if isinstance(cid,str) and cid:
            # Same agent's evidence endpoint, never trust an HTTP 200 by itself.
            from urllib.parse import urlencode
            proof=_agent(token,"/verify_action?"+urlencode({"command_id":cid}))
            rec=proof.get("record",{})
            if rec.get("command_id")==cid:
                record["verified_status"]=rec.get("status")
                record["physically_verified"]=rec.get("status")=="VERIFIED"
            else:
                record["physically_verified"]=False
        else:
            record["physically_verified"]=status=="VERIFIED"
        observed.append(record)
    except (RuntimeError,ValueError,OSError) as exc:
        observed.append({"action":action,"physically_verified":False,"status":"FAILED",
                         "error_type":type(exc).__name__})

def run(args):
    if platform.system()!="Windows":
        raise RuntimeError("Esta prueba física se ejecuta exclusivamente en Windows.")
    if not args.confirm:
        raise RuntimeError("Añadí --confirm solo cuando estés frente al equipo.")
    if args.app not in APPS:raise ValueError("Aplicación no admitida.")
    token=TOKEN.read_text(encoding="utf-8").strip() if TOKEN.exists() else os.getenv("SKY_DEVICE_TOKEN","")
    status=_agent(token,"/status")
    if status.get("ok") is not True:
        raise RuntimeError("El agente no confirmó su estado.")
    report={"at_utc":datetime.now(timezone.utc).isoformat(),
            "device_platform":"Windows","agent_version":status.get("version"),
            "app_requested":args.app,"observations":[],"tests_are_real_hardware":True}
    _execute(token,"launch_app",{"app":args.app},report["observations"])
    # Create a real file using the existing SKY Office engine; never overwrite.
    from neural_core.sky_office import create_document
    unique=secrets.token_hex(7)
    from neural_core.windows_controller import resolve_windows_special_folder
    docs=resolve_windows_special_folder("documentos")
    if docs is None:
        raise RuntimeError("No se encontró la carpeta Documentos autorizada en Windows.")
    folder=docs/"SKY_E2E"
    folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    spec={"kind":"docx","title":"SKY E2E "+unique,
          "content":"Prueba local autorizada para verificar generación de Word en SKY."}
    file=create_document(spec)
    output=folder/(unique+".docx")
    output.write_bytes(file.data)
    report["document"]={"exists":output.is_file(),"bytes":output.stat().st_size,
                        "valid_zip_signature":output.read_bytes()[:2]==b"PK"}
    if args.open_document:
        _execute(token,"open_file",{"target":str(output)},report["observations"])
    if args.media_test:
        _execute(token,"media_key",{"key":"play_pause"},report["observations"])
    report["overall_pass"]=bool(report["document"]["valid_zip_signature"] and
                       all(x.get("physically_verified") for x in report["observations"]))
    report["note"]="Solo acciones verificadas cuentan como éxito; otras pueden estar enviadas o pendientes."
    # Avoid storing local paths, tokens, microphone contents or document text.
    target=folder/("report_"+unique+".json")
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    try:target.chmod(0o600)
    except OSError:pass
    return report

def main():
    ap=argparse.ArgumentParser(description="Prueba E2E real, local, autorizada de SKY Windows.")
    ap.add_argument("--confirm",action="store_true",help="Acepto abrir apps y crear un documento privado de prueba.")
    ap.add_argument("--app",choices=APPS,default="calculator")
    ap.add_argument("--open-document",action="store_true",help="Abre el documento creado si está autorizado.")
    ap.add_argument("--media-test",action="store_true",help="Envía Play/Pausa (solo con permiso).")
    args=ap.parse_args()
    try:
        print(json.dumps(run(args),ensure_ascii=False,indent=2))
    except (RuntimeError,ValueError,OSError) as exc:
        ap.exit(status=2,message="E2E rechazado: "+str(exc)+"\n")

if __name__=="__main__":
    main()
