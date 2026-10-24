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
from neural_core import sky_subagents, sky_internal_roles, sky_supervisor
from neural_core.sky_approvals import approvals
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
    modo: str = Field(default='chat', pattern='^(chat|voz)

class OrdenCasa(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


class Ejecucion(BaseModel):
    approval_token: str = Field(default='', max_length=100)
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


def _emitir_aprobacion(tipo: str, payload: dict, request: Request) -> str:
    try:
        return approvals.issue(tipo, payload, request)
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(503, str(exc)[:180]) from exc


def _exigir_aprobacion(token: str, tipo: str, payload: dict, request: Request):
    if not approvals.consume(token, tipo, payload, request):
        raise HTTPException(403, 'La aprobación falta, caducó o no coincide con la operación mostrada.')


def _payload_casa(service: str, ids: list[str], data: dict) -> dict:
    return {'service': service, 'entity_ids': ids, 'data': data}


def _payload_correo(para: str, asunto: str, cuerpo: str, en_respuesta_a: str) -> dict:
    return {'para': para, 'asunto': asunto, 'cuerpo': cuerpo, 'en_respuesta_a': en_respuesta_a}


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
    if resultado['tipo'] == 'correo':
        b = resultado.get('borrador') or {}
        resultado['approval_token'] = _emitir_aprobacion(
            'correo', _payload_correo(b.get('para', ''), b.get('asunto', ''),
                                     b.get('cuerpo', ''), b.get('en_respuesta_a', '')), request)
        return resultado
    if resultado['tipo'] == 'casa':
        orden = resultado['propuesta']
        resultado['requiere_confirmacion'] = orden['requiere_confirmacion']
        if orden['requiere_confirmacion']:
            resultado['approval_token'] = _emitir_aprobacion(
                'casa', _payload_casa(orden['service'], orden['entity_ids'], orden.get('data', {})), request)
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
    if resultado['requiere_confirmacion']:
        resultado['approval_token'] = _emitir_aprobacion(
            'accion',
            {'action': propuesta['action'], 'params': propuesta['params'], 'dispositivo': dispositivo},
            request)
    return resultado


def _crear_subagente_si_pedido(texto: str) -> dict | None:
    cmd = sky_subagents.parse_create_command(texto)
    if not cmd:
        return None
    try:
        sub = sky_subagents.create(**cmd)
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from exc
    return {'tipo': 'respuesta', 'proveedor': 'sky-subagent-manager',
            'mensaje': (f'Creé el perfil «{sub["name"]}», desactivado y sin permisos nuevos. '
                        f'Especialidad: {sub["role"]}. Para delegarle tareas, '
                        'activá el subagente en Automatizaciones y aprobá cada flujo.'),
            'subagent': sub}


def _supervisar_si_pedido(body: Mensaje) -> dict | None:
    """An explicit SKY supervisor command auto-divides tasks but NEVER starts them."""
    import re
    expression = (
        r'^\s*(?:(?:oye|hey|ok)\s+)?sky[\s,;:!¡-]+'
        r'(?:coordina|coordin[aá]|organiza|organiz[aá]|delega|deleg[aá])\s+'
        r'(?P<task>.{8,3000})
    """La conversación siempre pertenece a SKY, no al motor o subagente interno."""
    if not isinstance(resultado, dict):
        return resultado
    respuesta = dict(resultado)
    respuesta['atendido_por'] = 'SKY'
    # Metadato de diagnóstico; NO representa ejecución automática del rol.
    respuesta['rol_interno_sugerido'] = sky_internal_roles.route_result(respuesta)
    return respuesta


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    creado = _crear_subagente_si_pedido(body.texto)
    if creado:
        return _centrar_en_sky(creado)
    supervision = _supervisar_si_pedido(body)
    if supervision:
        return _centrar_en_sky(supervision)
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _centrar_en_sky(_completar(resultado, body.dispositivo, request))


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
        creado = _crear_subagente_si_pedido(texto)
        if creado:
            yield linea({'final': _centrar_en_sky(creado)})
            return
        supervision = _supervisar_si_pedido(body)
        if supervision:
            yield linea({'final': _centrar_en_sky(supervision)})
            return
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _centrar_en_sky(_completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _centrar_en_sky(_completar(asis.resolver_especial(valor), body.dispositivo, request))})
                return
            elif evento == 'fin':
                yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})})
                else:
                    yield linea({'final': _centrar_en_sky(_completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    _exigir_aprobacion(body.approval_token, 'correo',
                      _payload_correo(body.para, body.asunto, body.cuerpo, body.en_respuesta_a), request)
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    if body.action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    if body.action != 'status':
        _exigir_aprobacion(body.approval_token, 'accion',
                          {'action': body.action, 'params': body.params, 'dispositivo': body.dispositivo},
                          request)
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    _exigir_aprobacion(body.approval_token, 'casa',
                       _payload_casa(body.service, body.entity_ids, body.data), request)
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


class CasaRapida(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


@router.post('/casa/preparar')
def preparar_casa_rapida(body: CasaRapida, request: Request):
    """El botón HUD prepara una orden de bajo riesgo; la ejecución exige token único."""
    from neural_core import sky_home_assistant as casa
    dominio, _, accion = body.service.partition('.')
    if (dominio not in ('light', 'switch', 'fan', 'scene')
            or accion not in casa.SERVICIOS_PERMITIDOS.get(dominio, set())
            or any(not entity.startswith(dominio + '.') for entity in body.entity_ids)
            or body.data):
        raise HTTPException(403, 'La operación requiere una propuesta explícita.')
    return {'approval_token': _emitir_aprobacion(
        'casa', _payload_casa(body.service, body.entity_ids, {}), request)}


@router.get('/verificar/{command_id}')
def verificar_accion(command_id: str, request: Request, dispositivo: str = LOCAL):
    """Consulta el estado del agente; sólo VERIFIED acredita una acción comprobada."""
    try:
        url, token = _destino(dispositivo, request)
        return dispositivos.verify_device_action(url, token, command_id, timeout=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200]) from exc


@router.get('/voz')
def voz_pendientes(request: Request):
    pending = []
    for entry in voz_inbox.read_inbox()[-8:]:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        action = item.get('action')
        if action not in caps.ACCION_A_CAPACIDAD:
            continue
        item['approval_token'] = _emitir_aprobacion(
            'accion', {'action': action, 'params': item.get('params', {}), 'dispositivo': LOCAL}, request)
        pending.append(item)
    return {'pendientes': pending}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}
)
    source_text: str = Field(default='', max_length=12000)
    document_format: str = Field(default='auto', max_length=12)


class OrdenCasa(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


class Ejecucion(BaseModel):
    approval_token: str = Field(default='', max_length=100)
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


def _emitir_aprobacion(tipo: str, payload: dict, request: Request) -> str:
    try:
        return approvals.issue(tipo, payload, request)
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(503, str(exc)[:180]) from exc


def _exigir_aprobacion(token: str, tipo: str, payload: dict, request: Request):
    if not approvals.consume(token, tipo, payload, request):
        raise HTTPException(403, 'La aprobación falta, caducó o no coincide con la operación mostrada.')


def _payload_casa(service: str, ids: list[str], data: dict) -> dict:
    return {'service': service, 'entity_ids': ids, 'data': data}


def _payload_correo(para: str, asunto: str, cuerpo: str, en_respuesta_a: str) -> dict:
    return {'para': para, 'asunto': asunto, 'cuerpo': cuerpo, 'en_respuesta_a': en_respuesta_a}


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
    if resultado['tipo'] == 'correo':
        b = resultado.get('borrador') or {}
        resultado['approval_token'] = _emitir_aprobacion(
            'correo', _payload_correo(b.get('para', ''), b.get('asunto', ''),
                                     b.get('cuerpo', ''), b.get('en_respuesta_a', '')), request)
        return resultado
    if resultado['tipo'] == 'casa':
        orden = resultado['propuesta']
        resultado['requiere_confirmacion'] = orden['requiere_confirmacion']
        if orden['requiere_confirmacion']:
            resultado['approval_token'] = _emitir_aprobacion(
                'casa', _payload_casa(orden['service'], orden['entity_ids'], orden.get('data', {})), request)
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
    if resultado['requiere_confirmacion']:
        resultado['approval_token'] = _emitir_aprobacion(
            'accion',
            {'action': propuesta['action'], 'params': propuesta['params'], 'dispositivo': dispositivo},
            request)
    return resultado


def _crear_subagente_si_pedido(texto: str) -> dict | None:
    cmd = sky_subagents.parse_create_command(texto)
    if not cmd:
        return None
    try:
        sub = sky_subagents.create(**cmd)
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from exc
    return {'tipo': 'respuesta', 'proveedor': 'sky-subagent-manager',
            'mensaje': (f'Creé el perfil «{sub["name"]}», desactivado y sin permisos nuevos. '
                        f'Especialidad: {sub["role"]}. Para delegarle tareas, '
                        'activá el subagente en Automatizaciones y aprobá cada flujo.'),
            'subagent': sub}


def _centrar_en_sky(resultado: dict) -> dict:
    """La conversación siempre pertenece a SKY, no al motor o subagente interno."""
    if not isinstance(resultado, dict):
        return resultado
    respuesta = dict(resultado)
    respuesta['atendido_por'] = 'SKY'
    # Metadato de diagnóstico; NO representa ejecución automática del rol.
    respuesta['rol_interno_sugerido'] = sky_internal_roles.route_result(respuesta)
    return respuesta


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    creado = _crear_subagente_si_pedido(body.texto)
    if creado:
        return _centrar_en_sky(creado)
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _centrar_en_sky(_completar(resultado, body.dispositivo, request))


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
        creado = _crear_subagente_si_pedido(texto)
        if creado:
            yield linea({'final': _centrar_en_sky(creado)})
            return
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _centrar_en_sky(_completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _centrar_en_sky(_completar(asis.resolver_especial(valor), body.dispositivo, request))})
                return
            elif evento == 'fin':
                yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})})
                else:
                    yield linea({'final': _centrar_en_sky(_completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    _exigir_aprobacion(body.approval_token, 'correo',
                      _payload_correo(body.para, body.asunto, body.cuerpo, body.en_respuesta_a), request)
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    if body.action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    if body.action != 'status':
        _exigir_aprobacion(body.approval_token, 'accion',
                          {'action': body.action, 'params': body.params, 'dispositivo': body.dispositivo},
                          request)
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    _exigir_aprobacion(body.approval_token, 'casa',
                       _payload_casa(body.service, body.entity_ids, body.data), request)
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


class CasaRapida(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


@router.post('/casa/preparar')
def preparar_casa_rapida(body: CasaRapida, request: Request):
    """El botón HUD prepara una orden de bajo riesgo; la ejecución exige token único."""
    from neural_core import sky_home_assistant as casa
    dominio, _, accion = body.service.partition('.')
    if (dominio not in ('light', 'switch', 'fan', 'scene')
            or accion not in casa.SERVICIOS_PERMITIDOS.get(dominio, set())
            or any(not entity.startswith(dominio + '.') for entity in body.entity_ids)
            or body.data):
        raise HTTPException(403, 'La operación requiere una propuesta explícita.')
    return {'approval_token': _emitir_aprobacion(
        'casa', _payload_casa(body.service, body.entity_ids, {}), request)}


@router.get('/verificar/{command_id}')
def verificar_accion(command_id: str, request: Request, dispositivo: str = LOCAL):
    """Consulta el estado del agente; sólo VERIFIED acredita una acción comprobada."""
    try:
        url, token = _destino(dispositivo, request)
        return dispositivos.verify_device_action(url, token, command_id, timeout=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200]) from exc


@router.get('/voz')
def voz_pendientes(request: Request):
    pending = []
    for entry in voz_inbox.read_inbox()[-8:]:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        action = item.get('action')
        if action not in caps.ACCION_A_CAPACIDAD:
            continue
        item['approval_token'] = _emitir_aprobacion(
            'accion', {'action': action, 'params': item.get('params', {}), 'dispositivo': LOCAL}, request)
        pending.append(item)
    return {'pendientes': pending}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}

    )
    match = re.match(expression, body.texto.strip(), re.IGNORECASE)
    if not match:
        return None
    task = match.group('task').strip()
    try:
        plan = sky_supervisor.prepare(
            task, source_text=body.source_text, document_format=body.document_format
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:220]) from exc
    if plan['status'] == 'needs_input':
        summary = "SKY preparó los roles, pero necesita: " + " | ".join(
            x['reason'] for x in plan['blockers']
        )
    else:
        summary = (f"SKY coordinó {len(plan['steps'])} etapas y asignó: "
                   f"{', '.join(plan['assigned_roles'])}. "
                   "El trabajo está en espera de tu aprobación en Automatizaciones. "
                   "No se ha ejecutado todavía.")
    return {'tipo': 'respuesta', 'mensaje': summary,
            'proveedor': 'sky-supervisor', 'supervisor': plan}


