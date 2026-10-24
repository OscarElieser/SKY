"""SKY Operational Cycle: auditable, fail-closed multi-step actions for desktop and mobile clients.

No model may directly execute device actions through this module. Explicit
owner approval advances ONE allowlisted step via the already-authorized agent.
Commands sent, pending, and physically verified are distinct states.
"""
from __future__ import annotations

import copy
import re
import secrets
import threading
import time
from urllib.parse import urlsplit

from . import sky_capacidades as caps
from . import sky_asistente_personal as assistant

_LOCK = threading.RLock()
_PLANS: dict[str, dict] = {}
_TTL_SECONDS = 30 * 60
_MAX_PLANS = 60
_MAX_STEPS = 6
_ALLOWED = frozenset({
    "status", "launch_app", "open_url", "open_file", "window_action",
    "media_key", "media_control", "volume", "type_text", "organize_windows",
})
_DISPATCHED = frozenset({"SENT", "RUNNING", "PENDING", "DISPATCHED"})
_TERMINAL = frozenset({"VERIFIED", "FAILED", "CANCELLED"})


class CycleInvalid(ValueError):
    pass


class CycleConflict(RuntimeError):
    pass


def _clean() -> None:
    now = time.monotonic()
    for sid in list(_PLANS):
        if now - _PLANS[sid]["updated_monotonic"] > _TTL_SECONDS:
            del _PLANS[sid]


def _validate_step(step: dict) -> dict:
    if not isinstance(step, dict):
        raise CycleInvalid("Cada paso debe ser un objeto JSON.")
    action = step.get("action")
    params = step.get("params", {})
    if not isinstance(action, str) or action not in _ALLOWED or action not in caps.ACCION_A_CAPACIDAD:
        raise CycleInvalid("La acción no forma parte del registro permitido de SKY.")
    if not isinstance(params, dict) or len(params) > 12:
        raise CycleInvalid("Parámetros inválidos.")
    # Only JSON-compatible, bounded action inputs may cross to a device agent.
    import json
    try:
        size = len(json.dumps(params, ensure_ascii=False, allow_nan=False))
    except (ValueError, TypeError) as exc:
        raise CycleInvalid("Los parámetros deben ser JSON válido.") from exc
    if size > 4000:
        raise CycleInvalid("Demasiados datos en un paso.")
    if action == "open_url":
        url = params.get("url")
        if not isinstance(url, str):
            raise CycleInvalid("Falta la URL.")
        try:
            caps.validar_url_https(url)
        except ValueError as exc:
            raise CycleInvalid("URL no permitida.") from exc
    if action == "launch_app":
        app = params.get("app")
        if not isinstance(app, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{1,39}", app):
            raise CycleInvalid("Nombre de aplicación inválido.")
    if action == "type_text":
        val = params.get("text", "")
        if not isinstance(val, str) or not 1 <= len(val) <= 2000:
            raise CycleInvalid("El texto debe tener entre 1 y 2000 caracteres.")
    if action == "window_action" and params.get("subaction", "list") not in {
        "list", "focus", "minimize", "restore", "close", "organize"
    }:
        raise CycleInvalid("Operación de ventana no autorizada.")
    name = step.get("label", action)
    if not isinstance(name, str) or not 1 <= len(name) <= 120:
        raise CycleInvalid("Etiqueta de paso inválida.")
    # Labels are visible through the status endpoint; never echo private text,
    # file paths, or URLs that can contain personal query parameters.
    private_labels = {
        "type_text": "Escribir texto autorizado en la aplicación",
        "open_file": "Abrir un archivo autorizado",
        "open_url": "Solicitar apertura de página web",
    }
    name = private_labels.get(action, name)
    return {"action": action, "params": copy.deepcopy(params), "label": name,
            "risk": caps.nivel_riesgo(action, params), "state": "READY",
            "result": None, "command_id": None, "attempts": 0}


def is_sequence(text: str) -> bool:
    """Only explicit multi-action imperatives are intercepted from regular chat."""
    if not isinstance(text, str) or len(text) > 1500:
        return False
    raw = re.sub(r"^(?:(?:oye|hey|ok)\s+)?sky[\s,:!¡-]+", "", text.strip(), flags=re.I)
    starts = re.match(r"^(?:abre|abr[ií]|abrir|inicia|lanza|ejecuta|pon|pone|muestra|m[uú]estrame|"
                      r"silencia|baja|sube|escribe|minimiza|restaura|cierra|reproduce)\b", raw, re.I)
    return bool(starts and re.search(r"\s+(?:y\s+luego|y\s+despu[eé]s|luego|despu[eé]s|"
                                      r"a\s+continuaci[oó]n)\s+", raw, re.I))


def from_text(text: str) -> list[dict]:
    """Deterministic action parser. No uncontrolled LLM-to-device execution."""
    if not isinstance(text, str) or not 4 <= len(text.strip()) <= 1500:
        raise CycleInvalid("Instrucción vacía o demasiado extensa.")
    parts = re.split(r"\s+(?:y\s+luego|y\s+despu[eé]s|luego|despu[eé]s|a\s+continuaci[oó]n)\s*[,;:]?\s*",
                     text.strip(), flags=re.I)
    if not 1 <= len(parts) <= _MAX_STEPS or any(not p.strip() for p in parts):
        raise CycleInvalid("Se admiten entre 1 y 6 pasos separados por 'y luego'.")
    steps = []
    for part in parts:
        order = assistant.interpretar(part.strip())
        if not isinstance(order, dict) or order.get("action") not in _ALLOWED:
            raise CycleInvalid("No entendí esta acción: " + part.strip()[:100])
        steps.append({"action": order["action"], "params": order.get("params", {}),
                      "label": order.get("description", part.strip())[:120]})
    return steps


def create(steps: list[dict], *, dispositivo: str = "local", origin: str = "chat") -> dict:
    if not isinstance(steps, list) or not 1 <= len(steps) <= _MAX_STEPS:
        raise CycleInvalid("Se requieren entre 1 y 6 pasos.")
    if not isinstance(dispositivo, str) or not 1 <= len(dispositivo) <= 80:
        raise CycleInvalid("Nombre de dispositivo inválido.")
    if origin not in {"chat", "voz"}:
        raise CycleInvalid("Origen inválido.")
    checked = [_validate_step(item) for item in steps]
    ident = secrets.token_urlsafe(24)
    plan = {"id": ident, "dispositivo": dispositivo, "origin": origin,
            "steps": checked, "cursor": 0, "state": "READY",
            "created_at": time.time(), "updated_monotonic": time.monotonic(),
            "execution_count": 0}
    with _LOCK:
        _clean()
        if len(_PLANS) >= _MAX_PLANS:
            raise CycleConflict("El límite de planes activos fue alcanzado.")
        _PLANS[ident] = plan
    return snapshot(ident)


def _get(ident: str) -> dict:
    _clean()
    if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,60}", ident):
        raise CycleInvalid("Identificador de ciclo inválido.")
    plan = _PLANS.get(ident)
    if plan is None:
        raise CycleConflict("El ciclo expiró o ya no existe.")
    return plan


