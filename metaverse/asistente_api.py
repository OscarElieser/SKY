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
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .api import require_key
from neural_core import dispositivos, voz_inbox
from neural_core import sky_capacidades as caps
from neural_core.sky_asistente_personal import AYUDA, atender, token_agente_local, url_agente_local
from neural_core.sky_capacidades import DESCRIPCION_ACCIONES as DESCRIPCIONES

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
    lesson_id: str = Field(default='', max_length=80)
    source_text: str = Field(default='', max_length=12000)


class OrdenCasa(BaseModel):
    service: str = Field(min_length=3, max_length=60)
    entity_ids: list[str] = Field(min_length=1, max_length=20)
    data: dict = Field(default_factory=dict)
    frase: str = Field(default='', max_length=120)


class Ejecucion(BaseModel):
    action: str = Field(min_length=2, max_length=40)
    params: dict = Field(default_factory=dict)
    dispositivo: str = Field(default=LOCAL, max_length=80)
    frase: str = Field(default='', max_length=120)   # v12.2: si viene del cerebro, SKY la aprende al salir bien


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


def _casa(service: str, entity_ids: list[str], data: dict) -> dict:
    """Ejecuta en Home Assistant y lo registra en los KPIs."""
    from neural_core import sky_home_assistant as casa, sky_metricas
    if caps.parada_activa():
        raise RuntimeError('SKY está en parada de emergencia.')
    inicio = time.perf_counter()
    try:
        res = casa.ejecutar(service, entity_ids, data)
    except (RuntimeError, ValueError) as exc:
        sky_metricas.registrar('casa', service, False, (time.perf_counter() - inicio) * 1000, detalle=str(exc))
        raise
    sky_metricas.registrar('casa', service, res.get('ok', True) is not False, (time.perf_counter() - inicio) * 1000)
    return res


def _aprender(frase: str, resultado: dict, ejecucion) -> None:
    """SKY aprende la frase como atajo sólo si la acción elegida por el cerebro salió bien."""
    if not frase:
        return
    from neural_core import sky_aprendizaje, sky_metricas
    ok, _ = sky_metricas.resultado_ok(ejecucion)
    if ok:
        try:
            if sky_aprendizaje.aprender_orden(frase, resultado):
                resultado['aprendido_ahora'] = True
        except Exception:
            pass


def _origen(resultado: dict) -> str:
    if resultado.get('aprendido'):
        return 'aprendido'
    if resultado.get('via') == 'cerebro' or resultado.get('aprender') or resultado.get('proveedor') == 'ollama':
        return 'cerebro'
    if resultado.get('tipo') == 'respuesta' and resultado.get('proveedor', '').split('-')[0] not in ('sky',):
        return 'ia'
    return 'reglas'


def _medir_turno(resultado: dict, inicio: float) -> dict:
    from neural_core import sky_metricas
    resultado['ms'] = int((time.perf_counter() - inicio) * 1000)
    sky_metricas.registrar('turno', resultado.get('tipo', '?'), resultado.get('tipo') != 'error', resultado['ms'],
                           origen=_origen(resultado), detalle=resultado.get('mensaje', '') if resultado.get('tipo') == 'error' else '')
    return resultado


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
        resultado['nivel_riesgo'] = 3 if any(str(e).split('.')[0] in ('lock', 'cover', 'alarm_control_panel')
                                             for e in orden.get('entity_ids', [])) else (2 if orden['requiere_confirmacion'] else 1)
        if caps.parada_activa():
            resultado['requiere_confirmacion'] = True
            resultado['aviso'] = 'Parada de emergencia activa.'
        elif not orden['requiere_confirmacion']:
            try:
                resultado['ejecucion'] = _casa(orden['service'], orden['entity_ids'], orden['data'])
            except (RuntimeError, ValueError) as exc:
                resultado['ejecucion'] = {'ok': False, 'error': str(exc)[:200]}
            _aprender(resultado.pop('aprender', ''), resultado, resultado['ejecucion'])
        return resultado
    if resultado['tipo'] == 'correo':
        resultado['nivel_riesgo'] = 3
    if resultado['tipo'] != 'accion':
        return resultado
    propuesta = resultado['propuesta']
    resultado['requiere_confirmacion'] = True
    resultado['nivel_riesgo'] = caps.nivel_riesgo(propuesta['action'], propuesta.get('params'))
    if propuesta['action'] in caps.ACCIONES_INTERFAZ:
        # Reproductor interno, ventanas holográficas y flujo de voz: los aplica la interfaz.
        resultado['requiere_confirmacion'] = False
        resultado['interfaz'] = True
        from neural_core import sky_metricas
        sky_metricas.registrar('interfaz', propuesta['action'], True)
        _aprender(resultado.pop('aprender', ''), resultado, None)
        return resultado
    if caps.parada_activa():
        resultado['aviso'] = 'SKY está en parada de emergencia: no ejecuto acciones hasta que la levantes (Reanudar).'
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
    if caps.requiere_confirmacion(propuesta['action'], propuesta['params'], politica):
        from neural_core import sky_metricas
        sky_metricas.registrar('tarea', 'propuesta', True, detalle=propuesta['action'])
    else:
        resultado['requiere_confirmacion'] = False
        try:
            resultado['ejecucion'] = _llamar(dispositivo, request, propuesta['action'], propuesta['params'])
        except HTTPException as exc:
            resultado['ejecucion'] = {'ok': False, 'error': str(exc.detail)[:200]}
        _aprender(resultado.pop('aprender', ''), resultado, resultado['ejecucion'])
    return resultado