def _centrar_en_sky(resultado: dict) -> dict:
    """La conversación siempre pertenece a SKY, no al motor o subagente interno."""
    if not isinstance(resultado, dict):
        return resultado
    respuesta = dict(resultado)
    respuesta['atendido_por'] = 'SKY'
    # Metadato de diagnóstico; NO representa ejecución automática del rol.
    respuesta['rol_interno_sugerido'] = sky_internal_roles.route_result(respuesta)
    return respuesta


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    creado = _crear_subagente_si_pedido(body.texto)
    if creado:
        return _centrar_en_sky(creado)
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _centrar_en_sky(_completar(resultado, body.dispositivo, request))


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
        creado = _crear_subagente_si_pedido(texto)
        if creado:
            yield linea({'final': _centrar_en_sky(creado)})
            return
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _centrar_en_sky(_completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _centrar_en_sky(_completar(asis.resolver_especial(valor), body.dispositivo, request))})
                return
            elif evento == 'fin':
                yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})})
                else:
                    yield linea({'final': _centrar_en_sky(_completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    _exigir_aprobacion(body.approval_token, 'correo',
                      _payload_correo(body.para, body.asunto, body.cuerpo, body.en_respuesta_a), request)
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    if body.action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    if body.action != 'status':
        _exigir_aprobacion(body.approval_token, 'accion',
                          {'action': body.action, 'params': body.params, 'dispositivo': body.dispositivo},
                          request)
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    _exigir_aprobacion(body.approval_token, 'casa',
                       _payload_casa(body.service, body.entity_ids, body.data), request)
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


class CasaRapida(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


@router.post('/casa/preparar')
def preparar_casa_rapida(body: CasaRapida, request: Request):
    """El botón HUD prepara una orden de bajo riesgo; la ejecución exige token único."""
    from neural_core import sky_home_assistant as casa
    dominio, _, accion = body.service.partition('.')
    if (dominio not in ('light', 'switch', 'fan', 'scene')
            or accion not in casa.SERVICIOS_PERMITIDOS.get(dominio, set())
            or any(not entity.startswith(dominio + '.') for entity in body.entity_ids)
            or body.data):
        raise HTTPException(403, 'La operación requiere una propuesta explícita.')
    return {'approval_token': _emitir_aprobacion(
        'casa', _payload_casa(body.service, body.entity_ids, {}), request)}


@router.get('/verificar/{command_id}')
def verificar_accion(command_id: str, request: Request, dispositivo: str = LOCAL):
    """Consulta el estado del agente; sólo VERIFIED acredita una acción comprobada."""
    try:
        url, token = _destino(dispositivo, request)
        return dispositivos.verify_device_action(url, token, command_id, timeout=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200]) from exc


@router.get('/voz')
def voz_pendientes(request: Request):
    pending = []
    for entry in voz_inbox.read_inbox()[-8:]:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        action = item.get('action')
        if action not in caps.ACCION_A_CAPACIDAD:
            continue
        item['approval_token'] = _emitir_aprobacion(
            'accion', {'action': action, 'params': item.get('params', {}), 'dispositivo': LOCAL}, request)
        pending.append(item)
    return {'pendientes': pending}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}
)
    source_text: str = Field(default='', max_length=12000)
    document_format: str = Field(default='auto', max_length=12)


class OrdenCasa(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


class Ejecucion(BaseModel):
    approval_token: str = Field(default='', max_length=100)
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


def _emitir_aprobacion(tipo: str, payload: dict, request: Request) -> str:
    try:
        return approvals.issue(tipo, payload, request)
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(503, str(exc)[:180]) from exc


def _exigir_aprobacion(token: str, tipo: str, payload: dict, request: Request):
    if not approvals.consume(token, tipo, payload, request):
        raise HTTPException(403, 'La aprobación falta, caducó o no coincide con la operación mostrada.')


def _payload_casa(service: str, ids: list[str], data: dict) -> dict:
    return {'service': service, 'entity_ids': ids, 'data': data}


def _payload_correo(para: str, asunto: str, cuerpo: str, en_respuesta_a: str) -> dict:
    return {'para': para, 'asunto': asunto, 'cuerpo': cuerpo, 'en_respuesta_a': en_respuesta_a}


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
    if resultado['tipo'] == 'correo':
        b = resultado.get('borrador') or {}
        resultado['approval_token'] = _emitir_aprobacion(
            'correo', _payload_correo(b.get('para', ''), b.get('asunto', ''),
                                     b.get('cuerpo', ''), b.get('en_respuesta_a', '')), request)
        return resultado
    if resultado['tipo'] == 'casa':
        orden = resultado['propuesta']
        resultado['requiere_confirmacion'] = orden['requiere_confirmacion']
        if orden['requiere_confirmacion']:
            resultado['approval_token'] = _emitir_aprobacion(
                'casa', _payload_casa(orden['service'], orden['entity_ids'], orden.get('data', {})), request)
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
    if resultado['requiere_confirmacion']:
        resultado['approval_token'] = _emitir_aprobacion(
            'accion',
            {'action': propuesta['action'], 'params': propuesta['params'], 'dispositivo': dispositivo},
            request)
    return resultado


def _crear_subagente_si_pedido(texto: str) -> dict | None:
    cmd = sky_subagents.parse_create_command(texto)
    if not cmd:
        return None
    try:
        sub = sky_subagents.create(**cmd)
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from exc
    return {'tipo': 'respuesta', 'proveedor': 'sky-subagent-manager',
            'mensaje': (f'Creé el perfil «{sub["name"]}», desactivado y sin permisos nuevos. '
                        f'Especialidad: {sub["role"]}. Para delegarle tareas, '
                        'activá el subagente en Automatizaciones y aprobá cada flujo.'),
            'subagent': sub}


def _centrar_en_sky(resultado: dict) -> dict:
    """La conversación siempre pertenece a SKY, no al motor o subagente interno."""
    if not isinstance(resultado, dict):
        return resultado
    respuesta = dict(resultado)
    respuesta['atendido_por'] = 'SKY'
    # Metadato de diagnóstico; NO representa ejecución automática del rol.
    respuesta['rol_interno_sugerido'] = sky_internal_roles.route_result(respuesta)
    return respuesta


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    creado = _crear_subagente_si_pedido(body.texto)
    if creado:
        return _centrar_en_sky(creado)
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _centrar_en_sky(_completar(resultado, body.dispositivo, request))


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
        creado = _crear_subagente_si_pedido(texto)
        if creado:
            yield linea({'final': _centrar_en_sky(creado)})
            return
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _centrar_en_sky(_completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _centrar_en_sky(_completar(asis.resolver_especial(valor), body.dispositivo, request))})
                return
            elif evento == 'fin':
                yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})})
                else:
                    yield linea({'final': _centrar_en_sky(_completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    _exigir_aprobacion(body.approval_token, 'correo',
                      _payload_correo(body.para, body.asunto, body.cuerpo, body.en_respuesta_a), request)
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    if body.action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    if body.action != 'status':
        _exigir_aprobacion(body.approval_token, 'accion',
                          {'action': body.action, 'params': body.params, 'dispositivo': body.dispositivo},
                          request)
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    _exigir_aprobacion(body.approval_token, 'casa',
                       _payload_casa(body.service, body.entity_ids, body.data), request)
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


class CasaRapida(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


@router.post('/casa/preparar')
def preparar_casa_rapida(body: CasaRapida, request: Request):
    """El botón HUD prepara una orden de bajo riesgo; la ejecución exige token único."""
    from neural_core import sky_home_assistant as casa
    dominio, _, accion = body.service.partition('.')
    if (dominio not in ('light', 'switch', 'fan', 'scene')
            or accion not in casa.SERVICIOS_PERMITIDOS.get(dominio, set())
            or any(not entity.startswith(dominio + '.') for entity in body.entity_ids)
            or body.data):
        raise HTTPException(403, 'La operación requiere una propuesta explícita.')
    return {'approval_token': _emitir_aprobacion(
        'casa', _payload_casa(body.service, body.entity_ids, {}), request)}


@router.get('/verificar/{command_id}')
def verificar_accion(command_id: str, request: Request, dispositivo: str = LOCAL):
    """Consulta el estado del agente; sólo VERIFIED acredita una acción comprobada."""
    try:
        url, token = _destino(dispositivo, request)
        return dispositivos.verify_device_action(url, token, command_id, timeout=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200]) from exc


@router.get('/voz')
def voz_pendientes(request: Request):
    pending = []
    for entry in voz_inbox.read_inbox()[-8:]:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        action = item.get('action')
        if action not in caps.ACCION_A_CAPACIDAD:
            continue
        item['approval_token'] = _emitir_aprobacion(
            'accion', {'action': action, 'params': item.get('params', {}), 'dispositivo': LOCAL}, request)
        pending.append(item)
    return {'pendientes': pending}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}
)
    source_text: str = Field(default='', max_length=12000)
    document_format: str = Field(default='auto', max_length=12)


class OrdenCasa(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


class Ejecucion(BaseModel):
    approval_token: str = Field(default='', max_length=100)
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


def _emitir_aprobacion(tipo: str, payload: dict, request: Request) -> str:
    try:
        return approvals.issue(tipo, payload, request)
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(503, str(exc)[:180]) from exc


def _exigir_aprobacion(token: str, tipo: str, payload: dict, request: Request):
    if not approvals.consume(token, tipo, payload, request):
        raise HTTPException(403, 'La aprobación falta, caducó o no coincide con la operación mostrada.')


def _payload_casa(service: str, ids: list[str], data: dict) -> dict:
    return {'service': service, 'entity_ids': ids, 'data': data}


def _payload_correo(para: str, asunto: str, cuerpo: str, en_respuesta_a: str) -> dict:
    return {'para': para, 'asunto': asunto, 'cuerpo': cuerpo, 'en_respuesta_a': en_respuesta_a}


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
    if resultado['tipo'] == 'correo':
        b = resultado.get('borrador') or {}
        resultado['approval_token'] = _emitir_aprobacion(
            'correo', _payload_correo(b.get('para', ''), b.get('asunto', ''),
                                     b.get('cuerpo', ''), b.get('en_respuesta_a', '')), request)
        return resultado
    if resultado['tipo'] == 'casa':
        orden = resultado['propuesta']
        resultado['requiere_confirmacion'] = orden['requiere_confirmacion']
        if orden['requiere_confirmacion']:
            resultado['approval_token'] = _emitir_aprobacion(
                'casa', _payload_casa(orden['service'], orden['entity_ids'], orden.get('data', {})), request)
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
    if resultado['requiere_confirmacion']:
        resultado['approval_token'] = _emitir_aprobacion(
            'accion',
            {'action': propuesta['action'], 'params': propuesta['params'], 'dispositivo': dispositivo},
            request)
    return resultado


def _crear_subagente_si_pedido(texto: str) -> dict | None:
    cmd = sky_subagents.parse_create_command(texto)
    if not cmd:
        return None
    try:
        sub = sky_subagents.create(**cmd)
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from exc
    return {'tipo': 'respuesta', 'proveedor': 'sky-subagent-manager',
            'mensaje': (f'Creé el perfil «{sub["name"]}», desactivado y sin permisos nuevos. '
                        f'Especialidad: {sub["role"]}. Para delegarle tareas, '
                        'activá el subagente en Automatizaciones y aprobá cada flujo.'),
            'subagent': sub}


def _supervisar_si_pedido(body: Mensaje) -> dict | None:
    """An explicit SKY supervisor command auto-divides tasks but NEVER starts them."""
    import re
    expression = (
        r'^\s*(?:(?:oye|hey|ok)\s+)?sky[\s,;:!¡-]+'
        r'(?:coordina|coordin[aá]|organiza|organiz[aá]|delega|deleg[aá])\s+'
        r'(?P<task>.{8,3000})
    """La conversación siempre pertenece a SKY, no al motor o subagente interno."""
    if not isinstance(resultado, dict):
        return resultado
    respuesta = dict(resultado)
    respuesta['atendido_por'] = 'SKY'
    # Metadato de diagnóstico; NO representa ejecución automática del rol.
    respuesta['rol_interno_sugerido'] = sky_internal_roles.route_result(respuesta)
    return respuesta


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    creado = _crear_subagente_si_pedido(body.texto)
    if creado:
        return _centrar_en_sky(creado)
    supervision = _supervisar_si_pedido(body)
    if supervision:
        return _centrar_en_sky(supervision)
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _centrar_en_sky(_completar(resultado, body.dispositivo, request))


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
        creado = _crear_subagente_si_pedido(texto)
        if creado:
            yield linea({'final': _centrar_en_sky(creado)})
            return
        supervision = _supervisar_si_pedido(body)
        if supervision:
            yield linea({'final': _centrar_en_sky(supervision)})
            return
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _centrar_en_sky(_completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _centrar_en_sky(_completar(asis.resolver_especial(valor), body.dispositivo, request))})
                return
            elif evento == 'fin':
                yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})})
                else:
                    yield linea({'final': _centrar_en_sky(_completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    _exigir_aprobacion(body.approval_token, 'correo',
                      _payload_correo(body.para, body.asunto, body.cuerpo, body.en_respuesta_a), request)
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    if body.action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    if body.action != 'status':
        _exigir_aprobacion(body.approval_token, 'accion',
                          {'action': body.action, 'params': body.params, 'dispositivo': body.dispositivo},
                          request)
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    _exigir_aprobacion(body.approval_token, 'casa',
                       _payload_casa(body.service, body.entity_ids, body.data), request)
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


class CasaRapida(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


@router.post('/casa/preparar')
def preparar_casa_rapida(body: CasaRapida, request: Request):
    """El botón HUD prepara una orden de bajo riesgo; la ejecución exige token único."""
    from neural_core import sky_home_assistant as casa
    dominio, _, accion = body.service.partition('.')
    if (dominio not in ('light', 'switch', 'fan', 'scene')
            or accion not in casa.SERVICIOS_PERMITIDOS.get(dominio, set())
            or any(not entity.startswith(dominio + '.') for entity in body.entity_ids)
            or body.data):
        raise HTTPException(403, 'La operación requiere una propuesta explícita.')
    return {'approval_token': _emitir_aprobacion(
        'casa', _payload_casa(body.service, body.entity_ids, {}), request)}


@router.get('/verificar/{command_id}')
def verificar_accion(command_id: str, request: Request, dispositivo: str = LOCAL):
    """Consulta el estado del agente; sólo VERIFIED acredita una acción comprobada."""
    try:
        url, token = _destino(dispositivo, request)
        return dispositivos.verify_device_action(url, token, command_id, timeout=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200]) from exc


@router.get('/voz')
def voz_pendientes(request: Request):
    pending = []
    for entry in voz_inbox.read_inbox()[-8:]:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        action = item.get('action')
        if action not in caps.ACCION_A_CAPACIDAD:
            continue
        item['approval_token'] = _emitir_aprobacion(
            'accion', {'action': action, 'params': item.get('params', {}), 'dispositivo': LOCAL}, request)
        pending.append(item)
    return {'pendientes': pending}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}
)
    source_text: str = Field(default='', max_length=12000)
    document_format: str = Field(default='auto', max_length=12)


class OrdenCasa(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


class Ejecucion(BaseModel):
    approval_token: str = Field(default='', max_length=100)
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


def _emitir_aprobacion(tipo: str, payload: dict, request: Request) -> str:
    try:
        return approvals.issue(tipo, payload, request)
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(503, str(exc)[:180]) from exc


def _exigir_aprobacion(token: str, tipo: str, payload: dict, request: Request):
    if not approvals.consume(token, tipo, payload, request):
        raise HTTPException(403, 'La aprobación falta, caducó o no coincide con la operación mostrada.')


def _payload_casa(service: str, ids: list[str], data: dict) -> dict:
    return {'service': service, 'entity_ids': ids, 'data': data}


def _payload_correo(para: str, asunto: str, cuerpo: str, en_respuesta_a: str) -> dict:
    return {'para': para, 'asunto': asunto, 'cuerpo': cuerpo, 'en_respuesta_a': en_respuesta_a}


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
    if resultado['tipo'] == 'correo':
        b = resultado.get('borrador') or {}
        resultado['approval_token'] = _emitir_aprobacion(
            'correo', _payload_correo(b.get('para', ''), b.get('asunto', ''),
                                     b.get('cuerpo', ''), b.get('en_respuesta_a', '')), request)
        return resultado
    if resultado['tipo'] == 'casa':
        orden = resultado['propuesta']
        resultado['requiere_confirmacion'] = orden['requiere_confirmacion']
        if orden['requiere_confirmacion']:
            resultado['approval_token'] = _emitir_aprobacion(
                'casa', _payload_casa(orden['service'], orden['entity_ids'], orden.get('data', {})), request)
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
    if resultado['requiere_confirmacion']:
        resultado['approval_token'] = _emitir_aprobacion(
            'accion',
            {'action': propuesta['action'], 'params': propuesta['params'], 'dispositivo': dispositivo},
            request)
    return resultado


def _crear_subagente_si_pedido(texto: str) -> dict | None:
    cmd = sky_subagents.parse_create_command(texto)
    if not cmd:
        return None
    try:
        sub = sky_subagents.create(**cmd)
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from exc
    return {'tipo': 'respuesta', 'proveedor': 'sky-subagent-manager',
            'mensaje': (f'Creé el perfil «{sub["name"]}», desactivado y sin permisos nuevos. '
                        f'Especialidad: {sub["role"]}. Para delegarle tareas, '
                        'activá el subagente en Automatizaciones y aprobá cada flujo.'),
            'subagent': sub}


def _centrar_en_sky(resultado: dict) -> dict:
    """La conversación siempre pertenece a SKY, no al motor o subagente interno."""
    if not isinstance(resultado, dict):
        return resultado
    respuesta = dict(resultado)
    respuesta['atendido_por'] = 'SKY'
    # Metadato de diagnóstico; NO representa ejecución automática del rol.
    respuesta['rol_interno_sugerido'] = sky_internal_roles.route_result(respuesta)
    return respuesta


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    creado = _crear_subagente_si_pedido(body.texto)
    if creado:
        return _centrar_en_sky(creado)
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _centrar_en_sky(_completar(resultado, body.dispositivo, request))


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
        creado = _crear_subagente_si_pedido(texto)
        if creado:
            yield linea({'final': _centrar_en_sky(creado)})
            return
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _centrar_en_sky(_completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _centrar_en_sky(_completar(asis.resolver_especial(valor), body.dispositivo, request))})
                return
            elif evento == 'fin':
                yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})})
                else:
                    yield linea({'final': _centrar_en_sky(_completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    _exigir_aprobacion(body.approval_token, 'correo',
                      _payload_correo(body.para, body.asunto, body.cuerpo, body.en_respuesta_a), request)
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    if body.action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    if body.action != 'status':
        _exigir_aprobacion(body.approval_token, 'accion',
                          {'action': body.action, 'params': body.params, 'dispositivo': body.dispositivo},
                          request)
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    _exigir_aprobacion(body.approval_token, 'casa',
                       _payload_casa(body.service, body.entity_ids, body.data), request)
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


class CasaRapida(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


@router.post('/casa/preparar')
def preparar_casa_rapida(body: CasaRapida, request: Request):
    """El botón HUD prepara una orden de bajo riesgo; la ejecución exige token único."""
    from neural_core import sky_home_assistant as casa
    dominio, _, accion = body.service.partition('.')
    if (dominio not in ('light', 'switch', 'fan', 'scene')
            or accion not in casa.SERVICIOS_PERMITIDOS.get(dominio, set())
            or any(not entity.startswith(dominio + '.') for entity in body.entity_ids)
            or body.data):
        raise HTTPException(403, 'La operación requiere una propuesta explícita.')
    return {'approval_token': _emitir_aprobacion(
        'casa', _payload_casa(body.service, body.entity_ids, {}), request)}


@router.get('/verificar/{command_id}')
def verificar_accion(command_id: str, request: Request, dispositivo: str = LOCAL):
    """Consulta el estado del agente; sólo VERIFIED acredita una acción comprobada."""
    try:
        url, token = _destino(dispositivo, request)
        return dispositivos.verify_device_action(url, token, command_id, timeout=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200]) from exc


@router.get('/voz')
def voz_pendientes(request: Request):
    pending = []
    for entry in voz_inbox.read_inbox()[-8:]:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        action = item.get('action')
        if action not in caps.ACCION_A_CAPACIDAD:
            continue
        item['approval_token'] = _emitir_aprobacion(
            'accion', {'action': action, 'params': item.get('params', {}), 'dispositivo': LOCAL}, request)
        pending.append(item)
    return {'pendientes': pending}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}

    )
    match = re.match(expression, body.texto.strip(), re.IGNORECASE)
    if not match:
        return None
    task = match.group('task').strip()
    try:
        plan = sky_supervisor.prepare(
            task, source_text=body.source_text, document_format=body.document_format
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:220]) from exc
    if plan['status'] == 'needs_input':
        summary = "SKY preparó los roles, pero necesita: " + " | ".join(
            x['reason'] for x in plan['blockers']
        )
    else:
        summary = (f"SKY coordinó {len(plan['steps'])} etapas y asignó: "
                   f"{', '.join(plan['assigned_roles'])}. "
                   "El trabajo está en espera de tu aprobación en Automatizaciones. "
                   "No se ha ejecutado todavía.")
    return {'tipo': 'respuesta', 'mensaje': summary,
            'proveedor': 'sky-supervisor', 'supervisor': plan}


