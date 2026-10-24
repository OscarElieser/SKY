"""Owner second factor: independent of the public community login."""
from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from .api import require_owner_key_only, require_key
from . import owner_mfa

router = APIRouter()


class SecondFactor(BaseModel):
    code: str = Field(min_length=6, max_length=6)


@router.get('/api/security/owner-mfa/status')
def status():
    return {'required': owner_mfa.required(), 'method': 'totp' if owner_mfa.required() else None,
            'setup': 'local_environment_only', 'expires_in_seconds': owner_mfa.LIFETIME}


@router.post('/api/security/owner-mfa/session', dependencies=[Depends(require_owner_key_only)])
def begin(body: SecondFactor, request: Request):
    try:
        token, lifetime = owner_mfa.open_session(body.code, request.client.host if request.client else 'unknown')
        return {'session': token, 'expires_in': lifetime, 'token_type': 'owner-second-factor'}
    except PermissionError as exc:
        raise HTTPException(429, str(exc), headers={'Retry-After': '300'}) from exc
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post('/api/security/owner-mfa/logout', dependencies=[Depends(require_key)])
def logout(session: str | None = Header(None, alias='X-SKY-SESSION')):
    owner_mfa.revoke(session)
    return {'revoked': True}


@router.get('/api/security/owner-mfa/verify', dependencies=[Depends(require_key)])
def verify_session():
    return {'authenticated':True,'second_factor':owner_mfa.required()}


# SKY Sentinel — access denial logs and owner-controlled emergency procedures.
from neural_core import sky_sentinel_guard as sentinel


class ShutdownConfirmation(BaseModel):
    confirmation_token: str = Field(min_length=32,max_length=100)
    phrase: str = Field(min_length=10,max_length=60)


def _host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get('/api/security/sentinel/status',dependencies=[Depends(require_key)])
def sentinel_status():
    return sentinel.status()


@router.post('/api/security/sentinel/shutdown/prepare',dependencies=[Depends(require_key)])
def sentinel_prepare_shutdown(request: Request):
    try:
        return sentinel.prepare_shutdown(_host(request))
    except PermissionError as exc:
        raise HTTPException(403,str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409,str(exc)) from exc


@router.post('/api/security/sentinel/shutdown/confirm',dependencies=[Depends(require_key)])
def sentinel_shutdown_confirm(body: ShutdownConfirmation,request: Request):
    try:
        return sentinel.shutdown_confirmed(_host(request),body.confirmation_token,body.phrase)
    except PermissionError as exc:
        raise HTTPException(403,str(exc)) from exc
    except (RuntimeError,OSError) as exc:
        raise HTTPException(409,str(exc)[:160]) from exc


@router.post('/api/security/sentinel/shutdown/abort',dependencies=[Depends(require_key)])
def sentinel_shutdown_abort(request: Request):
    try:
        return sentinel.abort_shutdown(_host(request))
    except PermissionError as exc:
        raise HTTPException(403,str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409,str(exc)) from exc