def _guardar_turno_seguro(role: str, text: str, mode: str) -> None:
    # Persistente y privado, no guarda PIN ni headers ni credenciales.
    try:
        from neural_core.sky_hud_history import append
        if isinstance(text, str) and text.strip():
            append(role, text[:4000], 'voz' if mode == 'voz' else 'chat')
    except (OSError, ValueError, RuntimeError):
        pass


@router.post('/mensaje')
def mensaje(body: Mensaje, request: Request):
    inicio = time.perf_counter()
    _guardar_turno_seguro('user',body.texto,body.modo)
    def terminar(resultado):
        if isinstance(resultado,dict):
            _guardar_turno_seguro('assistant',str(resultado.get('mensaje') or ''),body.modo)
        return _medir_turno(resultado,inicio)
    from .academy_voice import class_command
    academy = class_command(body.texto, lesson_id=body.lesson_id, source_text=body.source_text)
    if academy is not None:
        return terminar(academy)
    from neural_core.sky_creative_intent import handle as creative_handle
    creative_result = creative_handle(body.texto, body.proveedor)
    if creative_result is not None:
        return terminar(creative_result)
    from neural_core.sky_social_intent import prepare as social_prepare
    social_result = social_prepare(body.texto, body.proveedor)
    if social_result is not None:
        return terminar(social_result)
    from neural_core import sky_experience_learning as learning
    learned=learning.interpretar(body.texto,device=body.dispositivo,modo=body.modo)
    if learned is not None:
        return terminar(learned)
    from neural_core import sky_execution_cycle as ciclo
    if ciclo.is_sequence(body.texto):
        try:
            plan = ciclo.create(ciclo.from_text(body.texto), dispositivo=body.dispositivo, origin=body.modo)
            return terminar({'tipo': 'ciclo', 'mensaje': 'Preparé el ciclo; confirmá cada paso.',
                                 'ciclo': plan, 'proveedor': 'sky-cycle'})
        except (ciclo.CycleInvalid, ciclo.CycleConflict) as exc:
            return terminar({'tipo': 'error', 'mensaje': 'No puedo planificar esa secuencia: ' + str(exc)[:180]})
    resultado = atender(body.texto, [t.model_dump() for t in body.historial], body.proveedor, body.modo)
    return terminar(_completar(resultado, body.dispositivo, request))


