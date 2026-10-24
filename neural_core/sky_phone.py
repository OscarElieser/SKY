"""SKY Teléfono: voluntary, verified-number communication using official providers.

This is NOT a mobile carrier, a SIM replacement, a browser softphone, or an
OS-wide call blocker. Twilio sends SMS and bridges voice via the owner's real
verified handset; Jitsi meetings use an external service with user consent.

Every paid action requires: SKY authenticated owner, explicit approval,
configured PIN (checked by the API), prior phone verification, an opt-in
feature flag, destination consent and local rate limits.

No background calls, bulk messages, automatic answering, recordings,
contact scraping, number porting or phone OS permission escalation.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
import os
import re
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, HTTPSHandler, HTTPRedirectHandler, build_opener
from xml.sax.saxutils import escape as escape_xml

LOCK = threading.RLock()
STORE = Path.home() / ".neuralt" / "sky_phone.json"
MAX_BYTES = 100_000
PHONE_RE = re.compile(r"^\+[1-9][0-9]{7,14}$")
TWILIO_RE = re.compile(r"^(?:AC|VA)[a-fA-F0-9]{32}$")
SID_RE = re.compile(r"^(?:SM|MM|CA)[a-fA-F0-9]{32}$")


class PhoneInvalid(ValueError): pass
class PhoneUnavailable(RuntimeError): pass


def normalize(number: str) -> str:
    """International E.164; unknown local prefixes cannot be guessed."""
    if not isinstance(number, str) or len(number) > 22:
        raise PhoneInvalid("Indicá el número internacional, por ejemplo +505XXXXXXXX.")
    value = number.strip().replace(" ", "").replace("-", "")
    if not PHONE_RE.fullmatch(value):
        raise PhoneInvalid("Número inválido: usá + seguido de país y número (E.164).")
    return value


def _mask(number: str) -> str:
    return "••••" + number[-4:]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load() -> dict:
    try:
        if not STORE.exists():
            return {"blocked": [], "rate": {}, "pending": {}}
        if STORE.stat().st_size > MAX_BYTES:
            raise PhoneUnavailable("Estado del teléfono demasiado grande.")
        obj = json.loads(STORE.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise PhoneUnavailable("Estado de teléfono corrupto.")
        return obj
    except (OSError, ValueError) as exc:
        raise PhoneUnavailable("No se pudo cargar el estado privado del teléfono.") from exc


def _save(data: dict):
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode()) > MAX_BYTES:
        raise PhoneUnavailable("Se alcanzó el límite de almacenamiento.")
    STORE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = STORE.with_name(STORE.name + "." + secrets.token_hex(5) + ".tmp")
    try:
        with tmp.open("x", encoding="utf-8") as fp:
            fp.write(raw)
        try: tmp.chmod(0o600)
        except OSError: pass
        tmp.replace(STORE)
        try: STORE.chmod(0o600)
        except OSError: pass
    finally:
        try: tmp.unlink(missing_ok=True)
        except OSError: pass


def _cost_enabled() -> bool:
    return os.getenv("SKY_PHONE_ALLOW_PAID", "") == "1"


def _enabled() -> bool:
    return os.getenv("SKY_PHONE_ENABLED", "") == "1"


def _local_only():
    from .providers import local_only
    if local_only():
        raise PhoneUnavailable("El modo SKY_LOCAL_ONLY impide conexiones telefónicas externas.")


def _credentials(service: str):
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if not re.fullmatch(r"AC[a-fA-F0-9]{32}", sid) or len(token) < 20:
        raise PhoneUnavailable("Twilio no está configurado (Account SID/Auth Token).")
    if service == "verify":
        verify = os.getenv("TWILIO_VERIFY_SERVICE_SID", "").strip()
        if not re.fullmatch(r"VA[a-fA-F0-9]{32}", verify):
            raise PhoneUnavailable("Configurá TWILIO_VERIFY_SERVICE_SID.")
        return sid, token, verify
    outbound = os.getenv("TWILIO_PHONE_NUMBER", "")
    sender = normalize(outbound)
    return sid, token, sender


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PhoneUnavailable("El proveedor intentó redirigir una solicitud.")


def _post(host: str, path: str, fields: dict, sid: str, token: str) -> dict:
    if host not in ("verify.twilio.com", "api.twilio.com") or not path.startswith("/") or ".." in path or "//" in path:
        raise PhoneInvalid("Destino telefónico externo no permitido.")
    auth = base64.b64encode((sid + ":" + token).encode()).decode()
    data = urlencode(fields).encode("utf-8")
    req = Request("https://" + host + path, data=data, method="POST", headers={
        "Authorization": "Basic " + auth, "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json", "User-Agent": "SKY-Phone/1.0"})
    try:
        with build_opener(_RejectRedirect, HTTPSHandler()).open(req, timeout=15) as res:
            raw = res.read(40001)
            if len(raw) > 40000:
                raise PhoneUnavailable("Respuesta de proveedor demasiado grande.")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise PhoneUnavailable("Respuesta telefónica desconocida.")
            return result
    except (OSError, ValueError) as exc:
        # Twilio errors may echo targets or credentials; do not expose them.
        raise PhoneUnavailable("El servicio telefónico no confirmó la operación.") from exc


def _require():
    if not _enabled():
        raise PhoneUnavailable("Activá SKY_PHONE_ENABLED=1 para usar SKY Teléfono.")
    _local_only()


def _throttle(state: dict, action: str, limit: int):
    today = _day()
    data = state.setdefault("rate", {})
    if data.get("day") != today:
        data.clear()
        data["day"] = today
    used = int(data.get(action, 0))
    if used >= limit:
        raise PhoneUnavailable("Límite diario alcanzado para " + action + ".")
    data[action] = used + 1
    _save(state)


def _verified(state: dict) -> str:
    value = str(state.get("verified_phone") or "")
    if not PHONE_RE.fullmatch(value):
        raise PhoneInvalid("Primero verificá que el número de teléfono es tuyo.")
    return value


def _check_destination(state: dict, number: str):
    dest = normalize(number)
    if dest in state.get("blocked", []):
        raise PhoneInvalid("Número bloqueado dentro de SKY.")
    return dest


def readiness() -> dict:
    with LOCK:
        state = _load()
        owner = state.get("verified_phone", "")
        return {
            "enabled": _enabled(),
            "owner_phone_verified": bool(PHONE_RE.fullmatch(str(owner))),
            "verified_number_masked": _mask(owner) if owner else None,
            "verify_service_configured":bool(os.getenv("TWILIO_VERIFY_SERVICE_SID")),
            "twilio_sms_voice_configured":bool(os.getenv("TWILIO_ACCOUNT_SID") and
                                              os.getenv("TWILIO_AUTH_TOKEN") and
                                              os.getenv("TWILIO_PHONE_NUMBER")),
            "paid_actions_enabled":_cost_enabled(),
            "blocked_count":len(state.get("blocked", [])),
            "video_host":_video_host(),
            "phone_carrier_sim_control":False,
            "native_os_phone_blocking":False,
            "browser_pstn_audio":False,
            "inbound_sms_call_webhook":False,
            "live_tested":False,
            "note":"SKY llama a tu teléfono verificado y te conecta con el destino; los SMS salen desde Twilio.",
        }


def begin_verify(number: str, *, approved: bool) -> dict:
    if approved is not True:
        raise PhoneInvalid("Debés autorizar el envío del código.")
    _require()
    if os.getenv("SKY_PHONE_ALLOW_VERIFY") != "1":
        raise PhoneUnavailable("Verificación no habilitada: SKY_PHONE_ALLOW_VERIFY=1.")
    number = normalize(number)
    sid, token, service = _credentials("verify")
    with LOCK:
        state = _load()
        if number in state.get("blocked", []):
            raise PhoneInvalid("No se puede verificar un número bloqueado.")
        _throttle(state, "verify", 5)
    response = _post("verify.twilio.com", f"/v2/Services/{service}/Verifications",
                     {"To":number, "Channel":"sms"}, sid, token)
    if response.get("status") != "pending":
        raise PhoneUnavailable("Twilio no confirmó el envío del código.")
    with LOCK:
        state = _load()
        state["pending"] = {"phone":number, "created_at":time.time(), "attempts":0}
        _save(state)
    return {"status":"otp_requested","phone_masked":_mask(number),
            "verified":False,"cost_possible":True,"code_not_stored":True}


def finish_verify(number: str, code: str) -> dict:
    _require()
    number = normalize(number)
    if not isinstance(code,str) or not re.fullmatch(r"[0-9]{4,10}",code):
        raise PhoneInvalid("Código de verificación inválido.")
    with LOCK:
        state=_load()
        pending=state.get("pending") or {}
        if pending.get("phone")!=number or time.time()-float(pending.get("created_at",0))>600:
            raise PhoneInvalid("La verificación ha expirado. Solicitá un código nuevo.")
        if int(pending.get("attempts",0))>=5:
            raise PhoneInvalid("Se alcanzó el máximo de intentos de verificación.")
        pending["attempts"]=int(pending.get("attempts",0))+1
        _save(state)
    sid,token,service = _credentials("verify")
    result = _post("verify.twilio.com",f"/v2/Services/{service}/VerificationCheck",
                   {"To":number,"Code":code},sid,token)
    if result.get("status")!="approved":
        return {"verified":False,"status":"verification_not_approved"}
    with LOCK:
        data=_load()
        if (data.get("pending") or {}).get("phone")!=number:
            raise PhoneInvalid("La solicitud ya no está vigente.")
        data["verified_phone"]=number
        data["verified_at"]=_now()
        data.pop("pending",None)
        _save(data)
    return {"verified":True,"phone_masked":_mask(number),
            "status":"verified_by_twilio_otp"}


def revoke_owner(*,approved:bool)->dict:
    if approved is not True:raise PhoneInvalid("Se requiere confirmación.")
    with LOCK:
        data=_load()
        data.pop("verified_phone",None)
        data.pop("verified_at",None)
        data.pop("pending",None)
        _save(data)
    return {"revoked":True,"phone_owner_verified":False}


def blocked_list()->dict:
    with LOCK:
        numbers = sorted(set(_load().get("blocked",[])))
        return {"numbers":[{"id":hashlib.sha256(n.encode()).hexdigest()[:16],
                            "masked":_mask(n)} for n in numbers],
                "total":len(numbers),
                "scope":"sky_only_not_carrier_or_operating_system"}


def set_block(number: str, *, blocked:bool, approved:bool)->dict:
    if approved is not True:raise PhoneInvalid("Se requiere confirmación.")
    number=normalize(number)
    with LOCK:
        data=_load()
        if number==data.get("verified_phone"):
            raise PhoneInvalid("No podés bloquear el número propietario verificado.")
        numbers=set(data.get("blocked",[]))
        if blocked:numbers.add(number)
        else:numbers.discard(number)
        if len(numbers)>300:raise PhoneInvalid("Máximo de números bloqueados alcanzado.")
        data["blocked"]=sorted(numbers)
        _save(data)
        return {"blocked":blocked,"phone_masked":_mask(number),
                "scope":"sky_only","total":len(numbers)}


def unblock_by_id(identifier:str,*,approved:bool)->dict:
    if approved is not True:raise PhoneInvalid("Se requiere confirmación.")
    if not isinstance(identifier,str) or not re.fullmatch(r"[a-f0-9]{16}",identifier):
        raise PhoneInvalid("Identificador de bloqueo inválido.")
    with LOCK:
        state=_load(); numbers=set(state.get("blocked",[]))
        matched=[n for n in numbers if hashlib.sha256(n.encode()).hexdigest()[:16]==identifier]
        if len(matched)!=1:raise PhoneInvalid("Número bloqueado no encontrado.")
        number=matched[0];numbers.remove(number)
        state["blocked"]=sorted(numbers);_save(state)
    return {"blocked":False,"phone_masked":_mask(number),"scope":"sky_only"}


def send_sms(number: str, message: str, *,approved:bool,recipient_consented:bool)->dict:
    if approved is not True or recipient_consented is not True:
        raise PhoneInvalid("Confirmá el envío y que tenés permiso del destinatario.")
    _require()
    if not _cost_enabled():raise PhoneUnavailable("Mensajería de pago desactivada.")
    if not isinstance(message,str) or not 1<=len(message.strip())<=800:
        raise PhoneInvalid("Mensaje de 1 a 800 caracteres requerido.")
    sid,token,sender=_credentials("sms")
    with LOCK:
        state=_load()
        _verified(state)
        dest=_check_destination(state,number)
        _throttle(state,"sms",10)
    response=_post("api.twilio.com",f"/2010-04-01/Accounts/{sid}/Messages.json",
                 {"To":dest,"From":sender,"Body":message.strip()},sid,token)
    call_sid=str(response.get("sid",""))
    if not re.fullmatch(r"(?:SM|MM)[a-fA-F0-9]{32}",call_sid):
        raise PhoneUnavailable("Twilio no confirmó la aceptación del SMS.")
    return {"status":"queued_unverified","message_sid":call_sid,
            "destination_masked":_mask(dest),"sent_to_carrier_confirmed":False,
            "delivered_to_phone_verified":False,"may_cost_money":True}


def call_bridge(number: str, *, approved:bool, recipient_consented:bool)->dict:
    """Twilio calls the verified owner handset FIRST, then dials the destination.

    Does not capture the browser mic; two PSTN call legs can generate charges.
    """
    if approved is not True or recipient_consented is not True:
        raise PhoneInvalid("Confirmá la llamada y que contás con permiso para contactar.")
    _require()
    if not _cost_enabled():raise PhoneUnavailable("Llamadas de pago desactivadas.")
    sid,token,sender=_credentials("voice")
    with LOCK:
        state=_load()
        owner=_verified(state)
        target=_check_destination(state,number)
        if target==owner:raise PhoneInvalid("Seleccioná un número diferente del tuyo.")
        _throttle(state,"voice",3)
    # Only E.164 digits can be inside the TwiML. Avoid arbitrary XML.
    twiml=('<Response><Dial callerId="'+escape_xml(sender)+'" answerOnBridge="true"'
            ' record="do-not-record" timeout="25">'
            '<Number>'+escape_xml(target)+'</Number></Dial></Response>')
    response=_post("api.twilio.com",f"/2010-04-01/Accounts/{sid}/Calls.json",
          {"To":owner,"From":sender,"Twiml":twiml,"Record":"false",
           "Timeout":"25","TimeLimit":"1800"},sid,token)
    call_sid=str(response.get("sid",""))
    if not re.fullmatch(r"CA[a-fA-F0-9]{32}",call_sid):
        raise PhoneUnavailable("Twilio no confirmó la creación de llamada.")
    return {"status":"queued_unverified","call_sid":call_sid,
            "owner_handset_masked":_mask(owner),
            "destination_masked":_mask(target),
            "call_completed":False,"browser_microphone_call":False,
            "mode":"callback_to_verified_handset","may_charge_two_call_legs":True,
            "recording_enabled":False}


def _video_host() -> str:
    host=os.getenv("SKY_VIDEO_CONFERENCE_HOST","meet.jit.si").strip().lower()
    allowed={h.strip().lower() for h in os.getenv("SKY_VIDEO_ALLOWED_HOSTS","meet.jit.si").split(",") if h.strip()}
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{3,155}",host) or host not in allowed:
        raise PhoneInvalid("El anfitrión de video no está autorizado.")
    if host.startswith(".") or ".." in host or host.endswith("."):
        raise PhoneInvalid("Anfitrión de video inválido.")
    return host


def meeting(*,approved:bool)->dict:
    if approved is not True:raise PhoneInvalid("Debés autorizar la videoconferencia.")
    _require()
    with LOCK:
        _verified(_load())
    host=_video_host()
    room="SKY-" + secrets.token_urlsafe(24).replace("_","").replace("-","")
    url="https://"+host+"/"+room
    return {"status":"invitation_ready_not_joined","meeting_url":url,
            "room":room,"host":host,"media_shares_with_external_provider":True,
            "invited_participants":0,"room_server_verified":False,
            "privacy":"Cualquiera con el enlace podría intentar entrar; usá lobby/autenticación cuando sea posible.",
            "native_cellular_video_call":False}


def capabilities()->dict:
    return {"sms":"Twilio REST API outbound only",
            "voice":"Twilio callback to verified owner's handset then target; not browser softphone",
            "video":"Jitsi iframe/WebRTC after explicit click",
            "phone_number":"E.164 global format, carrier-independent, Twilio coverage varies",
            "verification":"Twilio Verify SMS OTP",
            "blocked_numbers":"enforced in SKY, not system-wide",
            "inbound":"not implemented",
            "no_recording":True,
            "send_limits":{"sms_per_day":10,"calls_per_day":3,"verify_per_day":5},
            "user_consent_required":True,"owner_pin_required":True}
