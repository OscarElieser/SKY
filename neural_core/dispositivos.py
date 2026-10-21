"""Cliente de dispositivos autorizados (sin comandos arbitrarios)."""
from __future__ import annotations
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
import unicodedata

ACTION_CAPABILITIES = {
    'status': 'Consultar estado del dispositivo',
    'open_url': 'Abrir un sitio web en el dispositivo',
    'launch_app': 'Abrir una aplicación permitida en el dispositivo',
    'media_key': 'Enviar tecla multimedia al reproductor del dispositivo (Windows)',
    'note_create': 'Crear nota local con confirmación',
    'note_append': 'Agregar texto a nota local con confirmación',
    'note_trash': 'Enviar una nota a la papelera recuperable con confirmación',
    'window_action': 'Gestionar ventanas abiertas autorizadas en el equipo (Windows)',
}
APP_OPTIONS = [
    'calculator', 'text_editor', 'file_manager', 'browser',
    'chrome', 'edge', 'firefox',
    'word', 'excel', 'powerpoint', 'vscode'
]
WINDOW_SUBACTIONS = frozenset({'list', 'focus', 'minimize', 'restore'})
MEDIA_KEYS = frozenset({'play_pause','next_track','previous_track','volume_up','volume_down','mute'})
_REGISTRY = Path(__file__).resolve().parent.parent / 'local_data' / 'paired_devices.json'


def validate_endpoint(url: str) -> str:
    u = urllib.parse.urlsplit(url.strip().rstrip('/'))
    if u.username or u.password or u.query or u.fragment or not u.hostname:
        raise ValueError('URL inválida: no incluyas usuario, contraseña, query o fragmento.')
    if u.scheme == 'https':
        pass
    elif u.scheme == 'http' and u.hostname in ('127.0.0.1', 'localhost', '::1'):
        pass
    else:
        raise ValueError('Usá HTTPS (Tailscale Serve) o HTTP sólo en localhost.')
    if u.path not in ('', '/'):
        raise ValueError('Usá la dirección base sin rutas adicionales.')
    if not 1 <= (u.port or 443) <= 65535:
        raise ValueError('Puerto inválido.')
    return f'{u.scheme}://{u.netloc}'