@router.post('/stream')
def mensaje_stream(body: Mensaje, request: Request):
    """Igual que /mensaje, pero cuando responde el modelo local envía el texto a medida que
    se genera (NDJSON: {"delta": "..."} … {"final": {...}}), para que SKY hable sin esperar."""
    from fastapi.responses import StreamingResponse
    from neural_core import sky_asistente_personal as asis

    def eventos():
        inicio = time.perf_counter()
        _guardar_turno_seguro('user',body.texto,body.modo)
        historial = [t.model_dump() for t in body.historial]
        def linea(obj):
            return json.dumps(obj, ensure_ascii=False) + '\n'
        def final(resultado):
            if isinstance(resultado,dict):
                _guardar_turno_seguro('assistant',str(resultado.get('mensaje') or ''),body.modo)
            return linea({'final': _medir_turno(resultado, inicio)})
        from .academy_voice import class_command
        academy = class_command(body.texto, lesson_id=body.lesson_id, source_text=body.source_text)
        if academy is not None:
            yield final(academy)
            return
        from neural_core.sky_creative_intent import handle as creative_handle
        creative_result = creative_handle(body.texto, body.proveedor)
        if creative_result is not None:
            yield final(creative_result)
            return
        from neural_core.sky_social_intent import prepare as social_prepare
        social_result = social_prepare(body.texto, body.proveedor)
        if social_result is not None:
            yield final(social_result)
            return
        from neural_core import sky_experience_learning as learning
        learned=learning.interpretar(body.texto,device=body.dispositivo,modo=body.modo)
        if learned is not None:
            yield final(learned)
            return
        from neural_core import sky_execution_cycle as ciclo
        if ciclo.is_sequence(body.texto):
            try:
                plan = ciclo.create(ciclo.from_text(body.texto), dispositivo=body.dispositivo, origin=body.modo)
                yield final({'tipo': 'ciclo', 'mensaje': 'Preparé el ciclo; confirmá cada paso.',
                             'ciclo': plan, 'proveedor': 'sky-cycle'})
            except (ciclo.CycleInvalid, ciclo.CycleConflict) as exc:
                yield final({'tipo': 'error', 'mensaje': 'No puedo planificar esa secuencia: ' + str(exc)[:180]})
            return
        original = body.texto.strip()
        texto = asis.preparar(original) if original else original
        r = asis.reglas(texto) if texto else None
        if r or not texto or not asis.usar_cerebro(body.proveedor):
            yield final(_completar(r or asis.atender(original, historial, body.proveedor, body.modo), body.dispositivo, request))
            return
        from neural_core.sky_unified_agents import maybe_answer as _sky_unified_answer
        contribucion = _sky_unified_answer(texto, asis._turnos(historial), body.modo, body.proveedor)
        if contribucion is not None:
            # Los expertos trabajan dentro de SKY; se transmite una unica
            # respuesta generada, sin simular deltas de un stream inexistente.
            yield final(contribucion)
            return
        from neural_core import sky_cerebro
        completo = ''
        for evento, valor in sky_cerebro.decidir_eventos(texto, asis._turnos(historial), body.modo):
            if evento == 'delta':
                completo += valor
                yield linea({'delta': valor})
            elif evento == 'herramienta':
                resultado = asis.marcar_cerebro(asis.resolver_especial(valor), original)
                yield final(_completar(resultado, body.dispositivo, request))
                return
            elif evento == 'fin':
                asis._necesidad(original)
                yield final({'tipo': 'respuesta', 'mensaje': valor, 'proveedor': 'ollama', 'transmitido': True})
                return
            elif evento == 'error':
                if completo:
                    yield final({'tipo': 'respuesta', 'mensaje': completo, 'proveedor': 'ollama', 'transmitido': True})
                else:
                    yield final(_completar(asis.atender(original, historial, body.proveedor, body.modo), body.dispositivo, request))
                return
    return StreamingResponse(eventos(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})


class Correo(BaseModel):
    para: str = Field(min_length=6, max_length=254)
    asunto: str = Field(default='', max_length=200)
    cuerpo: str = Field(min_length=1, max_length=20000)
    en_respuesta_a: str = Field(default='', max_length=300)
    borrador_id: str = Field(default='', max_length=20)


@router.post('/correo')
def enviar_correo(body: Correo, request: Request):
    """Envío confirmado por el dueño (un correo enviado no se puede deshacer)."""
    from .sentinel import exigir_pin
    exigir_pin(request, 'enviar un correo')
    from neural_core import sky_correo
    if caps.parada_activa():
        raise HTTPException(409, 'SKY está en parada de emergencia: levantala antes de enviar.')
    try:
        res = sky_correo.enviar(body.para, body.asunto, body.cuerpo, body.en_respuesta_a)
        if body.borrador_id:
            from neural_core import sky_borradores
            sky_borradores.descartar(body.borrador_id)
        return res
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)[:200])


@router.post('/ejecutar')
def ejecutar(body: Ejecucion, request: Request):
    """Confirmación explícita del dueño desde el panel. Nivel 3: además, su PIN (si lo configuró)."""
    if caps.nivel_riesgo(body.action, body.params) >= 3:
        from .sentinel import exigir_pin
        exigir_pin(request, 'una acción de alto riesgo')
    params = dict(body.params)
    if body.action in ('note_create', 'note_append', 'note_trash'):
        params['confirmed'] = True   # este clic ES la confirmación individual que exigen las notas
    from neural_core import sky_metricas
    sky_metricas.registrar('tarea', 'confirmada', True, detalle=body.action)
    res = _llamar(body.dispositivo, request, body.action, params)
    if body.frase:
        info = {'tipo': 'accion', 'propuesta': {'action': body.action, 'params': dict(body.params),
                                                'description': DESCRIPCIONES.get(body.action, body.action)}}
        _aprender(body.frase, info, res)
        if info.get('aprendido_ahora') and isinstance(res, dict):
            res = {**res, 'aprendido_ahora': True}
    return res


@router.get('/emergencia')
def emergencia_estado():
    return {'parada': caps.parada_activa()}


