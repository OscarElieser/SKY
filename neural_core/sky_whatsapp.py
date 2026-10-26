"""SKY v12.3 — Hablarle a SKY por WhatsApp (API oficial de WhatsApp Business Cloud, de Meta).

Cómo funciona:
    Vos (tu WhatsApp personal) ──escribís──► número de WhatsApp Business de SKY
    Meta ──webhook firmado──► sky_whatsapp_puente.py (sólo esta ruta es pública) ──► SKY en tu PC
    SKY ──respuesta──► Graph API de Meta ──► tu WhatsApp

Seguridad:
  * Sólo se atiende al número del dueño (SKY_WA_OWNER). Cualquier otro remitente se ignora sin responder.
  * Cada webhook se valida con la firma HMAC-SHA256 de Meta (SKY_WA_APP_SECRET); sin firma válida no se procesa.
  * Límite de 20 mensajes por minuto; los mensajes repetidos (reintentos de Meta) se descartan.
  * Las acciones respetan la política del agente: lo automático se ejecuta; lo demás pide «SÍ».
    Lo de nivel 3 (enviar correos, borrar notas, cerraduras) pide «CONFIRMO <código>» de 4 dígitos, que vence en 10 min.
  * Abrir cerraduras por WhatsApp no está permitido: se hace desde el HUD.
  * No se guardan los textos de los mensajes en los registros; el historial de la conversación (12 turnos) queda en tu PC.

Configuración (.env): SKY_WA_TOKEN (o SKY_WA_TOKEN_FILE), SKY_WA_PHONE_ID, SKY_WA_VERIFY_TOKEN,
SKY_WA_APP_SECRET, SKY_WA_OWNER (tu número con código de país, sólo dígitos), opcional SKY_WA_PLANTILLA
(plantilla aprobada para avisos fuera de la ventana de 24 h) y SKY_WA_API_VERSION.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
import unicodedata
from pathlib import Path

_LOCK = threading.Lock()
VENTANA_24H = 24 * 3600 - 300
MAX_TEXTO = 4000
LIMITE_POR_MINUTO = 20
VENCE_CONFIRMACION = 600
MAX_AUDIO = 16 * 1024 * 1024


# ------------------------------------------------------------------ configuración

def _env(nombre: str) -> str:
    valor = os.getenv(nombre, '').strip()
    archivo = os.getenv(nombre + '_FILE', '').strip()
    if not valor and archivo:
        try:
            valor = Path(archivo).expanduser().read_text(encoding='utf-8').strip()
        except OSError:
            valor = ''
    return valor


def dueno() -> str:
    return re.sub(r'\D', '', _env('SKY_WA_OWNER'))


def version() -> str:
    v = _env('SKY_WA_API_VERSION') or 'v25.0'
    return v if re.fullmatch(r'v\d{1,2}\.\d', v) else 'v25.0'


def configurado() -> bool:
    return all(_env(n) for n in ('SKY_WA_TOKEN', 'SKY_WA_PHONE_ID', 'SKY_WA_VERIFY_TOKEN', 'SKY_WA_APP_SECRET')) \
        and len(dueno()) >= 8 and re.fullmatch(r'\d{5,20}', _env('SKY_WA_PHONE_ID') or '') is not None


def estado() -> dict:
    e = _estado()
    return {'configurado': configurado(), 'dueno': ('…' + dueno()[-4:]) if dueno() else '',
            'ultimo_mensaje': e.get('ultimo_entrante'), 'ventana_abierta': ventana_abierta(),
            'plantilla_avisos': bool(_env('SKY_WA_PLANTILLA')), 'faltan': [n for n in (
                'SKY_WA_TOKEN', 'SKY_WA_PHONE_ID', 'SKY_WA_VERIFY_TOKEN', 'SKY_WA_APP_SECRET', 'SKY_WA_OWNER') if not _env(n)]}


# ------------------------------------------------------------------ estado local

def _ruta() -> Path:
    return Path.home() / '.neuralt' / 'sky_whatsapp.json'


def _estado() -> dict:
    try:
        d = json.loads(_ruta().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _guardar(d: dict) -> None:
    p = _ruta()
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    tmp.replace(p)
    try:
        p.chmod(0o600)
    except OSError:
        pass


def ventana_abierta(ahora: float | None = None) -> bool:
    """WhatsApp sólo permite mensajes libres hasta 24 h después del último mensaje del usuario."""
    ultimo = _estado().get('ultimo_entrante_ts') or 0
    return (ahora or time.time()) - float(ultimo) < VENTANA_24H


# ------------------------------------------------------------------ webhook: verificación y firma

def verificar_suscripcion(modo: str, token: str, desafio: str) -> str | None:
    esperado = _env('SKY_WA_VERIFY_TOKEN')
    if modo == 'subscribe' and esperado and hmac.compare_digest(str(token or ''), esperado) and re.fullmatch(r'[\w-]{1,100}', desafio or ''):
        return desafio
    return None


def firma_valida(cuerpo: bytes, cabecera: str) -> bool:
    secreto = _env('SKY_WA_APP_SECRET')
    if not secreto or not cabecera or not cabecera.startswith('sha256='):
        return False
    esperado = hmac.new(secreto.encode('utf-8'), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, cabecera[7:].strip())


# ------------------------------------------------------------------ Graph API

def _graph(ruta: str, cuerpo: dict | None = None, timeout: int = 20) -> dict:
    url = f'https://graph.facebook.com/{version()}/{ruta}'
    datos = json.dumps(cuerpo).encode('utf-8') if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method='POST' if cuerpo is not None else 'GET',
                                 headers={'Authorization': 'Bearer ' + _env('SKY_WA_TOKEN'), 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(1_000_000))


def enviar_texto(texto: str, para: str | None = None) -> dict:
    para = re.sub(r'\D', '', para or dueno())
    if para != dueno():
        raise PermissionError('SKY sólo le escribe por WhatsApp a su dueño.')
    texto = str(texto or '').strip()[:MAX_TEXTO] or '…'
    res = _graph(f"{_env('SKY_WA_PHONE_ID')}/messages", {
        'messaging_product': 'whatsapp', 'recipient_type': 'individual', 'to': para,
        'type': 'text', 'text': {'preview_url': False, 'body': texto}})
    _contar('whatsapp_enviado')
    return res


def _contar(nombre: str) -> None:
    """Meta cobra a partir del mensaje de servicio 1001 del mes y cada plantilla: SKY los cuenta en sus KPIs."""
    try:
        from . import sky_metricas
        sky_metricas.registrar('servicio', nombre, True)
    except Exception:
        pass


def enviar_aviso(texto: str) -> bool:
    """Avisos proactivos (recordatorios, problemas, tareas programadas). Dentro de las 24 h: texto libre.
    Fuera: sólo con una plantilla aprobada por Meta (SKY_WA_PLANTILLA, con una variable {{1}})."""
    if not configurado() or os.getenv('SKY_WA_AVISOS', '1').strip() == '0':
        return False
    try:
        if ventana_abierta():
            enviar_texto(texto)
            return True
        plantilla = _env('SKY_WA_PLANTILLA')
        if not plantilla:
            return False
        _graph(f"{_env('SKY_WA_PHONE_ID')}/messages", {
            'messaging_product': 'whatsapp', 'to': dueno(), 'type': 'template',
            'template': {'name': plantilla, 'language': {'code': _env('SKY_WA_PLANTILLA_IDIOMA') or 'es'},
                         'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': str(texto)[:900]}]}]}})
        _contar('whatsapp_plantilla')
        return True
    except Exception:
        return False


def descargar_audio(media_id: str) -> tuple[bytes, str]:
    if not re.fullmatch(r'\d{5,40}', str(media_id or '')):
        raise ValueError('Identificador de audio inválido.')
    info = _graph(media_id)
    url = str(info.get('url', ''))
    if not url.startswith('https://') or int(info.get('file_size') or 0) > MAX_AUDIO:
        raise ValueError('Audio no disponible o demasiado grande.')
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + _env('SKY_WA_TOKEN')})
    with urllib.request.urlopen(req, timeout=30) as r:
        datos = r.read(MAX_AUDIO + 1)
    if len(datos) > MAX_AUDIO:
        raise ValueError('Audio demasiado grande.')
    tipo = str(info.get('mime_type', 'audio/ogg'))
    ext = '.ogg' if 'ogg' in tipo else '.mp3' if 'mpeg' in tipo else '.m4a' if 'mp4' in tipo else '.ogg'
    return datos, 'nota' + ext


def transcribir(audio: bytes, nombre: str) -> str:
    from .sky_stt_isolated_v106 import isolated_transcribe
    return str(isolated_transcribe(audio, filename=nombre, language='es').get('text', '')).strip()


# ------------------------------------------------------------------ conversación

def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '').lower())
    return ' '.join(re.sub(r'[^\w\s]', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).split())


_SI = re.compile(r'^(?:si|sí|dale|ok|okay|hacelo|hazlo|confirmo|adelante|de una|va|claro)(?: sky)?$')
_NO = re.compile(r'^(?:no|cancela|cancelar|mejor no|deja|dejalo|olvidalo)(?: sky)?$')


def _limite(estado: dict, ahora: float) -> bool:
    marcas = [t for t in estado.get('marcas', []) if ahora - t < 60]
    estado['marcas'] = marcas + [ahora]
    return len(marcas) >= LIMITE_POR_MINUTO


def _pendiente_nuevo(estado: dict, tipo: str, datos: dict, nivel: int, descripcion: str) -> str:
    codigo = f'{secrets.randbelow(9000) + 1000}' if nivel >= 3 else ''
    estado['pendiente'] = {'tipo': tipo, 'datos': datos, 'nivel': nivel, 'codigo': codigo,
                           'descripcion': descripcion[:200], 'vence': estado.get('_ahora', time.time()) + VENCE_CONFIRMACION}
    if codigo:
        return f'{descripcion}. Es una operación de alto riesgo: para hacerlo respondé exactamente «CONFIRMO {codigo}» (vence en 10 minutos).'
    return f'¿Lo hago? {descripcion}. Respondé «sí» o «no».'


def _credenciales() -> tuple[str, str]:
    try:
        from .sky_voice_actions import local_agent_credentials
        return local_agent_credentials()
    except Exception:
        from .sky_asistente_personal import url_agente_local, token_agente_local
        return url_agente_local(), token_agente_local()


def _ejecutar_pendiente(p: dict) -> str:
    from . import sky_capacidades as caps
    if caps.parada_activa():
        return 'SKY está en parada de emergencia: no ejecuto nada hasta que la levantes en el HUD.'
    if p['tipo'] == 'accion':
        from .dispositivos import call_device
        from . import sky_metricas
        prop = p['datos']
        params = dict(prop.get('params') or {})
        if prop['action'] in ('note_create', 'note_append', 'note_trash'):
            params['confirmed'] = True
        base, token = _credenciales()
        res = call_device(base, token, prop['action'], params, timeout=15)
        ok, motivo = sky_metricas.resultado_ok(res)
        if ok and p.get('frase'):
            try:
                from .sky_aprendizaje import aprender_orden
                aprender_orden(p['frase'], {'tipo': 'accion', 'propuesta': prop})
            except Exception:
                pass
        if not ok and str(res.get('status', '')).upper() in ('SENT', 'RUNNING', 'PENDING', 'DISPATCHED'):
            return 'Orden enviada, todavía sin verificar: ' + str(res.get('message') or prop['description'])[:180]
        return (res.get('message') or 'Listo.') if ok else 'No se pudo: ' + (motivo or 'el agente rechazó la acción.')
    if p['tipo'] == 'casa':
        from . import sky_home_assistant as casa
        o = p['datos']
        res = casa.ejecutar(o['service'], o['entity_ids'], o.get('data', {}))
        return res.get('message') or 'Listo.'
    if p['tipo'] == 'correo':
        from . import sky_correo
        b = p['datos']['borrador']
        res = sky_correo.enviar(b['para'], b['asunto'], b['cuerpo'], b.get('en_respuesta_a', ''))
        if p['datos'].get('borrador_id'):
            from . import sky_borradores
            sky_borradores.descartar(p['datos']['borrador_id'])
        return res.get('message') or 'Correo enviado.'
    return 'No sé cómo ejecutar eso.'


def _resolver(resultado: dict, estado: dict, frase: str) -> str:
    """Convierte la respuesta estándar de SKY en texto para WhatsApp, ejecutando o pidiendo confirmación."""
    from . import sky_capacidades as caps
    tipo = resultado.get('tipo')
    if tipo in ('respuesta', 'local', 'error'):
        texto = resultado.get('mensaje') or 'Listo.'
        if resultado.get('acciones'):
            texto += '\n' + '\n'.join(f"• {a['description']}: {a['estado']}" for a in resultado['acciones'][:8])
        return texto
    if tipo == 'accion':
        prop = resultado['propuesta']
        if prop['action'] in caps.ACCIONES_INTERFAZ:
            return 'Eso es para la pantalla de SKY (HUD); desde WhatsApp no lo puedo mostrar.'
        if caps.parada_activa():
            return 'SKY está en parada de emergencia: no ejecuto acciones hasta que la levantes en el HUD.'
        from .sky_asistente_personal import ejecutar_local_si_autorizado
        try:
            hecho = ejecutar_local_si_autorizado(prop)
        except Exception as exc:
            return 'No pude hablar con el agente de tu PC: ' + str(exc)[:120]
        if hecho is not None:
            from . import sky_metricas
            ok, motivo = sky_metricas.resultado_ok(hecho)
            if ok and resultado.get('aprender'):
                try:
                    from .sky_aprendizaje import aprender_orden
                    aprender_orden(resultado['aprender'], resultado)
                except Exception:
                    pass
            if not ok and str(hecho.get('status', '')).upper() in ('SENT', 'RUNNING', 'PENDING', 'DISPATCHED'):
                return 'Orden enviada, todavía sin verificar: ' + str(hecho.get('message') or prop['description'])[:180]
            return (hecho.get('message') or prop['description'] + ': listo.') if ok else 'No se pudo: ' + motivo
        if not caps.accion_habilitada(prop['action'], caps.cargar_politica(), prop.get('params')):
            cap = caps.capacidad_para(prop['action'], prop.get('params'))
            return f'La capacidad «{cap}» está desactivada en tu PC. Activala con: python agente_dispositivo.py --activar {cap}'
        texto = _pendiente_nuevo(estado, 'accion', prop, caps.nivel_riesgo(prop['action'], prop.get('params')), prop['description'])
        estado['pendiente']['frase'] = resultado.get('aprender', '')
        return texto
    if tipo == 'casa':
        orden = resultado['propuesta']
        if orden['service'] == 'lock.unlock':
            return 'Por seguridad, las cerraduras sólo se abren desde el HUD de SKY.'
        if caps.parada_activa():
            return 'SKY está en parada de emergencia.'
        nivel = 3 if any(str(e).split('.')[0] in ('lock', 'cover', 'alarm_control_panel') for e in orden.get('entity_ids', [])) else 2
        if not orden.get('requiere_confirmacion'):
            return _ejecutar_pendiente({'tipo': 'casa', 'datos': orden})
        return _pendiente_nuevo(estado, 'casa', orden, nivel, orden['description'])
    if tipo == 'correo':
        b = resultado['borrador']
        desc = f"Enviar a {b['para']} — Asunto: {b['asunto']}\n«{b['cuerpo'][:600]}»"
        return _pendiente_nuevo(estado, 'correo', {'borrador': b, 'borrador_id': resultado.get('borrador_id', '')}, 3, desc)
    return resultado.get('mensaje') or 'Listo.'


def _turno_metrica(resultado: dict, ms: float) -> None:
    try:
        from . import sky_metricas
        via = 'aprendido' if resultado.get('aprendido') else 'cerebro' if resultado.get('via') == 'cerebro' else 'reglas'
        sky_metricas.registrar('turno', resultado.get('tipo', '?'), resultado.get('tipo') != 'error', ms, origen=via,
                               detalle='whatsapp')
    except Exception:
        pass


def _sesion_bloqueada_whatsapp(texto: str) -> str | None:
    """v12.6: con la sesión del dueño bloqueada, WhatsApp no ejecuta ni responde con datos (el PIN no se manda por
    chat). Sólo la parada de emergencia sigue funcionando. El mensaje no se guarda en el historial."""
    from .sentinel_identidad import sesion_bloqueada
    if not sesion_bloqueada():
        return None
    try:
        from .sky_aprendizaje import _norm as _norm_asis
        from .sky_asistente_personal import parada
        alerta = parada(_norm_asis(texto))
        if alerta and not (alerta.get('parada') or {}).get('reanudar'):
            return alerta.get('mensaje', 'Parada de emergencia activada.')
    except Exception:
        pass
    try:
        from . import sky_metricas
        sky_metricas.registrar('servicio', 'whatsapp_rechazado', False, detalle='sesión bloqueada')
    except Exception:
        pass
    return '🔒 SKY está bloqueada. Desbloqueala en tu PC diciendo o escribiendo tu PIN; por seguridad no lo envíes por chat.'


def atender_texto(texto: str, ahora: float | None = None) -> str:
    """Un mensaje del dueño → texto de respuesta (ejecutando lo que corresponda)."""
    ahora = ahora or time.time()
    texto = ' '.join(str(texto or '').split())[:MAX_TEXTO]
    bloqueo = _sesion_bloqueada_whatsapp(texto)
    if bloqueo:
        return bloqueo
    with _LOCK:
        estado = _estado()
    t = _norm(texto)
    estado['_ahora'] = ahora
    pend = estado.get('pendiente')
    if pend and pend.get('vence', 0) < ahora:
        pend, estado['pendiente'] = None, None
    respuesta = None
    if pend:
        codigo_ok = bool(pend.get('codigo')) and re.fullmatch(r'confirmo\s+' + pend['codigo'], t)
        if (pend.get('codigo') and codigo_ok) or (not pend.get('codigo') and _SI.match(t)):
            estado['pendiente'] = None
            try:
                respuesta = _ejecutar_pendiente(pend)
            except Exception as exc:
                respuesta = 'No se pudo: ' + str(exc)[:160]
        elif _NO.match(t):
            estado['pendiente'] = None
            respuesta = 'Cancelado.'
            try:
                from . import sky_metricas
                sky_metricas.registrar('tarea', 'cancelada', True, detalle='whatsapp')
            except Exception:
                pass
        elif pend.get('codigo') and t.startswith('confirmo'):
            respuesta = 'El código no coincide. Respondé «CONFIRMO» con el código de 4 dígitos que te mandé, o «no» para cancelar.'
    if respuesta is None:
        from .sky_asistente_personal import atender
        historial = estado.get('historial', [])[-12:]
        inicio = time.perf_counter()
        resultado = atender(texto, historial, 'auto', 'chat')
        respuesta = _resolver(resultado, estado, texto)
        _turno_metrica(resultado, (time.perf_counter() - inicio) * 1000)
    estado['historial'] = (estado.get('historial', []) + [{'role': 'user', 'content': texto[:2000]},
                                                         {'role': 'assistant', 'content': respuesta[:2000]}])[-12:]
    estado.pop('_ahora', None)
    with _LOCK:
        _guardar(estado)
    return respuesta


def procesar(payload: dict, ahora: float | None = None) -> list[str]:
    """Procesa un webhook YA verificado. Devuelve las respuestas enviadas (para pruebas y registro)."""
    ahora = ahora or time.time()
    enviados = []
    for entrada in (payload or {}).get('entry', [])[:5]:
        for cambio in entrada.get('changes', [])[:5]:
            valor = cambio.get('value') or {}
            if str((valor.get('metadata') or {}).get('phone_number_id', '')) not in ('', _env('SKY_WA_PHONE_ID')):
                continue
            for msg in valor.get('messages', [])[:10]:
                remitente = re.sub(r'\D', '', str(msg.get('from', '')))
                mid = str(msg.get('id', ''))[:120]
                if remitente != dueno():
                    from . import sky_metricas
                    sky_metricas.registrar('servicio', 'whatsapp_rechazado', False, detalle='remitente no autorizado')
                    continue
                with _LOCK:
                    estado = _estado()
                    vistos = estado.get('vistos', [])
                    if mid and mid in vistos:
                        continue
                    estado['vistos'] = (vistos + [mid])[-200:]
                    estado['ultimo_entrante_ts'] = ahora
                    estado['ultimo_entrante'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(ahora))
                    limitado = _limite(estado, ahora)
                    _guardar(estado)
                if limitado:
                    continue
                tipo = msg.get('type')
                try:
                    if tipo == 'text':
                        respuesta = atender_texto((msg.get('text') or {}).get('body', ''), ahora)
                    elif tipo == 'audio':
                        try:
                            audio, nombre = descargar_audio((msg.get('audio') or {}).get('id', ''))
                            texto = transcribir(audio, nombre)
                        except RuntimeError:
                            texto = None
                        if texto is None:
                            respuesta = ('Recibí tu nota de voz, pero la transcripción local (faster-whisper) no está '
                                         'instalada en tu PC. Mandame el pedido por texto.')
                        elif texto:
                            respuesta = f'🎙️ «{texto[:200]}»\n' + atender_texto(texto, ahora)
                        else:
                            respuesta = 'No entendí la nota de voz. ¿Me lo escribís?'
                    elif tipo == 'button':
                        respuesta = atender_texto((msg.get('button') or {}).get('text', ''), ahora)
                    elif tipo == 'interactive':
                        it = msg.get('interactive') or {}
                        respuesta = atender_texto(((it.get('button_reply') or it.get('list_reply') or {}).get('title', '')), ahora)
                    else:
                        respuesta = 'Por ahora entiendo texto y notas de voz.'
                except Exception as exc:
                    respuesta = 'Tuve un problema: ' + str(exc)[:160]
                try:
                    enviar_texto(respuesta)
                    enviados.append(respuesta)
                except Exception:
                    from . import sky_metricas
                    sky_metricas.registrar('servicio', 'whatsapp_envio', False, detalle='no se pudo responder')
    return enviados
