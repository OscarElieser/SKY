"""Owner-only SKY Teléfono API. Never bypasses SENTINEL or asks for SIM control.

User phone is verified via Twilio Verify before messaging, calls and video.
No public inbound callbacks, no access to device call logs or native OS blocks.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .api import require_key
from .sentinel import exigir_pin
from neural_core import sky_phone as phone
from neural_core import sentinel_identidad as ident

router = APIRouter(prefix="/api/sky/phone",dependencies=[Depends(require_key)])


class VerifyStart(BaseModel):
    number: str=Field(min_length=8,max_length=22)
    approved: bool=False


class VerifyCheck(BaseModel):
    number: str=Field(min_length=8,max_length=22)
    code: str=Field(min_length=4,max_length=10)


class SMS(BaseModel):
    to: str=Field(min_length=8,max_length=22)
    message: str=Field(min_length=1,max_length=800)
    approved: bool=False
    recipient_consented: bool=False


class PSTNCall(BaseModel):
    to: str=Field(min_length=8,max_length=22)
    approved: bool=False
    recipient_consented: bool=False


class BlockRequest(BaseModel):
    number: str=Field(min_length=8,max_length=22)
    approved: bool=False


class Consent(BaseModel):
    approved: bool=False


def _owner_pin(request:Request, purpose:str):
    # Unlike general SKY SENTINEL, paid telephone actions require that the PIN
    # has actually been enrolled. It cannot quietly default to no PIN.
    if not ident.pin_configurado():
        raise HTTPException(403,"Configurá el PIN SKY SENTINEL antes de activar comunicaciones.")
    exigir_pin(request,purpose)


def _return(fn,*args,**kwargs):
    try:
        return fn(*args,**kwargs)
    except phone.PhoneInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except phone.PhoneUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc


@router.get("/capabilities")
def capabilities():
    return phone.capabilities()


@router.get("/status")
def status():
    return _return(phone.readiness)


@router.post("/verify/start")
def verify_start(body:VerifyStart,request:Request):
    if not body.approved:
        raise HTTPException(422,"Confirmá que autorizás recibir un código SMS.")
    _owner_pin(request,"verificar número propio por SMS (puede generar cargos)")
    return _return(phone.begin_verify,body.number,approved=True)


@router.post("/verify/check")
def verify_check(body:VerifyCheck,request:Request):
    _owner_pin(request,"validar el número del propietario")
    return _return(phone.finish_verify,body.number,body.code)


@router.post("/verify/revoke")
def verify_revoke(body:Consent,request:Request):
    if not body.approved:raise HTTPException(422,"Confirmá la revocación.")
    _owner_pin(request,"revocar número telefónico de SKY")
    return _return(phone.revoke_owner,approved=True)


@router.get("/blocked")
def blocked():
    return _return(phone.blocked_list)


@router.post("/blocked")
def block(body:BlockRequest,request:Request):
    if not body.approved:raise HTTPException(422,"Confirmá el bloqueo.")
    _owner_pin(request,"bloquear este número dentro de SKY")
    return _return(phone.set_block,body.number,blocked=True,approved=True)


@router.delete("/blocked/{block_id}")
def unblock(block_id:str,body:Consent,request:Request):
    if not body.approved:raise HTTPException(422,"Confirmá el desbloqueo.")
    _owner_pin(request,"desbloquear este número dentro de SKY")
    return _return(phone.unblock_by_id,block_id,approved=True)


@router.post("/sms")
def sms(body:SMS,request:Request):
    if not body.approved or not body.recipient_consented:
        raise HTTPException(422,"Confirmá el envío y el consentimiento del contacto.")
    _owner_pin(request,"enviar SMS real con posible costo")
    return _return(phone.send_sms,body.to,body.message,
                   approved=True,recipient_consented=True)


@router.post("/voice/callback")
def voice_callback(body:PSTNCall,request:Request):
    if not body.approved or not body.recipient_consented:
        raise HTTPException(422,"Confirmá la llamada y el consentimiento del contacto.")
    _owner_pin(request,"iniciar llamada telefónica real con posible costo")
    return _return(phone.call_bridge,body.to,
                   approved=True,recipient_consented=True)


@router.post("/video/meeting")
def video_meeting(body:Consent,request:Request):
    if not body.approved:raise HTTPException(422,"Autorizá expresamente la videoconferencia.")
    _owner_pin(request,"abrir una sala de videoconferencia de un proveedor externo")
    return _return(phone.meeting,approved=True)
