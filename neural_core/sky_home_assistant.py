"""SKY v12 — Casa y oficina con Home Assistant (API REST oficial, en tu red local).

Configuración en .env del equipo donde corre SKY:
    SKY_HA_URL=http://homeassistant.local:8123      # http sólo en red local; https en cualquier caso
    SKY_HA_TOKEN=...                                  # token de larga duración (Perfil → Seguridad)
    # o SKY_HA_TOKEN_FILE=ruta/al/archivo
    SKY_HA_AUTO=light,switch,fan,media_player,scene   # dominios que se ejecutan sin clic (opcional)

Órdenes: "enciende la luz de la sala", "apaga las luces del cuarto", "activa la escena cine",
"pon el aire a 22 grados", "abre la cortina", "cierra el portón".
Cerraduras, portones/cortinas y clima SIEMPRE piden confirmación. Las alarmas no se controlan.
El token nunca se registra ni se devuelve al navegador.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SERVICIOS_PERMITIDOS = {
    'light': {'turn_on', 'turn_off', 'toggle'},
    'switch': {'turn_on', 'turn_off', 'toggle'},
    'fan': {'turn_on', 'turn_off', 'toggle'},
    'media_player': {'turn_on', 'turn_off', 'media_play_pause', 'media_next_track', 'media_previous_track',
                     'volume_up', 'volume_down', 'volume_mute'},
    'scene': {'turn_on'},
    'script': {'turn_on'},
    'cover': {'open_cover', 'close_cover', 'stop_cover'},
    'climate': {'set_temperature', 'turn_on', 'turn_off'},
    'lock': {'lock', 'unlock'},
}
SIEMPRE_CONFIRMAR = frozenset({'lock', 'cover', 'climate', 'script'})
AUTO_POR_DEFECTO = 'light,switch,fan,media_player,scene'
_CACHE: dict = {'t': 0.0, 'estados': []}
_CACHE_SEG = 20


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s).lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def _token() -> str:
    tok = os.getenv('SKY_HA_TOKEN', '').strip()
    archivo = os.getenv('SKY_HA_TOKEN_FILE', '').strip()
    if not tok and archivo:
        try:
            tok = Path(archivo).expanduser().read_text(encoding='utf-8').strip()
        except OSError:
            tok = ''
    return tok


def validar_url(url: str) -> str:
    u = urllib.parse.urlsplit(str(url or '').strip().rstrip('/'))
    if not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('', '/'):
        raise ValueError('SKY_HA_URL debe ser sólo la dirección base, por ejemplo http://homeassistant.local:8123')
    if u.scheme == 'https':
        return f'{u.scheme}://{u.netloc}'
    if u.scheme != 'http':
        raise ValueError('SKY_HA_URL debe empezar con http:// o https://')
    host = u.hostname
    local = host in ('localhost', '127.0.0.1', '::1') or host.endswith('.local') or '.' not in host
    try:
        ip = ipaddress.ip_address(host)
        local = local or ip.is_private or ip.is_loopback
    except ValueError:
        pass
    if not local:
        raise ValueError('Usá https:// para un Home Assistant fuera de tu red local.')
    return f'{u.scheme}://{u.netloc}'


def configurado() -> bool:
    return bool(os.getenv('SKY_HA_URL', '').strip() and len(_token()) >= 20)


def _peticion(metodo: str, ruta: str, cuerpo: dict | None = None, timeout: float = 6) -> object:
    if not configurado():
        raise RuntimeError('Home Assistant no está configurado (SKY_HA_URL y SKY_HA_TOKEN en .env).')
    base = validar_url(os.getenv('SKY_HA_URL', ''))
    datos = json.dumps(cuerpo).encode('utf-8') if cuerpo is not None else None
    req = urllib.request.Request(base + ruta, data=datos, method=metodo,
                                 headers={'Authorization': 'Bearer ' + _token(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read(2_000_000) or b'null')
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError('Home Assistant rechazó el token (401). Generá uno nuevo en tu perfil.') from exc
        raise RuntimeError(f'Home Assistant respondió HTTP {exc.code}.') from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError('No se pudo conectar con Home Assistant. Revisá SKY_HA_URL y tu red.') from exc


def estados(forzar: bool = False) -> list[dict]:
    """Entidades controlables, con nombre amigable (caché breve)."""
    if not forzar and time.time() - _CACHE['t'] < _CACHE_SEG:
        return _CACHE['estados']
    filas = []
    for e in _peticion('GET', '/api/states') or []:
        if not isinstance(e, dict):
            continue
        eid = str(e.get('entity_id', ''))
        dominio = eid.split('.', 1)[0]
        if dominio not in SERVICIOS_PERMITIDOS:
            continue
        attrs = e.get('attributes') or {}
        filas.append({'entity_id': eid, 'domain': dominio, 'state': str(e.get('state', ''))[:40],
                      'name': str(attrs.get('friendly_name') or eid)[:80]})
    _CACHE.update(t=time.time(), estados=filas[:400])
    return _CACHE['estados']


def _buscar(consulta: str, dominios: tuple[str, ...], filas: list[dict]) -> list[dict]:
    q = _norm(consulta)
    q = re.sub(r'\b(la|las|el|los|de|del|en|mi|mis|todas?|todos?|luz|luces|lampara|foco|focos)\b', ' ', q)
    palabras = [w for w in q.split() if len(w) > 1]
    candidatas = [f for f in filas if f['domain'] in dominios]
    if not palabras:
        return candidatas if 'todas' in _norm(consulta) or 'todos' in _norm(consulta) else candidatas[:1] if len(candidatas) == 1 else []
    puntuadas = []
    for f in candidatas:
        nombre = _norm(f['name'] + ' ' + f['entity_id'].replace('_', ' '))
        aciertos = sum(1 for w in palabras if w in nombre)
        if aciertos:
            puntuadas.append((aciertos, f))
    if not puntuadas:
        return []
    mejor = max(a for a, _ in puntuadas)
    return [f for a, f in puntuadas if a == mejor]


def requiere_confirmacion(dominio: str) -> bool:
    if dominio in SIEMPRE_CONFIRMAR:
        return True
    auto = {d.strip() for d in os.getenv('SKY_HA_AUTO', AUTO_POR_DEFECTO).split(',') if d.strip()}
    return dominio not in auto


def _orden(servicio: str, entidades: list[dict], datos: dict, descripcion: str) -> dict | None:
    if not entidades:
        return None
    dominio = entidades[0]['domain']
    return {'service': f'{dominio}.{servicio}', 'entity_ids': [e['entity_id'] for e in entidades][:20],
            'data': datos, 'description': descripcion + ': ' + ', '.join(e['name'] for e in entidades[:4]),
            'requiere_confirmacion': requiere_confirmacion(dominio)}


def interpretar(texto: str) -> dict | None:
    """Propone una acción de Home Assistant SÓLO si coincide con una entidad real."""
    if not configurado():
        return None
    t = _norm(texto).strip(' .!?¿¡')
    t = re.sub(r'^(?:sky|oye sky|hey sky)[\s,]+', '', t)
    try:
        filas = estados()
    except RuntimeError:
        return None
    m = re.match(r'^(?:pon|pone|ajusta|sube|baja)\s+(?:el\s+|la\s+)?(?:aire|clima|termostato|calefaccion|temperatura)(.*?)\s+a\s+(\d{1,2})\s*(?:grados)?$', t)
    if m:
        return _orden('set_temperature', _buscar(m.group(1), ('climate',), filas), {'temperature': int(m.group(2))},
                      f'Poner el clima a {m.group(2)} °C')
    m = re.match(r'^(?:activa|pon|pone|enciende)\s+(?:la\s+)?(?:escena|ambiente|modo)\s+(.+)$', t)
    if m:
        return _orden('turn_on', _buscar(m.group(1), ('scene',), filas), {}, 'Activar escena')
    m = re.match(r'^(abre|abri|cierra|cerra|deten|para)\s+(?:la\s+|el\s+|las\s+|los\s+)?((?:cortina|persiana|porton|garage|garaje|toldo)s?.*)$', t)
    if m:
        servicio = {'abre': 'open_cover', 'abri': 'open_cover', 'cierra': 'close_cover', 'cerra': 'close_cover'}.get(m.group(1), 'stop_cover')
        verbo = {'open_cover': 'Abrir', 'close_cover': 'Cerrar', 'stop_cover': 'Detener'}[servicio]
        return _orden(servicio, _buscar(m.group(2), ('cover',), filas), {}, verbo)
    m = re.match(r'^(?:pon|cierra|cerra|traba|asegura)\s+(?:con\s+)?(?:llave|seguro|candado)?\s*(?:la\s+|el\s+)?(?:cerradura|puerta)\s*(.*)$', t)
    if m:
        return _orden('lock', _buscar(m.group(1) or 'puerta', ('lock',), filas), {}, 'Cerrar con llave')
    m = re.match(r'^(enciende|prende|activa|apaga|desactiva|alterna)\s+(.+)$', t)
    if m:
        servicio = {'enciende': 'turn_on', 'prende': 'turn_on', 'activa': 'turn_on',
                    'apaga': 'turn_off', 'desactiva': 'turn_off', 'alterna': 'toggle'}[m.group(1)]
        resto = m.group(2)
        dominios = ('light',) if re.search(r'\b(luz|luces|lampara|foco|focos)\b', resto) else \
                   ('fan',) if re.search(r'\bventilador', resto) else \
                   ('media_player',) if re.search(r'\b(tele|television|tv|parlante|bocina)', resto) else \
                   ('light', 'switch', 'fan', 'media_player')
        verbo = {'turn_on': 'Encender', 'turn_off': 'Apagar', 'toggle': 'Alternar'}[servicio]
        return _orden(servicio, _buscar(resto, dominios, filas), {}, verbo)
    return None


def ejecutar(service: str, entity_ids: list[str], data: dict | None = None) -> dict:
    """Llama a un servicio permitido para entidades existentes."""
    if not isinstance(service, str) or service.count('.') != 1:
        raise ValueError('Servicio inválido.')
    dominio, nombre = service.split('.')
    if nombre not in SERVICIOS_PERMITIDOS.get(dominio, set()):
        raise ValueError('Servicio de Home Assistant no permitido en SKY.')
    if not isinstance(entity_ids, list) or not entity_ids or len(entity_ids) > 20:
        raise ValueError('Indicá entre 1 y 20 entidades.')
    conocidas = {f['entity_id'] for f in estados(forzar=True)}
    for eid in entity_ids:
        if not isinstance(eid, str) or eid.split('.', 1)[0] != dominio or eid not in conocidas:
            raise ValueError(f'Entidad no válida para {service}: {str(eid)[:60]}')
    extra = {}
    if dominio == 'climate' and nombre == 'set_temperature':
        temp = (data or {}).get('temperature')
        if not isinstance(temp, (int, float)) or not 10 <= temp <= 32:
            raise ValueError('Temperatura fuera de rango seguro (10–32 °C).')
        extra['temperature'] = temp
    _peticion('POST', f'/api/services/{dominio}/{nombre}', {'entity_id': entity_ids, **extra})
    _CACHE['t'] = 0.0
    return {'ok': True, 'message': f'Home Assistant ejecutó {service} en {len(entity_ids)} entidad(es).'}


def resumen() -> dict:
    if not configurado():
        return {'configurado': False}
    try:
        filas = estados()
        return {'configurado': True, 'ok': True, 'entidades': filas,
                'auto': sorted(d for d in SERVICIOS_PERMITIDOS if not requiere_confirmacion(d))}
    except RuntimeError as exc:
        return {'configurado': True, 'ok': False, 'error': str(exc)}


def servicio_celular() -> str | None:
    """SKY_HA_NOTIFY=notify.mobile_app_mi_telefono (app Home Assistant del celular)."""
    s = os.getenv('SKY_HA_NOTIFY', '').strip()
    return s if re.fullmatch(r'notify\.[a-z0-9_]{1,80}', s) else None


def notificar_celular(texto: str, titulo: str = 'SKY') -> bool:
    """Envía un aviso push al celular vía la app de Home Assistant. False si no está configurado."""
    servicio = servicio_celular()
    if not servicio or not configurado():
        return False
    _, nombre = servicio.split('.', 1)
    _peticion('POST', f'/api/services/notify/{nombre}',
              {'title': str(titulo)[:60], 'message': ' '.join(str(texto).split())[:500]})
    return True
