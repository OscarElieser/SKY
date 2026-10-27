"""SKY SENTINEL — Security Center: estado de seguridad, PIN, bloqueo de la interfaz y controles del dueño."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api/sentinel')   # la protección la aplica sentinel_api_guard (todas privadas salvo desbloquear)

LOCALES = {'127.0.0.1', '::1', 'localhost', 'testclient'}


class Pin(BaseModel):
    pin: str = Field(min_length=6, max_length=12)


@router.post('/desbloquear')
def desbloquear(body: Pin, request: Request):
    """La interfaz bloqueada pide el PIN para recibir la llave del dueño. Sólo desde este equipo."""
    from neural_core import sentinel_identidad as ident
    from .api import api_token
    if (request.client.host if request.client else '') not in LOCALES:
        raise HTTPException(403, 'El desbloqueo con PIN sólo funciona en este equipo.')
    if not ident.pin_configurado():
        raise HTTPException(409, 'No hay PIN configurado.')
    # v12.6: la misma puerta que usa la voz; abre la sesión compartida de todos los procesos de SKY.
    r = ident.desbloquear_sesion(body.pin, 'hud')
    if not r['ok']:
        if r.get('espera_s'):
            raise HTTPException(429, r['mensaje'], headers={'Retry-After': str(r['espera_s'])})
        raise HTTPException(401, r['mensaje'] + (f" Te quedan {r['restantes']} intentos." if 'restantes' in r else ''))
    return {'key': api_token()}


@router.get('/sesion')
def sesion():
    """Pública: sólo dice si SKY está bloqueada (no revela nada más). La interfaz la usa para pedir el PIN."""
    from neural_core import sentinel_identidad as ident
    e = ident.estado_sesion()
    return {'pin': e['pin'], 'bloqueada': e['bloqueada'], 'espera_s': e.get('pin_bloqueado_s', 0)}


@router.post('/bloquear')
def bloquear():
    """Vuelve a bloquear SKY en todos sus procesos (voz, HUD, WhatsApp, agente) hasta el próximo PIN."""
    from neural_core import sentinel_identidad as ident
    if not ident.bloquear_sesion('pedido desde la interfaz', 'hud'):
        raise HTTPException(409, 'Para bloquear SKY primero configurá un PIN.')
    return {'bloqueada': True}


class CambioPin(BaseModel):
    nuevo: str = Field(min_length=6, max_length=12)
    actual: str = Field(default='', max_length=12)


@router.post('/pin')
def cambiar_pin(body: CambioPin):
    from neural_core import sentinel_identidad as ident
    try:
        ident.establecer_pin(body.nuevo, body.actual or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    return {'ok': True}


class SoloLocal(BaseModel):
    activo: bool


@router.post('/solo-local')
def solo_local(body: SoloLocal, request: Request):
    """Activarlo (más restrictivo) es inmediato; desactivarlo exige el PIN si está configurado."""
    from neural_core import sentinel_identidad as ident
    from .sentinel import exigir_pin
    if not body.activo:
        exigir_pin(request, 'permitir conexiones desde otros equipos')
    ident.cambiar_solo_local(body.activo)
    return {'solo_local': ident.solo_local()}


@router.post('/automatizaciones/pausar')
def pausar():
    from neural_core import sentinel_identidad as ident
    return {'pausadas': ident.pausar_automatizaciones()}


@router.get('/estado')
def estado():
    from neural_core import sentinel_estado
    return sentinel_estado.estado()
