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