@router.post('/emergencia')
def emergencia_activar():
    """Detiene toda ejecución en este equipo (el agente la respeta en cada acción)."""
    from neural_core import sky_metricas
    sky_metricas.registrar('servicio', 'parada', True, detalle='activada desde el HUD')
    return {'parada': caps.activar_parada('Botón del HUD')}


@router.delete('/emergencia')
def emergencia_levantar(request: Request):
    """Sólo el dueño, con su llave (y su PIN si lo configuró): vuelve a permitir acciones según su política."""
    from .sentinel import exigir_pin
    exigir_pin(request, 'levantar la parada de emergencia')
    from neural_core import sky_metricas
    sky_metricas.registrar('servicio', 'reanudar', True, detalle='parada levantada por el dueño')
    return {'levantada': caps.levantar_parada()}


@router.post('/casa')
def ejecutar_casa(body: OrdenCasa, request: Request):
    """Confirmación del dueño para Home Assistant (luces, escenas, clima, cortinas, cerraduras)."""
    if any(str(e).split('.')[0] in ('lock', 'cover', 'alarm_control_panel') for e in body.entity_ids):
        from .sentinel import exigir_pin
        exigir_pin(request, 'cerraduras, cortinas o alarmas')
    try:
        res = _casa(body.service, body.entity_ids, body.data)
        if body.frase:
            _aprender(body.frase, {'tipo': 'casa', 'propuesta': {'service': body.service, 'entity_ids': body.entity_ids,
                                   'data': body.data, 'description': body.frase,
                                   'requiere_confirmacion': True}}, res)
        return res
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


# SKY Operational Cycle — all routes inherit the existing owner key + MFA.
# No background autonomy and no bypass of the existing authorized device agent.
class CicloCreate(BaseModel):
    texto: str = Field(default='', max_length=1500)
    pasos: list[dict] = Field(default_factory=list, max_length=6)
    dispositivo: str = Field(default='local', min_length=1, max_length=80)
    modo: str = Field(default='chat', pattern='^(chat|voz)$')


class CicloApproval(BaseModel):
    aprobado: bool = False


@router.post('/ciclo', status_code=201)
def ciclo_crear(body: CicloCreate):
    from neural_core import sky_execution_cycle as ciclo
    try:
        if bool(body.texto.strip()) == bool(body.pasos):
            raise ciclo.CycleInvalid('Indicá un texto con acciones secuenciales o una lista de pasos, no ambos.')
        pasos = ciclo.from_text(body.texto) if body.texto.strip() else body.pasos
        return ciclo.create(pasos, dispositivo=body.dispositivo, origin=body.modo)
    except ciclo.CycleInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except ciclo.CycleConflict as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get('/ciclo/{ident}')
def ciclo_estado(ident: str):
    from neural_core import sky_execution_cycle as ciclo
    try:
        return ciclo.snapshot(ident)
    except ciclo.CycleInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except ciclo.CycleConflict as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post('/ciclo/{ident}/siguiente')
def ciclo_siguiente(ident: str, body: CicloApproval, request: Request):
    from neural_core import sky_execution_cycle as ciclo
    from .sentinel import exigir_pin
    from neural_core import sky_metricas

    def _approved_step(action: str, params: dict, device: str):
        return _llamar(device, request, action, params)

    def _owner_pin():
        exigir_pin(request, 'un paso de alto riesgo de SKY')

    start = time.perf_counter()
    try:
        result = ciclo.execute_next(ident, _approved_step, approved=body.aprobado, pin_check=_owner_pin)
    except ciclo.CycleInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except ciclo.CycleConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    sky_metricas.registrar('tarea', 'sky-ciclo', result.get('last_step', {}).get('status') == 'VERIFIED',
                           (time.perf_counter()-start)*1000, origen=result['state'])
    return result


@router.post('/ciclo/{ident}/verificar')
def ciclo_verificar(ident: str, request: Request):
    from neural_core import sky_execution_cycle as ciclo

    def lookup(command_id: str, device: str) -> dict:
        url, token = _destino(device, request)
        try:
            return dispositivos.verify_device_action(url, token, command_id)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(502, str(exc)) from exc

    try:
        return ciclo.reconcile(ident, lookup)
    except ciclo.CycleInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except ciclo.CycleConflict as exc:
        raise HTTPException(409, str(exc)) from exc


@router.delete('/ciclo/{ident}')
def ciclo_cancelar(ident: str):
    from neural_core import sky_execution_cycle as ciclo
    try:
        return ciclo.cancel(ident)
    except ciclo.CycleInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except ciclo.CycleConflict as exc:
        raise HTTPException(404, str(exc)) from exc