def snapshot(ident: str) -> dict:
    with _LOCK:
        plan = _get(ident)
        # No expose action body contents in GET; may include private dictated text.
        steps = [{"label": x["label"], "action": x["action"], "risk": x["risk"],
                  "state": x["state"], "command_id": x["command_id"], "attempts": x["attempts"]}
                 for x in plan["steps"]]
        return {"id": ident, "state": plan["state"], "dispositivo": plan["dispositivo"],
                "origin": plan["origin"], "cursor": plan["cursor"],
                "total": len(steps), "steps": steps,
                "verified": sum(x["state"] == "VERIFIED" for x in plan["steps"]),
                "dispatched_unverified": sum(x["state"] == "DISPATCHED" for x in plan["steps"]),
                "complete_verified": plan["state"] == "VERIFIED"}



def export_verified_replay(ident: str) -> dict:
    """Export a narrowly replayable, physically verified routine for SKY learning.

    Exporting *never* executes any action. Text, URLs, paths and browser
    contents are excluded from procedural memory, even if the cycle succeeded.
    """
    from .windows_controller import AUTHORIZED_APPS
    with _LOCK:
        plan = _get(ident)
        if plan["state"] != "VERIFIED" or not plan["steps"]:
            raise CycleConflict("Solo se pueden recordar ciclos terminados y verificados.")
        if any(step["state"] != "VERIFIED" or step["attempts"] != 1
               for step in plan["steps"]):
            raise CycleConflict("Todos los pasos deben estar verificados y ejecutados una vez.")
        allowed = {"status", "launch_app"}
        if any(step["action"] not in allowed for step in plan["steps"]):
            raise CycleConflict("El procedimiento incluye acciones que no es seguro memorizar.")
        steps = []
        for step in plan["steps"]:
            if step["action"] == "status":
                # A read-only probe with no user-supplied arguments.
                if step["params"]:
                    raise CycleConflict("Consulta de estado no segura para reutilizar.")
                steps.append({"action": "status", "params": {}, "label": "Comprobar estado del agente"})
            elif step["action"] == "launch_app":
                app = step["params"].get("app")
                if app not in AUTHORIZED_APPS or set(step["params"]) != {"app"}:
                    raise CycleConflict("Aplicación no registrada para un procedimiento.")
                # A VERIFIED app launch must have been checked by the agent.
                if not step.get("command_id"):
                    raise CycleConflict("Falta evidencia del agente para aprender la aplicación.")
                steps.append({"action": "launch_app", "params": {"app": app},
                              "label": "Abrir " + AUTHORIZED_APPS[app]["desc"][:65]})
        return {"steps": copy.deepcopy(steps), "device": plan["dispositivo"],
                "verified": True, "total": len(steps)}


