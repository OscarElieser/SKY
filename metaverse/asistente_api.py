"""SKY v11.1 — API del Asistente Personal (sólo el dueño, con su llave y 2FA si está activo).

    POST /api/asistente/mensaje    texto → respuesta de IA o propuesta de acción
                                   (si el dueño activó auto_confirm para esa capacidad
                                   en el agente, se ejecuta al instante y se informa)
    POST /api/asistente/ejecutar   confirmar y ejecutar una acción en el dispositivo
    GET  /api/asistente/dispositivo estado + capacidades activas del agente
    GET  /api/asistente/ayuda      ejemplos de órdenes y catálogo de capacidades
    GET  /api/asistente/voz        propuestas pendientes del modo manos libres
    DELETE /api/asistente/voz/{id} descartar una propuesta de voz

El agente (agente_dispositivo.py) vuelve a validar todo con la política local
del dueño: esta API no puede activar capacidades ni saltarse esa política.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .api import require_key
from neural_core import dispositivos, voz_inbox
from neural_core import sky_capacidades as caps
from neural_core.sky_asistente_personal import AYUDA, atender, token_agente_local, url_agente_local

router = APIRouter(prefix='/api/asistente', dependencies=[Depends(require_key)])

LOCAL = 'local'


class Turno(BaseModel):
    role: str = Field(pattern='^(user|assistant)$')
    content: str = Field(max_length=4000)


class Mensaje(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    historial: list[Turno] = Field(default_factory=list, max_length=24)
    proveedor: str = Field(default='auto', max_length=20)
    dispositivo: str = Field(default=LOCAL, max_length=80)


class Ejecucion(BaseModel):
    action: str = Field(min_length=2, max_length=40)
    params: dict = Field(default_factory=dict)
    dispositivo: str = Field(default=LOCAL, max_length=80)


_url_local = url_agente_local
_token_local = token_agente_local


def _destino(nombre: str, request: Request) -> tuple[str, str]:
    """URL y token del dispositivo. El equipo local usa su token en disco; los
    remotos (Tailscale) reciben el token por cabecera X-SKY-DEVICE-TOKEN y
    nunca se almacena en el servidor."""
    if nombre == LOCAL:
        token = _token_local()
        if not token:
            raise HTTPException(409, 'Iniciá el agente en este equipo: python agente_dispositivo.py')
        return _url_local(), token
    info = next((d for d in dispositivos.paired_devices() if d['name'] == nombre), None)
    if not info:
        raise HTTPException(404, 'Dispositivo no emparejado.')
    token = request.headers.get('X-SKY-DEVICE-TOKEN', '').strip()
    if len(token) < 32:
        raise HTTPException(400, 'Enviá el token del dispositivo en la cabecera X-SKY-DEVICE-TOKEN.')
    return info['url'], token


def _llamar(nombre: str, request: Request, action: str, params: dict):
    if action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    url, token = _destino(nombre, request)
    try:
        return dispositivos.call_device(url, token, action, params, timeout=12)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(502, str(exc)[:250])


@router.get('/ayuda')
def ayuda():
    return {
        'ejemplos': [{'tema': t, 'frases': f} for t, f in AYUDA],
        'capacidades': [{'id': c.id, 'nombre': c.nombre, 'descripcion': c.descripcion, 'riesgo': c.riesgo}
                        for c in caps.CAPACIDADES.values()],
        'perfiles': caps.PERFILES,
        'dispositivos': [{'name': LOCAL, 'url': _url_local()}] +
                        [{'name': d['name'], 'url': d['url']} for d in dispositivos.paired_devices()],
    }


@router.get('/dispositivo')
def estado_dispositivo(request: Request, dispositivo: str = LOCAL):
    return _llamar(dispositivo, request, 'status', {})


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor)
    if resultado['tipo'] != 'accion':
        return resultado
    propuesta = resultado['propuesta']
    resultado['requiere_confirmacion'] = True
    # ¿El dueño autorizó esta capacidad sin confirmación? Lo dice el propio agente.
    try:
        estado = _llamar(body.dispositivo, request, 'status', {})
    except HTTPException as exc:
        resultado['aviso'] = str(exc.detail)
        return resultado
    politica = {'enabled': estado.get('enabled', []), 'auto_confirm': estado.get('auto_confirm', [])}
    if not caps.accion_habilitada(propuesta['action'], politica, propuesta['params']):
        cap = 'apps_extra' if propuesta['action'] == 'launch_app' else caps.capacidad_de(propuesta['action'])
        resultado['aviso'] = (f'La capacidad "{cap}" está desactivada en tu equipo. Activala con: '
                              f'python agente_dispositivo.py --activar {cap}')
        return resultado
    if not caps.requiere_confirmacion(propuesta['action'], propuesta['params'], politica):
        resultado['requiere_confirmacion'] = False
        resultado['ejecucion'] = _llamar(body.dispositivo, request, propuesta['action'], propuesta['params'])
    return resultado


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    return _llamar(body.dispositivo, request, body.action, body.params)


@router.get('/voz')
def voz_pendientes():
    return {'pendientes': voz_inbox.read_inbox()}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}
