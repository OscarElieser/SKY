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
    'open_file': 'Abrir documentos o carpetas locales en el equipo (Windows)',
    'social_action': 'Gestionar publicaciones, mensajes y comentarios en redes sociales',
    'player_control': 'Control del reproductor de video (modos, tamaño, pausa, cerrar)',
    'task_action': 'Gestionar tareas en segundo plano (presentaciones, documentos, modificaciones)',
    'voice_control': 'Control del flujo conversacional de voz (pausa, ritmo, interrupción, repetición)',
}
APP_OPTIONS = [
    'calculator', 'text_editor', 'file_manager', 'browser',
    'chrome', 'edge', 'firefox',
    'word', 'excel', 'powerpoint', 'vscode'
]
WINDOW_SUBACTIONS = frozenset({'list', 'focus', 'minimize', 'restore', 'close'})
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

    # Comandos de control conversacional directo (voz, ritmo, pausa, finalización)
    from neural_core.voice_coordinator import coordinador_voz
    vc = coordinador_voz.check_voice_control_command(clean)
    if vc:
        return vc

    # Saludos y confirmación de escucha ("SKY, ¿me escuchás?")
    if re.search(r'\b(?:me\s+escuchas|me\s+ois|estas\s+ahi|estas\s+conectado)\b', clean):
        return {'action': 'status', 'params': {'greeting': True, 'message': 'Sí, te escucho. ¿Qué necesitás?'},
                'description': 'Comprobar escucha activa'}

    if re.search(r'\b(estado|informacion|informacion del|diagnostico|como esta)\b.*\b(equipo|pc|computadora|ordenador|dispositivo)\b', clean):
        return {'action': 'status', 'params': {}, 'description': 'Consultar estado del equipo'}

    # Modos del reproductor SKY (Mini, Ampliado, Pantalla Completa, Normal, Cerrar)
    if re.search(r'\b(?:muestra|mostrar|mostra|pon|pone|poner|cambia|cambiar|ver|hace|hacer|ponelo|hacelo)?\s*(?:el\s+video\s+|el\s+reproductor\s+)?(?:en\s+)?(?:mini|miniventana|pequeno|mas\s+pequeno|chico|mas\s+chico)\b|\bmodo\s+mini\b|\bmini\s+ventana\b|\bminiventana\b', clean):
        return {'action': 'player_control', 'params': {'subaction': 'mode_mini'}, 'description': 'Mostrar reproductor en mini ventana flotante'}
    if re.search(r'\b(?:amplia|ampliar|agranda|agrandar)\s+(?:la\s+)?ventana\b|\bmodo\s+ampliado\b|\bventana\s+ampliada\b|\bver\s+ampliado\b|\bmas\s+grande\b|\bponelo\s+grande\b', clean):
        return {'action': 'player_control', 'params': {'subaction': 'mode_expanded'}, 'description': 'Ampliar reproductor a vista completa'}
    if re.search(r'\b(?:pantalla\s+completa|fullscreen|ponelo\s+en\s+pantalla\s+completa|pon\s+pantalla\s+completa)\b', clean):
        return {'action': 'player_control', 'params': {'subaction': 'mode_fullscreen'}, 'description': 'Activar pantalla completa en el reproductor'}
    if re.search(r'\b(?:tamano\s+normal|modo\s+normal|volver\s+al\s+tamano\s+normal|volve\s+al\s+tamano\s+normal|restaura\s+tamano)\b', clean):
        return {'action': 'player_control', 'params': {'subaction': 'mode_normal'}, 'description': 'Restaurar reproductor a tamaño normal'}
    if re.search(r'\b(?:cierra|cerra|cerrar|quita|quitar|oculta|ocultar)\s+(?:el\s+)?reproductor\b', clean):
        return {'action': 'player_control', 'params': {'subaction': 'close'}, 'description': 'Cerrar reproductor multimedia'}
    if re.search(r'\b(?:siguiente|proximo|otro)\s+video\b', clean):
        return {'action': 'player_control', 'params': {'subaction': 'next'}, 'description': 'Reproducir siguiente video'}

    media_phrases = (
        (r'\b(siguiente|proxima)\b.*\b(cancion|pista|video|tema)\b', 'next_track'),
        (r'\b(anterior|previa)\b.*\b(cancion|pista|video|tema)\b', 'previous_track'),
        (r'\b(sube|subir|subi|aumenta|aumentar)\b.*\bvolumen\b', 'volume_up'),
        (r'\b(baja|bajar|reduce|reducir)\b.*\bvolumen\b', 'volume_down'),
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

    m_close = re.search(r'\b(?:cierra|cerrar|cerra)\s+(?:la\s+ventana\s*(?:de\s*)?|ventana\s*(?:de\s*)?|la\s+app\s*(?:de\s*)?|la\s+aplicacion\s*(?:de\s*)?)?([a-z0-9_\-\. ]{2,50})?\b', clean)
    if m_close and not re.search(r'\b(reproductor|video|musica|cancion)\b', clean):
        raw_t = (m_close.group(1) or '').strip()
        target = '' if raw_t in ('ventana', 'la ventana', 'app', 'la app', '') else raw_t
        return {'action': 'window_action', 'params': {'subaction': 'close', 'target': target},
                'description': f'Cerrar ventana {target}' if target else 'Cerrar ventana activa'}

    # Modo texto inmediato ("SKY, quiero escribir")
    if re.search(r'\b(?:quiero\s+escribir|abrir?\s+(?:el\s+)?chat|modo\s+texto|escribir\s+por\s+chat|activar?\s+chat)\b', clean):
        return {'action': 'player_control', 'params': {'subaction': 'text_mode'},
                'description': 'Activar modo de texto / chat'}

    # Tareas en segundo plano / presentaciones / documentos Office
    m_pres = re.search(r'\b(?:prepara|preparar|crea|crear|hace|hacer|arma|armar)\s+(?:una\s+)?presentacion\s+(?:sobre|de|acerca\s+de)\s+(.+)', clean)
    if m_pres:
        topic = m_pres.group(1).strip()
        return {'action': 'task_action', 'params': {'subaction': 'create_presentation', 'topic': topic},
                'description': f'Preparar presentación sobre {topic}'}

    m_add_task = re.search(r'\b(?:agrega|agregar|anade|añade|incluye|incluir)\s+(?:fotografias|fotos|imagenes|datos|informacion|detalles)\s+(?:de\s+|sobre\s+|a\s+la\s+presentacion\s+(?:de\s+|sobre\s+)?|al\s+trabajo\s+(?:de\s+|sobre\s+)?)?(.+)', clean)
    if m_add_task and not re.search(r'\b(nota|cancion|video)\b', clean):
        detail = m_add_task.group(1).strip()
        return {'action': 'task_action', 'params': {'subaction': 'append', 'modification': detail},
                'description': f'Modificar trabajo en curso: agregar {detail}'}

    m_doc = re.search(r'\b(?:crea|crear|genera|generar|arma|armar)\s+(?:un\s+)?documento\s+(?:nuevo\s+)?(?:sobre|de|llamado|titulado)?\s*(.+)?', clean)
    if m_doc and not re.search(r'\b(nota|presentacion)\b', clean):
        topic = (m_doc.group(1) or 'documento general').strip()
        return {'action': 'task_action', 'params': {'subaction': 'create_document', 'topic': topic},
                'description': f'Crear documento sobre {topic}'}


    # YouTube y reproducción de medios / música
    yt_match = re.search(r'\b(?:abre|abrir|abri|pon|pone|poner|reproduce|reproducir|busca|buscar)\s+(?:en\s+)?youtube(?:\s+(?:y\s+)?(?:pon|pone|poner|busca|buscar|con|el\s+video\s+de|la\s+cancion\s+de|de)?\s*(.*))?', clean)
    if not yt_match and 'youtube' in clean and any(w in clean for w in ['pon', 'pone', 'busca', 'reproduce', 'ver']):
        yt_match = re.search(r'\byoutube\s+(?:pon|pone|busca|reproduce|ver)\s+(.*)', clean)
    if yt_match:
        raw_query = (yt_match.group(1) or '').strip()
        raw_query = re.sub(r'^(?:y\s+pon|y\s+pone|y\s+reproduce|pon|pone|reproduce|busca|con|de)\s+', '', raw_query).strip()
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
    m_music = re.search(r'\b(?:pon|pone|poner|reproduce|reproducir|toca|tocar|busca|buscar)\s+(?:musica|canciones|videos|una\s+cancion|cancion|un\s+video|video|el\s+tema|tema)\s*(?:de|a|el|la)?\s*([a-z0-9_\-\. ]{2,80})$', clean)
    if not m_music:
        m_music = re.search(r'\b(?:pon|pone|poner|reproduce|reproducir)\s+(?:de\s+|a\s+|el\s+|la\s+)?([a-z0-9_\-\. ]{2,80})$', clean)
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

    # Acciones de redes sociales (comentar, enviar mensaje, publicar)
    m_com = re.search(r'\b(?:comenta|comentar)\b\s*(?:en\s+(?:la\s+publicacion|el\s+post|redes|facebook|instagram|tiktok|x|twitter))?\s*(?:diciendo|con|que\s+diga)?\s*(.*)', clean)
    if m_com and not re.search(r'\b(nota|calculadora)\b', clean):
        plat = 'redes'
        for p_cand in ['facebook', 'instagram', 'tiktok', 'twitter', 'x', 'linkedin', 'whatsapp']:
            if p_cand in clean:
                plat = p_cand
                break
        body = m_com.group(1).strip()
        return {
            'action': 'social_action',
            'params': {'subaction': 'comment', 'platform': plat, 'comment': body},
            'description': f'Comentar en {plat.title()}'
        }

    m_msg = re.search(r'\b(?:responde|responder|contesta|contestar|envia\s+mensaje|enviar\s+mensaje|manda\s+mensaje)\b\s*(?:a|al|por\s+whatsapp\s+a)?\s*([a-z0-9_\-\. ]+?)\s*(?:diciendo|con\s+el\s+texto|que\s+diga)?\s*(.*)', clean)
    if m_msg and any(w in clean for w in ['mensaje', 'whatsapp', 'responde', 'contesta']):
        recip = m_msg.group(1).strip()
        body = m_msg.group(2).strip()
        return {
            'action': 'social_action',
            'params': {'subaction': 'message', 'platform': 'whatsapp', 'recipient': recip, 'message': body},
            'description': f'Enviar/Responder mensaje a {recip}'
        }

    m_post = re.search(r'\b(?:publica|publicar|postea|postear|crea\s+(?:un\s+)?post|crear\s+(?:un\s+)?post|crea\s+publicacion|crear\s+publicacion|sube\s+(?:una\s+)?foto|subir\s+(?:una\s+)?foto)\b\s*(?:en\s+|para\s+|a\s+)?(facebook|instagram|tiktok|twitter|x|linkedin|whatsapp)?\s*(.*)', clean)
    if m_post and (m_post.group(1) or m_post.group(2)):
        plat = (m_post.group(1) or 'general').strip()
        body = m_post.group(2).strip()
        if plat == 'general':
            for p_cand in ['facebook', 'instagram', 'tiktok', 'twitter', 'x', 'linkedin', 'whatsapp']:
                if re.search(r'\b(?:en|a|para)\s+' + p_cand + r'\b', clean):
                    plat = p_cand
                    break
        return {
            'action': 'social_action',
            'params': {'subaction': 'post', 'platform': plat, 'content': body},
            'description': f'Crear publicación para {plat.title()}'
        }

    # Apertura de carpetas y archivos locales (documentos, descargas, pdf, word, excel, imagenes, videos)
    m_folder = re.search(r'\b(?:abre|abrir|muestra|mostrar)\s+(?:mi\s+)?(?:carpeta\s+de\s+|carpeta\s+)?(documentos|descargas|escritorio|imagenes|fotos|videos|musica)\b', clean)
    if m_folder:
        fld = m_folder.group(1).strip()
        return {'action': 'open_file', 'params': {'target': fld}, 'description': f'Abrir carpeta de {fld}'}

    m_file = re.search(r'\b(?:abre|abrir|muestra|mostrar)\s+(?:el\s+)?(?:archivo|documento|pdf|informe|reporte|imagen|foto|video|presentacion|hoja\s+de\s+calculo)\s+(?:de\s+|titulado\s+|llamado\s+)?([a-z0-9_\-\. ]{2,80})', clean)
    if m_file:
        fname = m_file.group(1).strip()
        return {'action': 'open_file', 'params': {'target': fname}, 'description': f'Abrir archivo {fname}'}

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

        sites = {
            'whatsapp web': 'https://web.whatsapp.com',
            'whatsapp': 'https://web.whatsapp.com',
            'facebook': 'https://www.facebook.com',
            'instagram': 'https://www.instagram.com',
            'tiktok': 'https://www.tiktok.com',
            'twitter': 'https://x.com',
            'x': 'https://x.com',
            'linkedin': 'https://www.linkedin.com',
            'telegram': 'https://web.telegram.org',
            'reddit': 'https://www.reddit.com',
            'pinterest': 'https://www.pinterest.com',
            'youtube': 'https://www.youtube.com',
            'google': 'https://www.google.com',
            'baqueano': 'https://baqueanonicaragua.com',
            'wikipedia': 'https://www.wikipedia.org'
        }
        for term, url in sites.items():
            if term in clean:
                return {'action': 'open_url', 'params': {'url': url}, 'description': f'Abrir {url}'}
        match = re.search(r'https?://[^\s,;]+', text, re.I)
        if match:
            return {'action': 'open_url', 'params': {'url': match.group(0)},
                    'description': 'Abrir URL indicada'}
    return None
