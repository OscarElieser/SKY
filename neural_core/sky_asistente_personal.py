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


def resolver_especial(r: dict) -> dict:
    """Convierte resultados de agenda/correo/rutinas/avisos en la respuesta estándar,
    ejecutando lo que es inmediato y seguro (crear un recordatorio, leer correo)."""
    tipo = r.get('tipo')
    if tipo == 'recordatorio':
        from . import sky_rutinas
        try:
            item = sky_rutinas.crear(r['texto'], r['cuando'], r.get('clase', 'recordatorio'))
        except (ValueError, KeyError) as exc:
            return {'tipo': 'error', 'mensaje': 'No pude crear el recordatorio: ' + str(exc)[:120]}
        return {'tipo': 'respuesta', 'mensaje': 'Listo. ' + r['description'] + '.', 'proveedor': 'sky-agenda', 'recordatorio': item}
    if tipo == 'agenda':
        from . import sky_rutinas
        return {'tipo': 'respuesta', 'mensaje': sky_rutinas.describir_agenda(), 'proveedor': 'sky-agenda'}
    if tipo == 'rutina':
        from . import sky_rutinas
        res = sky_rutinas.ejecutar_rutina(r['rutina'])
        return {'tipo': 'respuesta', 'mensaje': res['mensaje'] or 'Rutina ejecutada.', 'proveedor': 'sky-rutina', 'acciones': res['acciones']}
    if tipo == 'correo_leer':
        from . import sky_correo
        try:
            correos = sky_correo.no_leidos(6)
        except RuntimeError as exc:
            return {'tipo': 'error', 'mensaje': str(exc)}
        if not correos:
            return {'tipo': 'respuesta', 'mensaje': 'No tenés correos nuevos.', 'proveedor': 'sky-correo'}
        partes = [f"de {c['de']}: {c['asunto']}" for c in correos]
        return {'tipo': 'respuesta', 'proveedor': 'sky-correo', 'correos': correos,
                'mensaje': f'Tenés {len(correos)} correos nuevos. ' + '; '.join(partes) + '.'}
    if tipo == 'correo_enviar':
        return {'tipo': 'correo', 'borrador': r['borrador'], 'mensaje': r['description'], 'requiere_confirmacion': True}
    if tipo in ('correo_aviso', 'aviso'):
        return {'tipo': 'respuesta', 'mensaje': r['description'], 'proveedor': 'sky'}
    if tipo == 'accion':
        p = r['propuesta']
        return {'tipo': 'accion', 'propuesta': p, 'mensaje': p['description'] + ' — ' + DESCRIPCION_ACCIONES.get(p['action'], '')}
    if tipo == 'casa':
        return {'tipo': 'casa', 'propuesta': r['propuesta'], 'mensaje': r['propuesta']['description']}
    if tipo == 'kpi':
        from . import sky_metricas
        datos = sky_metricas.resumen(r.get('periodo', 'hoy'))
        texto_kpi = sky_metricas.diagnosticar(datos) if r.get('diagnostico') else sky_metricas.describir(datos)
        return {'tipo': 'respuesta', 'mensaje': texto_kpi, 'proveedor': 'sky-metricas',
                'modulo': 'kpi', 'kpi': datos}
    if tipo == 'aprendizaje':
        from . import sky_aprendizaje
        return sky_aprendizaje.interpretar(r['texto']) or {'tipo': 'error', 'mensaje': 'No entendí qué aprender.'}
    return r


def preparar(texto: str) -> str:
    """Si el dueño le enseñó a SKY esa frase («cuando diga modo cine, …»), devuelve la orden enseñada."""
    try:
        from . import sky_aprendizaje
        return sky_aprendizaje.alias_para(texto) or texto
    except Exception:
        return texto


