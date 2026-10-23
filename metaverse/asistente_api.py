"""SKY v12 — API del Asistente Personal (sólo el dueño, con su llave y 2FA si está activo).

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

import json

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
    modo: str = Field(default='chat', pattern='^(chat|voz)$')


class OrdenCasa(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


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


def _completar(resultado: dict, dispositivo: str, request: Request) -> dict:
    """Ejecuta lo automático (según la política del agente o SKY_HA_AUTO) y marca lo que pide confirmación."""
    if resultado['tipo'] == 'casa':
        orden = resultado['propuesta']
        resultado['requiere_confirmacion'] = orden['requiere_confirmacion']
        if not orden['requiere_confirmacion']:
            from neural_core import sky_home_assistant as casa
            try:
                resultado['ejecucion'] = casa.ejecutar(orden['service'], orden['entity_ids'], orden['data'])
            except (RuntimeError, ValueError) as exc:
                resultado['ejecucion'] = {'ok': False, 'error': str(exc)[:200]}
        return resultado
    if resultado['tipo'] != 'accion':
        return resultado
    propuesta = resultado['propuesta']
    resultado['requiere_confirmacion'] = True
    if propuesta['action'] in caps.ACCIONES_INTERFAZ:
        # Reproductor interno, ventanas holográficas y flujo de voz: los aplica la interfaz.
        resultado['requiere_confirmacion'] = False
        resultado['interfaz'] = True
        return resultado
    # ¿El dueño autorizó esta capacidad sin confirmación? Lo dice el propio agente.
    try:
        estado = _llamar(dispositivo, request, 'status', {})
    except HTTPException as exc:
        resultado['aviso'] = str(exc.detail)
        return resultado
    politica = {'enabled': estado.get('enabled', []), 'auto_confirm': estado.get('auto_confirm', [])}
    if not caps.accion_habilitada(propuesta['action'], politica, propuesta['params']):
        cap = caps.capacidad_para(propuesta['action'], propuesta['params'])
        resultado['aviso'] = (f'La capacidad "{cap}" está desactivada en tu equipo. Activala con: '
                              f'python agente_dispositivo.py --activar {cap}')
        return resultado
    if not caps.requiere_confirmacion(propuesta['action'], propuesta['params'], politica):
        resultado['requiere_confirmacion'] = False
        try:
            resultado['ejecucion'] = _llamar(dispositivo, request, propuesta['action'], propuesta['params'])
        except HTTPException as exc:
            resultado['ejecucion'] = {'ok': False, 'error': str(exc.detail)[:200]}
    return resultado


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _completar(resultado, body.dispositivo, request)


@router.post('/stream')
def mensaje_stream(body: Mensaje, request: Request):
    """Igual que /mensaje, pero cuando responde el modelo local envía el texto a medida que
    se genera (NDJSON: {"delta": "..."} … {"final": {...}}), para que SKY hable sin esperar."""
    from fastapi.responses import StreamingResponse
    from neural_core import sky_asistente_personal as asis

    def eventos():
        historial = [t.model_dump() for t in body.historial]
        def linea(obj):
            return json.dumps(obj, ensure_ascii=False) + '\n'
        texto = body.texto.strip()
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request)})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _completar(asis.resolver_especial(valor), body.dispositivo, request)})
                return
            elif evento == 'fin':
                yield linea({'final': {'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True}})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': {'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True}})
                else:
                    yield linea({'final': _completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request)})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.get('/voz')
def voz_pendientes():
    return {'pendientes': voz_inbox.read_inbox()}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}
