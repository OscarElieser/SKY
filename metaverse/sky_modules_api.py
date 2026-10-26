"""Bridge autenticado: abre módulos originales de app.py sólo bajo pedido.

No hace precarga de Streamlit ni sustituye servicios propios de SKY.
El proceso secundario sólo escucha en loopback y mantiene la protección XSRF/CORS.
"""
from __future__ import annotations
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from neural_core.sky_module_registry import (
    all_modules, lookup, latest_activation_id, activations_after,
)

ROOT = Path(__file__).resolve().parent.parent
router = APIRouter(prefix="/api/sky/modules", tags=["Módulos SKY"])
_lock = threading.RLock()
_legacy_process = None
_legacy_log = None
STREAMLIT_URL = "http://127.0.0.1:8501"

def _port_busy() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 8501), timeout=0.3):
            return True
    except OSError:
        return False

def _healthy() -> bool:
    try:
        with urllib.request.urlopen(STREAMLIT_URL + "/_stcore/health", timeout=0.8) as response:
            return response.status == 200
    except Exception:
        return False

def start_legacy() -> bool:
    """Inicia Streamlit una sola vez. No mata ni adopta otros procesos."""
    global _legacy_process, _legacy_log
    with _lock:
        if _legacy_process is not None and _legacy_process.poll() is None:
            return _healthy()
        if _port_busy():
            # Otro Streamlit (o programa) ya ocupa 8501: nunca matarlo.
            raise HTTPException(409, "El puerto 8501 está ocupado por una instancia ajena al gestor. Cerrala normalmente antes de activar el módulo.")
        log_path = ROOT / "local_data" / "sky_streamlit_on_demand.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _legacy_log = log_path.open("ab")
        cmd = [
            sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
            "--server.address", "127.0.0.1", "--server.port", "8501",
            "--server.headless", "true", "--browser.gatherUsageStats", "false",
        ]
        _legacy_process = subprocess.Popen(
            cmd, cwd=str(ROOT), stdin=subprocess.DEVNULL,
            stdout=_legacy_log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        for _ in range(20):
            if _healthy():
                return True
            if _legacy_process.poll() is not None:
                raise HTTPException(503, "Streamlit terminó al iniciarse. Revisá local_data/sky_streamlit_on_demand.log")
            time.sleep(0.25)
        return False

@router.get("")
def catalog():
    return {"modules": all_modules(), "count": len(all_modules())}

@router.get("/events/latest")
def events_latest():
    return {"cursor": latest_activation_id()}

@router.get("/events")
def events(after: int = Query(default=0, ge=0)):
    return {"events": activations_after(after)}

@router.post("/{module_id}/open")
def open_module(module_id: str):
    module = lookup(module_id)
    if not module:
        raise HTTPException(404, "Módulo no registrado en SKY")
    if module["backend"] == "hud":
        return {"module": module, "ready": True, "url": module["url"]}
    ready = start_legacy()
    # La URL es fija en loopback: jamás se permite un host controlado por la solicitud.
    return {
        "module": module, "ready": ready,
        "url": STREAMLIT_URL + "/?sky_mod=" + module_id + "&embed=true",
        "backend": "streamlit_on_demand",
    }

@router.get("/{module_id}/status")
def module_status(module_id: str):
    module = lookup(module_id)
    if not module:
        raise HTTPException(404, "Módulo desconocido")
    if module["backend"] == "hud":
        return {"ready": True}
    return {"ready": _healthy()}


# Eventos de ventanas del asistente de voz independiente (Vosk).
# El HUD los recoge autenticado sin iniciar una segunda captura del micrófono.
@router.get("/windows/events/latest")
def window_events_latest():
    from neural_core.sky_hud_window_requests import latest
    return {"cursor": latest()}

@router.get("/windows/events")
def window_events(after: int = Query(default=0, ge=0)):
    from neural_core.sky_hud_window_requests import since
    return {"events": since(after)}