def cancel(ident: str) -> dict:
    with _LOCK:
        plan = _get(ident)
        if plan["state"] not in {"VERIFIED", "FAILED", "CANCELLED"}:
            plan["state"] = "CANCELLED"
            plan["updated_monotonic"] = time.monotonic()
        return snapshot(ident)


def execute_next(ident: str, invoke, *, approved: bool, pin_check=None) -> dict:
    """Run precisely one previously validated step using SKY's device policy.

    `invoke(action,params,dispositivo)` is supplied by the existing API.
    The service never accepts a command or URL for the agent from the request.
    """
    if approved is not True:
        raise CycleInvalid("Confirmá expresamente este paso.")
    with _LOCK:
        plan = _get(ident)
        if plan["state"] not in {"READY"}:
            raise CycleConflict("El ciclo no está listo para ejecutar otro paso.")
        if caps.parada_activa():
            raise CycleConflict("Parada de emergencia activa: ejecución bloqueada.")
        index = plan["cursor"]
        if index >= len(plan["steps"]):
            raise CycleConflict("No quedan pasos.")
        step = plan["steps"][index]
        if step["state"] != "READY":
            raise CycleConflict("El paso no está listo.")
        if step["risk"] >= 3:
            if pin_check is None:
                raise CycleConflict("Este paso requiere verificación adicional del propietario.")
            pin_check()
        step["attempts"] += 1
        step["state"] = "RUNNING"
        plan["state"] = "RUNNING"
        plan["updated_monotonic"] = time.monotonic()
        start = time.perf_counter()
        try:
            response = invoke(step["action"], copy.deepcopy(step["params"]), plan["dispositivo"])
            if not isinstance(response, dict):
                response = {"ok": False, "status": "FAILED"}
            status = str(response.get("status", "")).upper()
            # The agent's authenticated status query is itself the verified
            # observation; unlike a launched application it has no async task.
            if step["action"] == "status" and response.get("ok") is True and response.get("agent"):
                status = "VERIFIED"
            if response.get("ok") is False or status in {"FAILED", "DENIED", "ERROR"}:
                step["state"] = "FAILED"
                plan["state"] = "FAILED"
            elif status == "VERIFIED":
                step["state"] = "VERIFIED"
                plan["cursor"] += 1
                plan["state"] = "VERIFIED" if plan["cursor"] == len(plan["steps"]) else "READY"
            else:
                # No promote SENT/RUNNING/PENDING/unspecified to VERIFIED.
                step["state"] = "DISPATCHED"
                plan["state"] = "WAITING_VERIFICATION"
            step["command_id"] = response.get("command_id")
            step["result"] = {"status": status or "UNVERIFIED", "ok": response.get("ok"),
                              "elapsed_ms": round((time.perf_counter() - start) * 1000, 1)}
            plan["execution_count"] += 1
            plan["updated_monotonic"] = time.monotonic()
            return {**snapshot(ident), "last_step": step["result"]}
        except Exception:
            step["state"] = "FAILED"
            plan["state"] = "FAILED"
            plan["updated_monotonic"] = time.monotonic()
            raise


def reconcile(ident: str, lookup) -> dict:
    """Only evidence from the authorized existing agent can verify pending work."""
    with _LOCK:
        plan = _get(ident)
        if plan["state"] != "WAITING_VERIFICATION":
            raise CycleConflict("No existe un paso pendiente de verificación.")
        step = plan["steps"][plan["cursor"]]
        command_id = step.get("command_id")
        if not isinstance(command_id, str) or not command_id:
            raise CycleConflict("El agente no devolvió un identificador verificable.")
        data = lookup(command_id, plan["dispositivo"])
        record = data.get("record", {}) if isinstance(data, dict) else {}
        if record.get("command_id") != command_id:
            raise CycleConflict("La evidencia no corresponde a esta acción.")
        status = str(record.get("status", "")).upper()
        if status == "VERIFIED":
            step["state"] = "VERIFIED"
            plan["cursor"] += 1
            plan["state"] = "VERIFIED" if plan["cursor"] == len(plan["steps"]) else "READY"
        elif status == "FAILED":
            step["state"] = "FAILED"
            plan["state"] = "FAILED"
        plan["updated_monotonic"] = time.monotonic()
        return snapshot(ident)