def reglas(texto: str) -> dict | None:
    """Todas las reglas rápidas, en orden. None si ninguna entiende la orden."""
    from .sky_aprendizaje import _norm
    stop = parada(_norm(texto))   # la parada de emergencia va antes que todo
    if stop:
        return stop
    try:
        from . import sentinel_estado
        seg = sentinel_estado.interpretar(texto)   # SENTINEL: consultas y restricciones de seguridad
    except Exception as exc:
        seg = {'tipo': 'error', 'mensaje': 'No pude consultar la seguridad: ' + str(exc)[:120]}
    if seg:
        return seg
    try:
        from .sky_agent import interpret_local_command
        local = interpret_local_command(texto)
        if local:
            return {'tipo': 'local', 'mensaje': local}
    except Exception:
        pass
    from . import sky_rutinas, sky_correo, sky_contactos
    rutina = sky_rutinas.rutina_por_frase(texto)
    if rutina:
        return resolver_especial({'tipo': 'rutina', 'rutina': rutina})
    # Skillpack externo: voz y texto comparten la misma ruta segura,
    # sólo para órdenes explícitas y sin efectos externos.
    from . import sky_skillpack
    paquete = sky_skillpack.interpretar(texto)
    if paquete:
        return paquete
    # Investigaciones externas solo bajo petición explícita y de lectura.
    from . import sky_research_commands
    research = sky_research_commands.interpretar(texto)
    if research:
        return research
    from . import sky_skills, sky_perfil
    try:
        from . import sky_habilidades
        r = sky_perfil.interpretar(_norm(texto)) or sky_skills.interpretar(texto) or sky_habilidades.interpretar(texto)
    except Exception as exc:
        r = {'tipo': 'error', 'mensaje': 'No pude completar eso: ' + str(exc)[:140]}
    if r:
        return r
    for modulo in (sky_rutinas, sky_contactos, sky_correo):
        try:
            r = modulo.interpretar(texto)
        except Exception:
            r = None
        if r:
            return resolver_especial(r)
    from . import sky_aprendizaje
    try:
        r = sky_aprendizaje.interpretar(texto)
    except Exception as exc:
        r = {'tipo': 'error', 'mensaje': 'No pude aprender eso: ' + str(exc)[:120]}
    if r:
        return r
    hud = _reglas_hud(sky_aprendizaje._norm(texto))
    if hud:
        return {'tipo': 'accion', 'propuesta': hud, 'mensaje': hud['description']}
    from . import sky_metricas
    kpi = sky_metricas.interpretar(sky_aprendizaje._norm(texto))
    if kpi:
        return resolver_especial(kpi)
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
    # Atajos que SKY aprendió del cerebro: la misma frase ya no necesita al modelo.
    try:
        aprendido = sky_aprendizaje.orden_aprendida(texto)
    except Exception:
        aprendido = None
    if aprendido:
        if aprendido['tipo'] == 'casa':
            # Los permisos de la casa se vuelven a calcular hoy (SKY_HA_AUTO puede haber cambiado).
            from . import sky_home_assistant as casa
            p = aprendido['propuesta']
            p['requiere_confirmacion'] = any(casa.requiere_confirmacion(str(e).split('.')[0]) for e in p.get('entity_ids') or ['?.x'])
        r = resolver_especial(aprendido)
        r['aprendido'] = True
        return r
    return None


_PANEL = r'(?:el |la |los |las )?(?:panel|paneles|ventana|kpis?|metricas|indicadores|rendimiento|estadisticas)(?: de (?:kpis?|rendimiento|metricas|indicadores|sky))?'


_PARAR = re.compile(r'^(?:sky )?(?:para todo|para todas las acciones|deten(?:te)?(?: todo| todas las acciones| todas las tareas)?|'
                    r'parada de emergencia|emergencia|modo emergencia|cancela todo|cancela todas las acciones|alto total|frena todo)$')
_REANUDAR = re.compile(r'^(?:quita|levanta|desactiva|termina) (?:la )?(?:parada|emergencia|parada de emergencia)$|'
                       r'^(?:reanuda|retoma) (?:las acciones|el control|todo)$|^ya (?:puedes|podes) (?:seguir|continuar)$')


def parada(t: str) -> dict | None:
    """Parada de emergencia: detener es inmediato; reanudar siempre requiere un clic del dueño."""
    from . import sky_capacidades as caps
    if _PARAR.match(t):
        caps.activar_parada('Orden por voz o texto')
        try:
            from . import sky_metricas
            sky_metricas.registrar('servicio', 'parada', True, detalle='activada por el dueño')
        except Exception:
            pass
        return {'tipo': 'respuesta', 'proveedor': 'sky-seguridad', 'parada': {'activa': True},
                'mensaje': 'Me detuve. No voy a ejecutar ninguna acción en tus equipos hasta que me lo autorices con un clic.'}
    if _REANUDAR.match(t):
        activa = caps.parada_activa()
        if not activa:
            return {'tipo': 'respuesta', 'proveedor': 'sky-seguridad', 'mensaje': 'No hay ninguna parada activa.'}
        return {'tipo': 'respuesta', 'proveedor': 'sky-seguridad', 'parada': {'activa': True, 'reanudar': True},
                'mensaje': 'Para reanudar necesito tu confirmación: tocá «Reanudar» en la tarjeta.'}
    return None


def _reglas_hud(t: str) -> dict | None:
    """Órdenes sobre la propia interfaz holográfica de SKY (no sobre las ventanas del escritorio)."""
    m = re.match(r'^(?:cierra|cerra|oculta|ocultá|quita|saca)(?: me)? ' + _PANEL + r'$', t)
    if m:
        cual = 'close_kpi' if re.search(r'kpi|metric|indicador|rendimiento|estadistic', t) else 'close_panel'
        return {'action': 'holographic_window', 'params': {'subaction': cual},
                'description': 'Cerrar el panel de rendimiento' if cual == 'close_kpi' else 'Cerrar el panel'}
    if re.match(r'^(?:muestra|mostra|ensena|abre|abri|ver)(?:me)? (?:los|mis) archivos$', t):
        return {'action': 'open_file', 'params': {'target': 'documentos'}, 'description': 'Abrir tus documentos'}
    return None


def _necesidad(texto: str) -> None:
    try:
        from .sky_skill_builder import registrar_necesidad
        registrar_necesidad(texto)
    except Exception:
        pass


