"""SKY Sentinel incident decisions and owner-initiated local emergency shutdown.

UNAUTHORIZED API CALLS MUST NOT TRIGGER A POWER OFF. Otherwise any attacker
could take down the machine simply by requesting invalid logins repeatedly.
Default deny + audit + existing per-IP throttling. Shutdown is an independent,
explicit, short-lived, MFA-protected local owner decision.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import platform
import secrets
import subprocess
import threading
import time
from collections import Counter, deque

_LOCK = threading.RLock()
_EVENTS: deque[tuple[float,str,str]] = deque(maxlen=512)
_NONCE = secrets.token_bytes(24)
_PENDING: dict[str,tuple[float,str]] = {}
_SHUTDOWN_TIMER: threading.Timer | None = None
_DENIAL_WINDOW_SECONDS = 300


def register_denial(remote: str, path: str) -> dict:
    """Sanitize telemetry. No passwords, tokens, request body or real IP retained."""
    remote_digest = hashlib.sha256(_NONCE + str(remote).encode("utf-8")[:128]).hexdigest()[:20]
    family = "mfa" if path.startswith("/api/security/owner-mfa") else (
        "api" if path.startswith(("/api/","/v1/")) else "other")
    timestamp=time.monotonic()
    with _LOCK:
        _EVENTS.append((timestamp,remote_digest,family))
        attempts=sum(1 for when,who,_ in _EVENTS
                     if who==remote_digest and timestamp-when<=_DENIAL_WINDOW_SECONDS)
    return {"decision":"ACCESO DENEGADO","action":"deny_and_audit",
            "shutdown_triggered":False,
            "suspicious":attempts>=5,"recent_failures":attempts}


def status() -> dict:
    now=time.monotonic()
    with _LOCK:
        observations=[event for event in _EVENTS if now-event[0]<=_DENIAL_WINDOW_SECONDS]
    counts=Counter(family for _,_,family in observations)
    return {"decision_on_unauthorized":"ACCESO DENEGADO",
            "recent_denied":len(observations),"by_category":dict(counts),
            "shutdown_on_failed_login":False,
            "shutdown_available_only_to_owner":True,
            "manual_shutdown_enabled":os.getenv("SKY_OWNER_LOCAL_SHUTDOWN","0")=="1",
            "windows_lock_supported":platform.system()=="Windows",
            "warning":"Los intentos remotos jamás deben apagar el equipo automáticamente."}


def _local_owner_guard(client_host: str) -> None:
    from metaverse import owner_mfa
    if client_host not in ("127.0.0.1","::1"):
        raise PermissionError("Disponible exclusivamente desde el servicio local.")
    if platform.system()!="Windows":
        raise RuntimeError("El bloqueo y apagado del equipo requieren Windows.")
    if not owner_mfa.required():
        raise PermissionError("Activá primero SKY_OWNER_MFA_SECRET para las acciones críticas.")
    if os.getenv("SKY_OWNER_LOCAL_SHUTDOWN","0")!="1":
        raise PermissionError("El apagado está desactivado: habilitalo de forma local y explícita.")


def prepare_shutdown(client_host: str) -> dict:
    """Called ONLY after require_key validated an owner MFA session."""
    _local_owner_guard(client_host)
    token=secrets.token_urlsafe(32)
    digest=hashlib.sha256(token.encode("ascii")).hexdigest()
    with _LOCK:
        _PENDING.clear()
        _PENDING[digest]=(time.monotonic()+60,client_host)
    return {"confirmation_token":token,"expires_in":60,
            "message":"SKY: apagado manual en 120 segundos, sin forzar aplicaciones.",
            "countdown_seconds":120, "initiated":False}


def shutdown_confirmed(client_host: str, token: str, phrase: str) -> dict:
    _local_owner_guard(client_host)
    if phrase != "AUTORIZO APAGAR MI EQUIPO" or not isinstance(token,str) or len(token)>100:
        raise PermissionError("Falta una confirmación exacta del propietario.")
    digest=hashlib.sha256(token.encode("utf-8")).hexdigest()
    with _LOCK:
        item=_PENDING.get(digest)
        if item is None or item[0] < time.monotonic() or item[1] != client_host:
            raise PermissionError("La autorización caducó o es inválida.")
        del _PENDING[digest] # consume before side-effect; never replay
    # Windows 'shutdown /t 120' implicitly forces closure on many versions,
    # risking unsaved data. Instead, keep a cancellable timer and call /t 0
    # WITHOUT /f after 120 seconds. If the service dies, the timer dies safely.
    def _request_shutdown():
        global _SHUTDOWN_TIMER
        try:
            subprocess.run(["shutdown","/s","/t","0"],check=True,timeout=8,
                           capture_output=True,text=True)
        finally:
            with _LOCK:
                _SHUTDOWN_TIMER = None

    global _SHUTDOWN_TIMER
    with _LOCK:
        if _SHUTDOWN_TIMER is not None:
            raise PermissionError("Ya existe una cuenta regresiva de apagado.")
        timer=threading.Timer(120,_request_shutdown)
        timer.daemon=True
        _SHUTDOWN_TIMER=timer
        timer.start()
    return {"shutdown_scheduled":True,"countdown_seconds":120,
            "cancel":"POST /api/security/sentinel/shutdown/abort",
            "reason":"explicit_owner_confirmation"}


def abort_shutdown(client_host: str) -> dict:
    _local_owner_guard(client_host)
    global _SHUTDOWN_TIMER
    with _LOCK:
        if _SHUTDOWN_TIMER is None:
            return {"shutdown_aborted":False,"reason":"not_scheduled"}
        _SHUTDOWN_TIMER.cancel()
        _SHUTDOWN_TIMER=None
    return {"shutdown_aborted":True}