def _centrar_en_sky(resultado: dict) -> dict:
    """La conversación siempre pertenece a SKY, no al motor o subagente interno."""
    if not isinstance(resultado, dict):
        return resultado
    respuesta = dict(resultado)
    respuesta['atendido_por'] = 'SKY'
    # Metadato de diagnóstico; NO representa ejecución automática del rol.
    respuesta['rol_interno_sugerido'] = sky_internal_roles.route_result(respuesta)
    return respuesta


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    creado = _crear_subagente_si_pedido(body.texto)
    if creado:
        return _centrar_en_sky(creado)
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _centrar_en_sky(_completar(resultado, body.dispositivo, request))


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
        creado = _crear_subagente_si_pedido(texto)
        if creado:
            yield linea({'final': _centrar_en_sky(creado)})
            return
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _centrar_en_sky(_completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _centrar_en_sky(_completar(asis.resolver_especial(valor), body.dispositivo, request))})
                return
            elif evento == 'fin':
                yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})})
                else:
                    yield linea({'final': _centrar_en_sky(_completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    _exigir_aprobacion(body.approval_token, 'correo',
                      _payload_correo(body.para, body.asunto, body.cuerpo, body.en_respuesta_a), request)
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    if body.action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    if body.action != 'status':
        _exigir_aprobacion(body.approval_token, 'accion',
                          {'action': body.action, 'params': body.params, 'dispositivo': body.dispositivo},
                          request)
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    _exigir_aprobacion(body.approval_token, 'casa',
                       _payload_casa(body.service, body.entity_ids, body.data), request)
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


class CasaRapida(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


@router.post('/casa/preparar')
def preparar_casa_rapida(body: CasaRapida, request: Request):
    """El botón HUD prepara una orden de bajo riesgo; la ejecución exige token único."""
    from neural_core import sky_home_assistant as casa
    dominio, _, accion = body.service.partition('.')
    if (dominio not in ('light', 'switch', 'fan', 'scene')
            or accion not in casa.SERVICIOS_PERMITIDOS.get(dominio, set())
            or any(not entity.startswith(dominio + '.') for entity in body.entity_ids)
            or body.data):
        raise HTTPException(403, 'La operación requiere una propuesta explícita.')
    return {'approval_token': _emitir_aprobacion(
        'casa', _payload_casa(body.service, body.entity_ids, {}), request)}


@router.get('/verificar/{command_id}')
def verificar_accion(command_id: str, request: Request, dispositivo: str = LOCAL):
    """Consulta el estado del agente; sólo VERIFIED acredita una acción comprobada."""
    try:
        url, token = _destino(dispositivo, request)
        return dispositivos.verify_device_action(url, token, command_id, timeout=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200]) from exc


@router.get('/voz')
def voz_pendientes(request: Request):
    pending = []
    for entry in voz_inbox.read_inbox()[-8:]:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        action = item.get('action')
        if action not in caps.ACCION_A_CAPACIDAD:
            continue
        item['approval_token'] = _emitir_aprobacion(
            'accion', {'action': action, 'params': item.get('params', {}), 'dispositivo': LOCAL}, request)
        pending.append(item)
    return {'pendientes': pending}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}
)
    source_text: str = Field(default='', max_length=12000)
    document_format: str = Field(default='auto', max_length=12)


class OrdenCasa(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


class Ejecucion(BaseModel):
    approval_token: str = Field(default='', max_length=100)
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


def _emitir_aprobacion(tipo: str, payload: dict, request: Request) -> str:
    try:
        return approvals.issue(tipo, payload, request)
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(503, str(exc)[:180]) from exc


def _exigir_aprobacion(token: str, tipo: str, payload: dict, request: Request):
    if not approvals.consume(token, tipo, payload, request):
        raise HTTPException(403, 'La aprobación falta, caducó o no coincide con la operación mostrada.')


def _payload_casa(service: str, ids: list[str], data: dict) -> dict:
    return {'service': service, 'entity_ids': ids, 'data': data}


def _payload_correo(para: str, asunto: str, cuerpo: str, en_respuesta_a: str) -> dict:
    return {'para': para, 'asunto': asunto, 'cuerpo': cuerpo, 'en_respuesta_a': en_respuesta_a}


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
    if resultado['tipo'] == 'correo':
        b = resultado.get('borrador') or {}
        resultado['approval_token'] = _emitir_aprobacion(
            'correo', _payload_correo(b.get('para', ''), b.get('asunto', ''),
                                     b.get('cuerpo', ''), b.get('en_respuesta_a', '')), request)
        return resultado
    if resultado['tipo'] == 'casa':
        orden = resultado['propuesta']
        resultado['requiere_confirmacion'] = orden['requiere_confirmacion']
        if orden['requiere_confirmacion']:
            resultado['approval_token'] = _emitir_aprobacion(
                'casa', _payload_casa(orden['service'], orden['entity_ids'], orden.get('data', {})), request)
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
    if resultado['requiere_confirmacion']:
        resultado['approval_token'] = _emitir_aprobacion(
            'accion',
            {'action': propuesta['action'], 'params': propuesta['params'], 'dispositivo': dispositivo},
            request)
    return resultado


def _crear_subagente_si_pedido(texto: str) -> dict | None:
    cmd = sky_subagents.parse_create_command(texto)
    if not cmd:
        return None
    try:
        sub = sky_subagents.create(**cmd)
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from exc
    return {'tipo': 'respuesta', 'proveedor': 'sky-subagent-manager',
            'mensaje': (f'Creé el perfil «{sub["name"]}», desactivado y sin permisos nuevos. '
                        f'Especialidad: {sub["role"]}. Para delegarle tareas, '
                        'activá el subagente en Automatizaciones y aprobá cada flujo.'),
            'subagent': sub}


def _centrar_en_sky(resultado: dict) -> dict:
    """La conversación siempre pertenece a SKY, no al motor o subagente interno."""
    if not isinstance(resultado, dict):
        return resultado
    respuesta = dict(resultado)
    respuesta['atendido_por'] = 'SKY'
    # Metadato de diagnóstico; NO representa ejecución automática del rol.
    respuesta['rol_interno_sugerido'] = sky_internal_roles.route_result(respuesta)
    return respuesta


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    creado = _crear_subagente_si_pedido(body.texto)
    if creado:
        return _centrar_en_sky(creado)
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return _centrar_en_sky(_completar(resultado, body.dispositivo, request))


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
        creado = _crear_subagente_si_pedido(texto)
        if creado:
            yield linea({'final': _centrar_en_sky(creado)})
            return
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield linea({'final': _centrar_en_sky(_completar(r or asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                yield linea({'final': _centrar_en_sky(_completar(asis.resolver_especial(valor), body.dispositivo, request))})
                return
            elif evento == 'fin':
                yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})})
                return
            elif evento == 'error':
                if completo:
                    yield linea({'final': _centrar_en_sky({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})})
                else:
                    yield linea({'final': _centrar_en_sky(_completar(asis.atender(texto, historial, body.proveedor, body.modo), body.dispositivo, request))})
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    approval_token: str = Field(default='', max_length=100)
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from neural_core import sky_correo
    _exigir_aprobacion(body.approval_token, 'correo',
                      _payload_correo(body.para, body.asunto, body.cuerpo, body.en_respuesta_a), request)
    try:
        return sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel."""
    if body.action not in caps.ACCION_A_CAPACIDAD:
        raise HTTPException(400, 'Acción no permitida.')
    if body.action != 'status':
        _exigir_aprobacion(body.approval_token, 'accion',
                          {'action': body.action, 'params': body.params, 'dispositivo': body.dispositivo},
                          request)
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    return _llamar(body.dispositivo, request, body.action, params)


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    from neural_core import sky_home_assistant as casa
    _exigir_aprobacion(body.approval_token, 'casa',
                       _payload_casa(body.service, body.entity_ids, body.data), request)
    try:
        return casa.ejecutar(body.service, body.entity_ids, body.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


class CasaRapida(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)


@router.post('/casa/preparar')
def preparar_casa_rapida(body: CasaRapida, request: Request):
    """El botón HUD prepara una orden de bajo riesgo; la ejecución exige token único."""
    from neural_core import sky_home_assistant as casa
    dominio, _, accion = body.service.partition('.')
    if (dominio not in ('light', 'switch', 'fan', 'scene')
            or accion not in casa.SERVICIOS_PERMITIDOS.get(dominio, set())
            or any(not entity.startswith(dominio + '.') for entity in body.entity_ids)
            or body.data):
        raise HTTPException(403, 'La operación requiere una propuesta explícita.')
    return {'approval_token': _emitir_aprobacion(
        'casa', _payload_casa(body.service, body.entity_ids, {}), request)}


@router.get('/verificar/{command_id}')
def verificar_accion(command_id: str, request: Request, dispositivo: str = LOCAL):
    """Consulta el estado del agente; sólo VERIFIED acredita una acción comprobada."""
    try:
        url, token = _destino(dispositivo, request)
        return dispositivos.verify_device_action(url, token, command_id, timeout=5)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200]) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200]) from exc


@router.get('/voz')
def voz_pendientes(request: Request):
    pending = []
    for entry in voz_inbox.read_inbox()[-8:]:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        action = item.get('action')
        if action not in caps.ACCION_A_CAPACIDAD:
            continue
        item['approval_token'] = _emitir_aprobacion(
            'accion', {'action': action, 'params': item.get('params', {}), 'dispositivo': LOCAL}, request)
        pending.append(item)
    return {'pendientes': pending}


@router.delete('/voz/{entry_id}')
def voz_descartar(entry_id: str):
    if len(entry_id) > 64:
        raise HTTPException(400, 'Identificador inválido.')
    voz_inbox.dismiss_inbox(entry_id)
    return {'ok': True}