def marcar_cerebro(resultado: dict, frase: str) -> dict:
    """Marca una acción elegida por el cerebro para que SKY la aprenda si sale bien."""
    if isinstance(resultado, dict):
        resultado['via'] = 'cerebro'
        if resultado.get('tipo') in ('accion', 'casa'):
            resultado['aprender'] = frase[:120]
    return resultado


def _turnos(historial: list[dict] | None) -> list[dict]:
    return [{'role': h['role'], 'content': str(h['content'])[:4000]} for h in (historial or [])[-12:]
            if isinstance(h, dict) and h.get('role') in ('user', 'assistant') and h.get('content')]


def usar_cerebro(proveedor: str) -> bool:
    """Cerebro con herramientas: Ollama local, o el proveedor de la nube que el dueño eligió (v12.3)."""
    from . import sky_cerebro
    proveedor = proveedor or 'auto'
    if proveedor not in ('auto', 'sky', 'ollama') + sky_cerebro.NUBE:
        return False
    sky_cerebro.preferir(proveedor)
    return sky_cerebro.disponible()


def atender(texto: str, historial: list[dict] | None = None, proveedor: str = 'auto', modo: str = 'chat') -> dict:
    """Punto de entrada único del asistente.

    1. Reglas rápidas (agenda, rutinas, correo, WhatsApp, equipo, casa): instantáneas.
    2. Cerebro con herramientas (Ollama local): entiende frases libres y referencias.
    3. Respuesta: modo='voz' breve; modo='chat' el cerebro completo de SKY (documentos, memorias).

    Devuelve: accion | casa | correo | local | respuesta | error (ver docs/api).
    """
    texto = str(texto or '').strip()
    if not texto:
        return {'tipo': 'error', 'mensaje': 'Decime qué necesitás.'}
    if len(texto) > 4000:
        return {'tipo': 'error', 'mensaje': 'El mensaje es demasiado largo (máx. 4000 caracteres).'}
    original = texto
    texto = preparar(texto)
    r = reglas(texto)
    if r:
        return r
    turnos = _turnos(historial)
    # SKY decide si necesita expertos cognitivos efimeros. No ofrecen acciones
    # ni sustituyen sky_supervisor / agentes persistentes.
    from .sky_unified_agents import maybe_answer as _sky_unified_answer
    contribucion = _sky_unified_answer(texto, turnos, modo)
    if contribucion is not None:
        return contribucion
    try:
        if usar_cerebro(proveedor):
            from . import sky_cerebro
            d = sky_cerebro.decidir(texto, turnos, modo)
            if d['tipo'] == 'herramienta':
                return marcar_cerebro(resolver_especial(d['resultado']), original)
            if d['tipo'] == 'texto':
                _necesidad(original)            # el cerebro no encontró herramienta: quizá falta una habilidad
            if d['tipo'] == 'texto' and d['mensaje'] and modo == 'voz':
                return {'tipo': 'respuesta', 'mensaje': d['mensaje'], 'proveedor': 'ollama'}
        else:
            _necesidad(original)
    except Exception:
        pass
    try:
        from .providers import ProviderError
    except Exception as exc:  # dependencias opcionales ausentes
        return {'tipo': 'error', 'mensaje': 'El motor de IA no está disponible: ' + str(exc)[:160]}
    try:
        if modo == 'voz':
            from .providers import reply, choose_provider
            nombre, _ = choose_provider(proveedor or 'auto')
            from .sky_cerebro import contexto_aprendido
            extra = contexto_aprendido(texto)
            from .sky_impacto import impact_instructions
            from .sky_pro_skills import skill_instructions
            impacto = impact_instructions('Asistente SKY personal', texto)
            skills = skill_instructions('Asistente SKY personal', texto)
            reglas_voz = SISTEMA_ASISTENTE + ('\n\n' + extra if extra else '')
            if impacto:
                reglas_voz += '\n\n' + impacto
            if skills:
                reglas_voz += '\n\n' + skills
            mensajes = [{'role': 'system', 'content': reglas_voz}, *turnos,
                        {'role': 'user', 'content': texto}]
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
    ('Agenda', ['recuérdame en 10 minutos sacar la ropa', 'pon una alarma a las 6:30', 'qué recordatorios tengo', 'buenos días']),
    ('Aprendizaje', ['aprende sobre energía solar', 'recuerda que mi equipo es el Real Madrid', 'qué sabes de mí',
                     'sigue el tema inteligencia artificial', 'cuando diga modo cine, pon el video en pantalla completa', 'no, eso no era']),
    ('Automatización', ['todos los días a las 8 prepara las respuestas de los correos', 'qué tareas programadas tengo',
                        'crea una skill modo trabajo que abra Word y ponga lofi para estudiar', 'qué borradores tengo', 'muéstrame mi perfil']),
    ('Mensajes', ['lee mis correos', 'responde al último correo diciendo gracias, lo reviso hoy', 'mandale un whatsapp a mamá que llego tarde']),
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
    if caps.parada_activa():
        return None   # parada de emergencia: nada automático
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