def call_device(url: str, token: str, action: str='status', params: dict | None=None, timeout: int=7):
    if action not in ACTION_CAPABILITIES:
        raise ValueError('Acción no permitida por NeuralT.')
    if not token or len(token.strip()) < 32:
        raise ValueError('Token de dispositivo inválido o no configurado.')
    base = validate_endpoint(url)
    payload = None if action == 'status' else json.dumps({'action':action, 'params': params or {}}, ensure_ascii=False).encode('utf-8')
    method = 'GET' if action == 'status' else 'POST'
    req = urllib.request.Request(base+('/status' if action=='status' else '/action'), method=method,
            data=payload, headers={'Authorization':'Bearer '+token.strip(), 'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            data=resp.read(16_384)
            return json.loads(data)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'El agente respondió HTTP {exc.code}: verificá el token y los permisos.') from exc
    except (urllib.error.URLError,TimeoutError,OSError) as exc:
        raise RuntimeError('No se pudo conectar. Verificá que el agente y Tailscale estén activos.') from exc


def paired_devices():
    try:
        data=json.loads(_REGISTRY.read_text(encoding='utf-8'))
        if not isinstance(data,list): return []
        return [x for x in data if isinstance(x,dict) and 'name' in x and 'url' in x][:100]
    except (OSError,ValueError): return []


def save_device(name: str,url: str):
    name=name.strip()[:80]
    if not name: raise ValueError('Introducí el nombre del dispositivo.')
    url=validate_endpoint(url)
    current=[x for x in paired_devices() if x['name'] != name]
    current.append({'name':name, 'url':url,'registered_at':datetime.now(timezone.utc).isoformat()})
    _REGISTRY.parent.mkdir(parents=True,exist_ok=True)
    _REGISTRY.write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
    try: _REGISTRY.chmod(0o600)
    except OSError: pass


def remove_device(name: str):
    devices=[x for x in paired_devices() if x['name']!=name]
    _REGISTRY.parent.mkdir(parents=True,exist_ok=True)
    _REGISTRY.write_text(json.dumps(devices,ensure_ascii=False,indent=2),encoding='utf-8')


def norm(s):
    s=unicodedata.normalize('NFD',s.lower())
    return ''.join(c for c in s if unicodedata.category(c)!='Mn')


def interpret_command(text: str):
    """Propone una acción local de bajo riesgo; no ejecuta acciones directamente."""
    clean = norm(text.strip())
    if not clean:
        return None
    if re.search(r'\b(estado|informacion|informacion del|diagnostico|como esta)\b.*\b(equipo|pc|computadora|ordenador|dispositivo)\b', clean):
        return {'action': 'status', 'params': {}, 'description': 'Consultar estado del equipo'}

    media_phrases = (
        (r'\b(siguiente|proxima)\b.*\b(cancion|pista|video|tema)\b', 'next_track'),
        (r'\b(anterior|previa)\b.*\b(cancion|pista|video|tema)\b', 'previous_track'),
        (r'\b(sube|subir|aumenta)\b.*\bvolumen\b', 'volume_up'),
        (r'\b(baja|bajar|reduce)\b.*\bvolumen\b', 'volume_down'),
        (r'\b(silencia|silenciar|mutea|mutear)\b', 'mute'),
        (r'\b(pausa|pausar|reanuda|reanudar|continua|continuar)\b.*\b(musica|video|reproduccion|cancion)\b', 'play_pause'),
        (r'\b(reproduce|reproducir|pausa|reanuda)\b\s*$', 'play_pause'),
    )
    for pattern, key in media_phrases:
        if re.search(pattern, clean):
            return {'action': 'media_key', 'params': {'key': key},
                    'description': 'Enviar tecla multimedia ' + key}

    # Únicamente nombres simples; toda escritura se confirma manualmente en el panel.
    simple = text.strip()
    create = re.fullmatch(r'(?i)(?:sky\s*[,;:]?\s*)?(?:crea|crear)\s+(?:una\s+)?nota\s+([A-Za-z0-9_-]{1,64})\s+(?:que\s+diga|con\s+el\s+texto)\s+(.{1,12000})', simple, re.S)
    if create:
        return {'action':'note_create', 'params':{'name':create.group(1),'content':create.group(2)},
                'description':'Crear nota '+create.group(1)+' (requiere aprobación)'}
    append = re.fullmatch(r'(?i)(?:sky\s*[,;:]?\s*)?(?:agrega|agregar|añade|anade)\s+(?:a\s+)?(?:la\s+)?nota\s+([A-Za-z0-9_-]{1,64})\s+(?:el\s+texto\s+)?(.{1,12000})', simple, re.S)
    if append:
        return {'action':'note_append','params':{'name':append.group(1),'content':append.group(2)},
                'description':'Agregar texto a '+append.group(1)+' (requiere aprobación)'}
    trash = re.fullmatch(r'(?i)(?:sky\s*[,;:]?\s*)?(?:elimina|eliminar|borra|borrar)\s+(?:la\s+)?nota\s+([A-Za-z0-9_-]{1,64})', simple)
    if trash:
        return {'action':'note_trash','params':{'name':trash.group(1)},
                'description':'Mover nota '+trash.group(1)+' a papelera (requiere aprobación)'}

    # Comandos de ventanas (Windows)
    if re.search(r'\b(que\s+ventanas|cuales\s+ventanas|lista(?:r)?\s+(?:las\s+)?ventanas|muestra(?:r)?\s+(?:las\s+)?ventanas|ver\s+ventanas|ventanas\s+abiertas)\b', clean):
        return {'action': 'window_action', 'params': {'subaction': 'list'}, 'description': 'Listar ventanas abiertas en el equipo'}

    m_focus = re.search(r'\b(?:cambia|cambiar|pasa|pasar|ve|ir|enfoca|enfocar)\s+(?:a\s+)?(?:la\s+)?(?:ventana\s+)?(?:de\s+)?([a-z0-9_\-\. ]{2,50})\b', clean)
    if m_focus and not re.search(r'\b(abre|abri|abrir|inicia|iniciar|ejecuta|ejecutar)\b', clean):
        target = m_focus.group(1).strip()
        return {'action': 'window_action', 'params': {'subaction': 'focus', 'target': target}, 'description': f'Cambiar a la ventana de {target}'}

    m_min = re.search(r'\b(?:minimiza|minimizar)\s+(?:la\s+ventana\s*(?:de\s*)?|ventana\s*(?:de\s*)?)?([a-z0-9_\-\. ]{2,50})?\b', clean)
    if m_min:
        raw_t = (m_min.group(1) or '').strip()
        target = '' if raw_t in ('ventana', 'la ventana', '') else raw_t
        return {'action': 'window_action', 'params': {'subaction': 'minimize', 'target': target},
                'description': f'Minimizar ventana {target}' if target else 'Minimizar ventana en primer plano'}

    m_rest = re.search(r'\b(?:restaura|restaurar|maximiza|maximizar)\s+(?:la\s+ventana\s*(?:de\s*)?|ventana\s*(?:de\s*)?)?([a-z0-9_\-\. ]{2,50})?\b', clean)
    if m_rest:
        raw_t = (m_rest.group(1) or '').strip()
        target = '' if raw_t in ('ventana', 'la ventana', '') else raw_t
        return {'action': 'window_action', 'params': {'subaction': 'restore', 'target': target},
                'description': f'Restaurar ventana {target}' if target else 'Restaurar ventana'}

    # YouTube y reproducción de medios / música
    yt_match = re.search(r'\b(?:abre|abrir|abri|pon|poner|reproduce|reproducir|busca|buscar)\s+(?:en\s+)?youtube(?:\s+(?:y\s+)?(?:pon|poner|busca|buscar|con|el\s+video\s+de|la\s+cancion\s+de|de)?\s*(.*))?', clean)
    if not yt_match and 'youtube' in clean and any(w in clean for w in ['pon', 'busca', 'reproduce', 'ver']):
        yt_match = re.search(r'\byoutube\s+(?:pon|busca|reproduce|ver)\s+(.*)', clean)
    if yt_match:
        raw_query = (yt_match.group(1) or '').strip()
        raw_query = re.sub(r'^(?:y\s+pon|y\s+reproduce|pon|reproduce|busca|con|de)\s+', '', raw_query).strip()
        if raw_query:
            encoded = urllib.parse.quote_plus(raw_query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            return {
                'action': 'open_url',
                'params': {'url': url, 'query': raw_query, 'service': 'youtube', 'media_type': 'video'},
                'description': f'Abrir YouTube: {raw_query}'
            }
        else:
            return {'action': 'open_url', 'params': {'url': 'https://www.youtube.com'}, 'description': 'Abrir https://www.youtube.com'}

    # Reproducción multimedia directa (música o videos)
    m_music = re.search(r'\b(?:pon|poner|reproduce|reproducir|toca|tocar)\s+(?:musica|una\s+cancion|cancion|un\s+video|video|el\s+tema|tema)?\s*(?:de|a|el|la)?\s*([a-z0-9_\-\. ]{2,80})$', clean)
    if m_music and not re.search(r'\b(nota|calculadora|bloc|explorador|ventana|archivo)\b', clean):
        query = m_music.group(1).strip()
        query = re.sub(r'^(?:de|a|el|la)\s+', '', query).strip()
        if query and query not in ('musica', 'video', 'cancion', 'reproduccion'):
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            return {
                'action': 'open_url',
                'params': {'url': url, 'query': query, 'service': 'youtube', 'media_type': 'video'},
                'description': f'Reproducir {query} en YouTube'
            }

    # Búsqueda en Google / Web
    m_search = re.search(r'\b(?:busca|buscar|investiga|investigar)\s+(?:en\s+google\s+|en\s+internet\s+|en\s+la\s+web\s+)(.+)', clean)
    if not m_search:
        m_search = re.search(r'\b(?:abre|abrir)\s+google\s+y\s+(?:busca|investiga)\s+(.+)', clean)
    if m_search:
        q = m_search.group(1).strip()
        if q:
            encoded = urllib.parse.quote_plus(q)
            url = f"https://www.google.com/search?q={encoded}"
            return {
                'action': 'open_url',
                'params': {'url': url, 'query': q, 'service': 'google'},
                'description': f'Buscar "{q}" en Google'
            }

    if re.search(r'\b(abre|abri|abrir|inicia|iniciar|ejecuta|ejecutar|lanza|lanzar)\b', clean):
        app_terms = [
            ('calculadora', 'calculator'),
            ('bloc de notas', 'text_editor'),
            ('editor de texto', 'text_editor'),
            ('explorador de archivos', 'file_manager'),
            ('explorador', 'file_manager'),
            ('archivos', 'file_manager'),
            ('visual studio code', 'vscode'),
            ('vs code', 'vscode'),
            ('vscode', 'vscode'),
            ('powerpoint', 'powerpoint'),
            ('presentaciones', 'powerpoint'),
            ('excel', 'excel'),
            ('hoja de calculo', 'excel'),
            ('microsoft word', 'word'),
            ('word', 'word'),
            ('google chrome', 'chrome'),
            ('chrome', 'chrome'),
            ('microsoft edge', 'edge'),
            ('edge', 'edge'),
            ('mozilla firefox', 'firefox'),
            ('firefox', 'firefox'),
            ('navegador web', 'browser'),
            ('navegador', 'browser')
        ]
        for term, app in app_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', clean):
                return {'action': 'launch_app', 'params': {'app': app}, 'description': f'Abrir {term}'}

        sites = {'youtube': 'https://www.youtube.com', 'google': 'https://www.google.com',
                 'baqueano': 'https://baqueanonicaragua.com', 'wikipedia': 'https://www.wikipedia.org'}
        for term, url in sites.items():
            if term in clean:
                return {'action': 'open_url', 'params': {'url': url}, 'description': f'Abrir {url}'}
        match = re.search(r'https?://[^\s,;]+', text, re.I)
        if match:
            return {'action': 'open_url', 'params': {'url': match.group(0)},
                    'description': 'Abrir URL indicada'}
    return None
