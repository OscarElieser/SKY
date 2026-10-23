"""SKY v11.1 — Asistente Personal: entiende órdenes en español y las convierte
en acciones del dispositivo, o responde con la IA configurada.

Flujo:  texto/voz → interpretar() → propuesta {action, params, description}
        → el dueño confirma (o se ejecuta sola si activó auto_confirm para
        esa capacidad) → dispositivos.call_device() → agente del equipo.

El intérprete nunca ejecuta nada: sólo propone. La ejecución la decide la
política local del agente y la confirmación del dueño.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from .dispositivos import interpret_command as _interpretar_basico, norm
from .sky_capacidades import (CATALOGO_APPS, DESCRIPCION_ACCIONES, url_busqueda_media)

_VERBO_ABRIR = r'(?:abre|abri|abrir|inicia|iniciar|ejecuta|ejecutar|lanza|lanzar|pon|pone|muestra|muestrame)'

# alias en español → id del catálogo
_ALIAS_APPS = [
    ('spotify', 'spotify'), ('vlc', 'vlc'), ('chrome', 'chrome'), ('google chrome', 'chrome'),
    ('firefox', 'firefox'), ('edge', 'edge'), ('visual studio code', 'vscode'), ('vs code', 'vscode'),
    ('vscode', 'vscode'), ('word', 'word'), ('excel', 'excel'), ('power point', 'powerpoint'),
    ('powerpoint', 'powerpoint'), ('whatsapp', 'whatsapp'), ('telegram', 'telegram'),
    ('camara', 'camera'), ('configuracion', 'settings'), ('ajustes', 'settings'), ('paint', 'paint'),
    ('correo', 'mail'), ('calendario', 'calendar'), ('reproductor de musica', 'music'),
]

_CARPETAS = {
    'musica': '~/Music', 'canciones': '~/Music', 'videos': '~/Videos', 'peliculas': '~/Videos',
    'documentos': '~/Documents', 'descargas': '~/Downloads', 'imagenes': '~/Pictures',
    'fotos': '~/Pictures', 'escritorio': '~/Desktop',
}

_SITIOS_BUSQUEDA = {
    'google': 'https://www.google.com/search?q={q}',
    'youtube': 'https://www.youtube.com/results?search_query={q}',
    'wikipedia': 'https://es.wikipedia.org/w/index.php?search={q}',
    'maps': 'https://www.google.com/maps/search/{q}',
    'mapas': 'https://www.google.com/maps/search/{q}',
}


def _p(action: str, params: dict, description: str) -> dict:
    return {'action': action, 'params': params, 'description': description}


def _limpiar_wake(texto: str) -> str:
    return re.sub(r'^\s*(?:/sky|sky|oye sky|hey sky|ok sky)[\s,.:;!¡]*', '', texto, flags=re.I).strip()


# Órdenes en las que manda el intérprete SKY JARVIS (dispositivos.interpret_command):
# reproductor interno, ventanas, notas, tareas, redes y carpetas de Windows/OneDrive.
_PRIORIDAD_JARVIS = frozenset({'player_control', 'holographic_window', 'voice_control', 'window_action',
                               'organize_windows', 'note_create', 'note_append', 'note_trash',
                               'task_action', 'social_action', 'open_file'})


def interpretar(texto: str) -> dict | None:
    """Une los dos intérpretes de SKY y devuelve una propuesta de acción, o None si es conversación."""
    propio = _interpretar_propio(texto)
    if propio and propio['action'] == 'list_path':
        return propio
    try:
        jarvis = _interpretar_basico(_limpiar_wake(str(texto or ''))[:2000])
    except Exception:
        jarvis = None
    jarvis = _normalizar(jarvis)
    if jarvis and jarvis.get('action') in _PRIORIDAD_JARVIS:
        return jarvis
    return propio or jarvis


def _normalizar(orden: dict | None) -> dict | None:
    """Algunas órdenes JARVIS (control de voz) llegan sin 'params' ni 'description'."""
    if not isinstance(orden, dict) or not orden.get('action'):
        return None
    params = orden.get('params')
    if not isinstance(params, dict):
        params = {k: v for k, v in orden.items() if k not in ('action', 'description', 'target_device')}
    descripcion = str(orden.get('description') or params.get('message') or orden['action'])[:200]
    salida = {'action': orden['action'], 'params': params, 'description': descripcion}
    if orden.get('target_device'):
        salida['target_device'] = orden['target_device']
    return salida


def _interpretar_propio(texto: str) -> dict | None:
    """Intérprete del Asistente Personal (música por servicio, volumen exacto, equipo)."""
    original = _limpiar_wake(str(texto or ''))[:500]
    t = norm(original).strip(' .!?¿¡')
    if not t:
        return None

    # --- volumen (antes que "pon" para no confundir con reproducir)
    m = re.search(r'\bvolumen\b.*?\b(?:al|en|a)\s+(\d{1,3})\s*(?:%|por ?ciento)?', t)
    if m and int(m.group(1)) <= 100:
        n = int(m.group(1))
        return _p('volume', {'command': 'set', 'level': n}, f'Poner el volumen al {n} %')
    if re.search(r'\b(sube|subi|subir|aumenta|aumentar|mas)\b.*\b(volumen|sonido|audio)\b|\bvolumen\b.*\b(arriba|mas alto)\b', t):
        return _p('volume', {'command': 'up'}, 'Subir el volumen')
    if re.search(r'\b(baja|baji|bajar|disminuye|reduce|menos)\b.*\b(volumen|sonido|audio)\b|\bvolumen\b.*\b(abajo|mas bajo)\b', t):
        return _p('volume', {'command': 'down'}, 'Bajar el volumen')
    if re.search(r'\b(silencia|silenciar|mutea|mute|quita el sonido|quita el silencio|activa el sonido)\b', t):
        return _p('volume', {'command': 'mute'}, 'Silenciar / activar sonido')

    # --- control multimedia
    if re.search(r'\b(siguiente|proxima|salta|saltar|adelanta)\b.*\b(cancion|tema|pista|video|track)\b|^(siguiente|next)$', t):
        return _p('media_control', {'command': 'next'}, 'Siguiente canción')
    if re.search(r'\b(anterior|previa|regresa|vuelve)\b.*\b(cancion|tema|pista|video|track)\b|\b(cancion|tema|pista)\s+anterior\b', t):
        return _p('media_control', {'command': 'previous'}, 'Canción anterior')
    if re.search(r'^(pausa|pausar|pausa la musica|pausa el video|deten|detene|para)( la musica| el video| la cancion)?$|\b(pausa|pausar)\b.*\b(musica|cancion|video|reproduccion)\b', t):
        return _p('media_control', {'command': 'play_pause'}, 'Pausar la reproducción')
    if re.search(r'^(reanuda|reanudar|continua|continuar|sigue|play|dale play)( la musica| el video| la cancion| reproduciendo)?$|\b(reanuda|continua)\b.*\b(musica|cancion|video)\b', t):
        return _p('media_control', {'command': 'play_pause'}, 'Reanudar la reproducción')
    if re.search(r'\b(deten|detene|para|stop)\b.*\b(musica|reproduccion|cancion)\b', t):
        return _p('media_control', {'command': 'stop'}, 'Detener la reproducción')

    # --- reproducir en YouTube / Spotify
    m = re.match(r'^(?:reproduce|reproducir|reproduci|pon|pone|ponme|toca|quiero escuchar|quiero ver|escuchar|ver)\s+(.+?)'
                 r'(?:\s+(?:en|por|desde)\s+(youtube music|youtube|spotify))?$', t)
    if m and not re.match(r'^(la |el )?(volumen|alarma|recordatorio|temporizador)\b', m.group(1)):
        consulta_norm = m.group(1).strip()
        servicio = (m.group(2) or 'youtube').replace(' ', '_')
        # recuperar la consulta con tildes/mayúsculas del texto original
        consulta = _recortar_original(original, consulta_norm) or consulta_norm
        consulta = re.sub(r'^(?:musica de|canciones de|la cancion|el video de|el video|la musica de)\s+', '', consulta, flags=re.I)
        if consulta:
            nombre = {'youtube': 'YouTube', 'youtube_music': 'YouTube Music', 'spotify': 'Spotify'}[servicio]
            return _p('play_media', {'query': consulta, 'service': servicio}, f'Reproducir "{consulta}" en {nombre}')

    # --- búsquedas web
    m = re.match(r'^(?:busca|buscar|busca en|buscame)\s+(?:en\s+)?(google|youtube|wikipedia|maps|mapas)\s+(.+)$', t) or \
        re.match(r'^(?:busca|buscar|buscame)\s+(.+?)\s+en\s+(google|youtube|wikipedia|maps|mapas)$', t)
    if m:
        a, b = m.group(1), m.group(2)
        sitio, consulta = (a, b) if a in _SITIOS_BUSQUEDA else (b, a)
        consulta = _recortar_original(original, consulta) or consulta
        from urllib.parse import quote_plus
        url = _SITIOS_BUSQUEDA[sitio].format(q=quote_plus(consulta))
        return _p('open_url', {'url': url}, f'Buscar "{consulta}" en {sitio.capitalize()}')

    # --- capturas, bloqueo, portapapeles, notificaciones
    if re.search(r'\b(captura|capture|screenshot|pantallazo)\b', t) and re.search(r'\b(toma|tomar|haz|hace|saca|sacar|captura|guarda)\b', t):
        return _p('screenshot', {}, 'Tomar una captura de pantalla')
    if re.search(r'\b(bloquea|bloquear)\b.*\b(pantalla|pc|computadora|equipo|sesion|laptop)\b', t):
        return _p('lock_screen', {}, 'Bloquear el equipo')
    m = re.match(r'^copia(?:r)?\s+(?:al portapapeles\s+)?(.+?)(?:\s+al portapapeles)?$', t)
    if m and 'portapapeles' in t:
        texto = _recortar_original(original, m.group(1)) or m.group(1)
        return _p('clipboard_set', {'text': texto}, 'Copiar texto al portapapeles')
    if re.search(r'\b(que hay en|lee|leer|muestra)\b.*\bportapapeles\b', t):
        return _p('clipboard_get', {}, 'Leer el portapapeles')
    m = re.match(r'^(?:notificame|avisame|muestra una notificacion(?: que diga)?|notifica)\s*(?:que\s+)?(.+)$', t)
    if m:
        msg = _recortar_original(original, m.group(1)) or m.group(1)
        return _p('notify', {'title': 'SKY', 'message': msg}, 'Mostrar notificación')

    # --- carpetas
    m = re.search(r'\b' + _VERBO_ABRIR + r'\b.*\b(?:carpeta|mis|mi)\s+(?:de\s+)?(' + '|'.join(_CARPETAS) + r')\b', t)
    if m:
        return _p('open_path', {'path': _CARPETAS[m.group(1)]}, f'Abrir la carpeta {m.group(1)}')
    m = re.search(r'\b(?:que hay en|lista|listar|muestrame que hay en)\b.*\b(?:mis|mi|la carpeta(?: de)?)\s+(' + '|'.join(_CARPETAS) + r')\b', t)
    if m:
        return _p('list_path', {'path': _CARPETAS[m.group(1)]}, f'Listar la carpeta {m.group(1)}')

    # --- apps del catálogo ampliado
    if re.search(r'\b' + _VERBO_ABRIR + r'\b', t):
        for alias, app in sorted(_ALIAS_APPS, key=lambda x: -len(x[0])):
            if re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', t):
                return _p('launch_app', {'app': app}, f'Abrir {CATALOGO_APPS[app]["nombre"]}')
        # apps personalizadas que el dueño declaró en su política local
        try:
            from .sky_capacidades import cargar_politica
            for app in cargar_politica().get('custom_apps', {}):
                if re.search(r'(?<!\w)' + re.escape(app) + r'(?!\w)', t):
                    return _p('launch_app', {'app': app}, f'Abrir {app}')
        except Exception:
            pass

    return None


def _recortar_original(original: str, fragmento_norm: str) -> str | None:
    """Devuelve el fragmento con su ortografía original (tildes, mayúsculas)."""
    if not fragmento_norm:
        return None
    o_norm = norm(original)
    i = o_norm.find(fragmento_norm)
    if i < 0 or len(o_norm) != len(original):
        return None
    return original[i:i + len(fragmento_norm)].strip()


SISTEMA_ASISTENTE = (
    'Sos SKY, el asistente personal de Oscar Elieser Chamorro Guzmán. Estás hablando en voz alta: respondé en el '
    'idioma del usuario con frases naturales y cortas (2 a 4 oraciones), sin listas, emojis, markdown ni fórmulas, '
    'salvo que pida detalle. Si pide controlar su equipo y la '
    'orden no se entendió, sugerí cómo decirla: "abre Spotify", "reproduce Bad Bunny en Spotify", '
    '"sube el volumen", "pausa la música", "toma una captura", "abre mis documentos", "bloquea la pantalla". '
    'Nunca afirmes haber ejecutado acciones en el dispositivo: eso sólo lo hace el agente tras la confirmación.'
)


def atender(texto: str, historial: list[dict] | None = None, proveedor: str = 'auto', modo: str = 'chat') -> dict:
    """Punto de entrada único del asistente.

    modo='voz'  → respuesta breve y conversacional (para hablarla sin esperas).
    modo='chat' → el cerebro completo de SKY (documentos, memorias, evidencias).

    Devuelve uno de:
      {'tipo':'accion','propuesta':{...},'mensaje':str}
      {'tipo':'local','mensaje':str}            (calculadora, hora… de sky_agent)
      {'tipo':'respuesta','mensaje':str,'proveedor':str}
      {'tipo':'error','mensaje':str}
    """
    texto = str(texto or '').strip()
    if not texto:
        return {'tipo': 'error', 'mensaje': 'Decime qué necesitás.'}
    if len(texto) > 4000:
        return {'tipo': 'error', 'mensaje': 'El mensaje es demasiado largo (máx. 4000 caracteres).'}
    try:
        from .sky_agent import interpret_local_command
        local = interpret_local_command(texto)
        if local:
            return {'tipo': 'local', 'mensaje': local}
    except Exception:
        pass
    propuesta = interpretar(texto)
    if propuesta:
        return {'tipo': 'accion', 'propuesta': propuesta,
                'mensaje': propuesta['description'] + ' — ' + DESCRIPCION_ACCIONES.get(propuesta['action'], '')}
    try:
        from . import sky_home_assistant as casa
        orden_casa = casa.interpretar(texto)
        if orden_casa:
            return {'tipo': 'casa', 'propuesta': orden_casa, 'mensaje': orden_casa['description']}
    except Exception:
        pass
    turnos = [{'role': h['role'], 'content': str(h['content'])[:4000]} for h in (historial or [])[-12:]
              if isinstance(h, dict) and h.get('role') in ('user', 'assistant') and h.get('content')]
    try:
        from .providers import ProviderError
    except Exception as exc:  # dependencias opcionales ausentes
        return {'tipo': 'error', 'mensaje': 'El motor de IA no está disponible: ' + str(exc)[:160]}
    try:
        if modo == 'voz':
            from .providers import reply, choose_provider
            nombre, _ = choose_provider(proveedor or 'auto')
            mensajes = [{'role': 'system', 'content': SISTEMA_ASISTENTE}, *turnos, {'role': 'user', 'content': texto}]
            return {'tipo': 'respuesta', 'mensaje': reply(mensajes, nombre, max_output_tokens=600), 'proveedor': nombre}
        from .assistant import responder
        respuesta, _ = responder(texto, 'Asistente SKY personal', turnos, proveedor=proveedor or 'auto')
        return {'tipo': 'respuesta', 'mensaje': respuesta, 'proveedor': proveedor or 'auto'}
    except ProviderError as exc:
        return {'tipo': 'error', 'mensaje': 'Configurá un proveedor de IA: Ollama para 100 % local (ollama serve), '
                                             'o una clave en .env (GEMINI_API_KEY, ANTHROPIC_API_KEY…). Detalle: ' + str(exc)[:160]}
    except Exception as exc:
        return {'tipo': 'error', 'mensaje': 'No pude consultar la IA: ' + str(exc)[:160]}


AYUDA = [
    ('Música y video', ['reproduce Bad Bunny en Spotify', 'pon lofi para estudiar', 'pausa la música', 'siguiente canción']),
    ('Volumen', ['sube el volumen', 'baja el volumen', 'volumen al 30', 'silencia']),
    ('Aplicaciones', ['abre Spotify', 'abre Word', 'abre WhatsApp', 'abre la calculadora']),
    ('Web', ['busca recetas de gallo pinto en Google', 'abre YouTube', 'busca en mapas León Nicaragua']),
    ('Archivos', ['abre mis documentos', 'qué hay en mis descargas']),
    ('Equipo', ['toma una captura', 'bloquea la pantalla', 'copia hola mundo al portapapeles', 'avísame que tengo reunión']),
]


# ---------------------------------------------------------------- agente local

def url_agente_local() -> str:
    return f'http://127.0.0.1:{int(os.getenv("SKY_DEVICE_PORT") or os.getenv("NEURALT_DEVICE_PORT", "8766"))}'


def token_agente_local() -> str:
    env = (os.getenv('SKY_DEVICE_TOKEN') or os.getenv('NEURALT_DEVICE_TOKEN', '')).strip()
    if env:
        return env
    try:
        return (Path.home() / '.neuralt' / 'device_agent.token').read_text(encoding='utf-8').strip()
    except OSError:
        return ''


def ejecutar_local_si_autorizado(propuesta: dict) -> dict | None:
    """Para la voz en este mismo equipo: ejecuta la propuesta sólo si el dueño
    activó la capacidad Y la marcó como automática en su política local.
    Devuelve el resultado del agente, o None si hace falta confirmar en el panel."""
    from . import sky_capacidades as caps
    from .dispositivos import call_device
    politica = caps.cargar_politica()
    accion, params = propuesta['action'], propuesta.get('params', {})
    if not caps.accion_habilitada(accion, politica, params) or caps.requiere_confirmacion(accion, params, politica):
        return None
    try:
        from .sky_voice_actions import local_agent_credentials
        base, token = local_agent_credentials()   # detecta 8766/8765 o SKY_DEVICE_PORT
    except Exception:
        base, token = url_agente_local(), token_agente_local()
    if not token:
        return None
    return call_device(base, token, accion, params, timeout=12)
