"""SKY Desktop Agent v6.0 — el brazo de SKY en tu equipo (Windows, macOS y Linux).

Ejecutar en la sesión de usuario:  python agente_dispositivo.py
Puerto por defecto 8766 (la API de SKY usa 8765). Sólo escucha en 127.0.0.1;
para otros equipos usar Tailscale Serve, nunca abrir el puerto a Internet.

Vos decidís qué puede hacer SKY (la política vive sólo en este equipo):
    python agente_dispositivo.py --perfil basico       # apps, música, volumen, webs, avisos, tareas
    python agente_dispositivo.py --perfil multimedia   # lo mismo, pero sin pedir clic para lo cotidiano
    python agente_dispositivo.py --perfil completo --carpeta ~/Música --carpeta ~/Documentos
    python agente_dispositivo.py --activar windows,notes --auto lock
    python agente_dispositivo.py --ver-politica

Capacidades: estado, webs, 30+ apps (verificadas en Windows), multimedia y volumen,
YouTube/Spotify, notificaciones, tareas en segundo plano, carpetas y documentos
(con OneDrive), ventanas del escritorio, notas, escribir en la app activa,
capturas, portapapeles y bloqueo. Cada acción queda en el registro verificable
(/actions_history). Nunca: comandos de shell arbitrarios, abrir ejecutables o
scripts, descargas, instalar programas ni pagos.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import platform
import secrets
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from neural_core import sky_capacidades as caps
from neural_core.action_verifier import verificador_acciones
from neural_core.dispositivos import APP_OPTIONS, MEDIA_KEYS, WINDOW_SUBACTIONS
from neural_core.sky_notes_local import NOTE_ACTIONS, run_note_action
from neural_core.windows_controller import (
    AUTHORIZED_APPS,
    close_user_window,
    focus_user_window,
    launch_authorized_app,
    list_user_windows,
    minimize_user_window,
    open_local_file_or_folder,
    organize_windows,
    restore_user_window,
    type_text_in_active_window,
)

CONFIG_DIR = Path.home() / '.neuralt'
TOKEN_PATH = CONFIG_DIR / 'device_agent.token'
AUDIT_PATH = CONFIG_DIR / 'device_agent_audit.jsonl'
PORT = int(os.getenv('SKY_DEVICE_PORT') or os.getenv('NEURALT_DEVICE_PORT') or os.getenv('SKY_AGENT_PORT') or '8766')
LISTEN_ADDRESS = '127.0.0.1'  # No publicar HTTP sin TLS fuera de localhost
MAX_BODY = 32_768
VERSION = '6.0.0'
AGENT_NAME = 'SKY Desktop Agent'

# Acciones que verifican y registran por sí mismas en el ledger (windows_controller).
_AUTOREGISTRADAS = frozenset({'launch_app', 'open_file'})


class Desactivada(ValueError):
    """La capacidad existe pero el dueño no la activó en su política."""


def token_secret() -> str:
    env = (os.getenv('SKY_DEVICE_TOKEN') or os.getenv('NEURALT_DEVICE_TOKEN', '')).strip()
    if env:
        return env
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding='utf-8').strip()
    key = secrets.token_urlsafe(36)
    try:
        with TOKEN_PATH.open('x', encoding='utf-8') as h:
            h.write(key + '\n')
        TOKEN_PATH.chmod(0o600)
    except FileExistsError:
        return TOKEN_PATH.read_text(encoding='utf-8').strip()
    return key


def audit(action: str, result: str, detail: str = '') -> None:
    """Registro local por acción. Nunca guarda el token, textos dictados ni el portapapeles."""
    try:
        CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        with AUDIT_PATH.open('a', encoding='utf-8') as file:
            file.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(), 'action': action,
                                   'result': result, 'detail': str(detail)[:120]}, ensure_ascii=False) + '\n')
    except OSError:
        pass


def _detalle_seguro(action: str, params: dict) -> str:
    if action == 'launch_app':
        return str(params.get('app', ''))
    if action in ('media_control', 'volume'):
        return str(params.get('command', ''))
    if action == 'media_key':
        return str(params.get('key', ''))
    if action in ('window_action', 'task_action', 'player_control'):
        return str(params.get('subaction', ''))
    if action == 'word_write':
        return str(len(str(params.get('text', '')))) + ' caracteres a Word'
    if action == 'keyboard_shortcut':
        return str(params.get('shortcut', ''))[:30]
    if action == 'play_media':
        return str(params.get('service', 'archivo' if params.get('path') else ''))
    return ''


def apps_permitidas(politica: dict) -> list[str]:
    apps = caps.apps_disponibles(politica)
    if 'apps_extra' in politica['enabled']:
        apps += [a for a in AUTHORIZED_APPS if a not in apps]
    return apps


def status(politica: dict | None = None) -> dict:
    politica = politica or caps.cargar_politica()
    return {
        'ok': True,
        'agent': AGENT_NAME,
        'version': VERSION,
        'agent_version': VERSION,
        'device': platform.node() or 'Equipo local',
        'platform': platform.system(),
        'system_version': platform.release(),
        'capabilities': caps.acciones_habilitadas(politica),
        'profile': politica['perfil'],
        'enabled': politica['enabled'],
        'auto_confirm': politica['auto_confirm'],
        'allowed_apps': apps_permitidas(politica),
        'allowed_folders': len(politica['allowed_folders']),
        'system': caps.info_sistema(),
        'parada_emergencia': caps.parada_activa(),
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }


def send_media_key(key: str) -> None:
    """Tecla multimedia nativa (Windows) o su equivalente en macOS/Linux."""
    if key not in MEDIA_KEYS:
        raise ValueError('Tecla multimedia no autorizada.')
    if key in caps.TECLAS_VOLUMEN:
        caps.volumen({'volume_up': 'up', 'volume_down': 'down', 'mute': 'mute'}[key])
    else:
        caps.control_multimedia({'play_pause': 'play_pause', 'next_track': 'next', 'previous_track': 'previous'}[key])


def launch_app(app: str, politica: dict) -> dict:
    """Apps del catálogo verificado de Windows primero; luego el catálogo multiplataforma."""
    if app in AUTHORIZED_APPS:
        try:
            res = launch_authorized_app(app)
            return res if isinstance(res, dict) else {'ok': True, 'status': 'VERIFIED', 'message': f'Listo, ya está abierto {app}.'}
        except RuntimeError:
            if app not in caps.CATALOGO_APPS:
                raise
    nombre = caps.abrir_app(app, politica)
    return {'ok': True, 'status': 'RUNNING', 'app': app, 'message': f'Se solicitó abrir {nombre}.'}


def _validar(action: str, params: dict, politica: dict) -> None:
    if not isinstance(params, dict):
        raise ValueError('Parámetros inválidos.')
    if action in caps.ACCIONES_INTERFAZ:
        return
    parada = caps.parada_activa() if action != 'status' else None
    if parada:
        raise Desactivada('SKY está en parada de emergencia desde ' + str(parada.get('desde', '')) +
                          '. Levantala desde el HUD (Permisos → Reanudar) para volver a ejecutar acciones.')
    if action not in caps.ACCION_A_CAPACIDAD:
        raise ValueError(f"Acción '{action}' no permitida.")
    if action == 'launch_app':
        app = str(params.get('app', ''))[:40]
        if app not in APP_OPTIONS and app not in AUTHORIZED_APPS and app not in caps.CATALOGO_APPS \
                and app not in politica.get('custom_apps', {}):
            raise ValueError('Esta aplicación no está permitida en el agente.')
    if action == 'media_key' and params.get('key') not in MEDIA_KEYS:
        raise ValueError('Tecla multimedia no autorizada.')
    if action == 'window_action' and params.get('subaction', 'list') not in WINDOW_SUBACTIONS:
        raise ValueError('Subacción de ventana no autorizada.')
    if action == 'keyboard_shortcut':
        if params != {'shortcut': 'ctrl+f4', 'expected_app': 'winword.exe'}:
            raise ValueError('Atajo de teclado no autorizado: sólo Ctrl+F4 en Word.')
    if action == 'word_write':
        from neural_core.sky_word_editor import validar_parametros
        validar_parametros(params)
    if not caps.accion_habilitada(action, politica, params):
        cap = caps.capacidad_para(action, params)
        raise Desactivada(f'La capacidad "{cap}" está desactivada. Activala en tu equipo con: '
                          f'python agente_dispositivo.py --activar {cap}')


def _ejecutar(action: str, params: dict, politica: dict) -> dict:
    if action == 'status':
        return status(politica)
    if action == 'launch_app':
        return launch_app(str(params.get('app', '')), politica)
    if action == 'open_url':
        url = caps.validar_url_https(params.get('url', ''))
        opened = webbrowser.open(url, new=2)
        return {'ok': bool(opened), 'status': 'SENT' if opened else 'FAILED', 'message': 'Se solicitó abrir la página; la carga del navegador no está verificada.'}
    if action == 'media_key':
        send_media_key(str(params.get('key')))
        return {'ok': True, 'status': 'SENT', 'message': f'Tecla multimedia {params.get("key")} enviada.'}
    if action == 'media_control':
        caps.control_multimedia(str(params.get('command', '')))
        return {'ok': True, 'status': 'SENT', 'message': 'Control multimedia: ' + str(params['command'])}
    if action == 'volume':
        nivel = params.get('level')
        if nivel is not None:
            try:
                nivel = int(nivel)
            except (TypeError, ValueError):
                raise ValueError('Nivel de volumen inválido.')
        return {'ok': True, 'status': 'SENT', 'message': 'Volumen: ' + caps.volumen(str(params.get('command', '')), nivel)}
    if action == 'play_media':
        if params.get('path'):
            ruta = caps.abrir_ruta(str(params['path']), politica, solo_media=True)
            return {'ok': True, 'status': 'RUNNING', 'message': 'Reproduciendo ' + Path(ruta).name}
        servicio_id = str(params.get('service', 'youtube'))
        url = caps.url_busqueda_media(params.get('query', ''), servicio_id)
        webbrowser.open(url, new=2)
        servicio = {'youtube': 'YouTube', 'youtube_music': 'YouTube Music', 'spotify': 'Spotify'}[servicio_id]
        return {'ok': True, 'status': 'RUNNING', 'message': 'Abriendo ' + servicio + ': ' + str(params.get('query', ''))[:80], 'url': url}
    if action == 'notify':
        caps.notificar(params.get('title', 'SKY'), params.get('message', ''))
        return {'ok': True, 'status': 'VERIFIED', 'message': 'Notificación mostrada.'}
    if action == 'open_file':
        return open_local_file_or_folder(str(params.get('target', '')))
    if action == 'open_path':
        ruta = caps.abrir_ruta(str(params.get('path', '')), politica)
        return {'ok': True, 'status': 'RUNNING', 'message': 'Abriendo ' + Path(ruta).name}
    if action == 'list_path':
        return {'ok': True, 'status': 'VERIFIED', **caps.listar_ruta(str(params.get('path', '')), politica)}
    if action == 'keyboard_shortcut':
        from neural_core.sky_keyboard_shortcuts import enviar_ctrl_f4_word
        return enviar_ctrl_f4_word()
    if action == 'word_write':
        from neural_core.sky_word_editor import escribir_en_word
        return escribir_en_word(params)
    if action == 'window_action':
        sub = params.get('subaction', 'list')
        if sub == 'list':
            return {'ok': True, 'status': 'VERIFIED', 'windows': list_user_windows()}
        if sub == 'organize':
            return organize_windows()
        fn = {'focus': focus_user_window, 'minimize': minimize_user_window,
              'restore': restore_user_window, 'close': close_user_window}[sub]
        return fn(params.get('target', '') if sub == 'focus' else params.get('target'))
    if action == 'organize_windows':
        return organize_windows()
    if action == 'type_text':
        text = str(params.get('text', ''))
        if not text or len(text) > 5000:
            raise ValueError('El texto a escribir debe tener entre 1 y 5000 caracteres.')
        return type_text_in_active_window(text)
    if action in NOTE_ACTIONS:
        return run_note_action(action, params)
    if action == 'task_action':
        return _tarea(params)
    if action == 'screenshot':
        return {'ok': True, 'status': 'VERIFIED', 'message': 'Captura guardada.', **caps.captura_pantalla()}
    if action == 'clipboard_get':
        return {'ok': True, 'status': 'VERIFIED', 'text': caps.portapapeles_leer()}
    if action == 'clipboard_set':
        n = caps.portapapeles_escribir(params.get('text', ''))
        return {'ok': True, 'status': 'VERIFIED', 'message': f'Copiados {n} caracteres al portapapeles.'}
    if action == 'lock_screen':
        caps.bloquear_pantalla()
        return {'ok': True, 'status': 'VERIFIED', 'message': 'Equipo bloqueado.'}
    raise ValueError(f"Acción '{action}' no permitida.")


def _tarea(params: dict) -> dict:
    from neural_core.task_manager import gestor_tareas
    sub = params.get('subaction', 'create_presentation')
    topic = str(params.get('topic', '') or 'tema general')[:200]
    if sub == 'create_presentation':
        t = gestor_tareas.create_task('presentation', f'Presentación: {topic}', f'Preparando presentación sobre {topic}', params)
        gestor_tareas.run_presentation_task(t.id, topic)
        return {'ok': True, 'status': 'RUNNING', 'task_id': t.id,
                'message': f'Inicié la presentación sobre «{topic}» en segundo plano.'}
    if sub == 'append':
        mod = str(params.get('modification', ''))[:500]
        t = gestor_tareas.append_to_active_task(mod)
        if t:
            return {'ok': True, 'status': 'VERIFIED', 'task_id': t.id, 'message': f'Agregué a «{t.title}»: {mod}.'}
        return {'ok': False, 'status': 'FAILED', 'message': 'No hay una tarea activa a la que agregar eso.'}
    if sub == 'create_document':
        t = gestor_tareas.create_task('document', f'Documento: {topic}', f'Creando documento sobre {topic}', params)
        return {'ok': True, 'status': 'PENDING', 'task_id': t.id, 'message': f'Registré el documento sobre «{topic}» en tus tareas.'}
    raise ValueError('Subacción de tarea no autorizada.')


def execute_action(action: str, params: dict, politica: dict | None = None) -> dict:
    """Ejecuta sólo acciones del registro que el dueño activó, y las deja en el ledger verificable."""
    politica = politica or caps.cargar_politica()
    _validar(action, params, politica)
    if action in caps.ACCIONES_INTERFAZ:
        # No tocan el sistema operativo: no se informan como "VERIFIED".
        return {'ok': True, 'status': 'UI', 'message': str(params.get('message') or 'La interfaz de SKY aplica esta acción.')[:200]}
    if action in _AUTOREGISTRADAS or action == 'status':
        return _ejecutar(action, params, politica)
    rec = verificador_acciones.start_action(action, _detalle_seguro(action, params) or action)
    verificador_acciones.mark_running(rec.command_id)
    t0 = time.time()
    try:
        res = _ejecutar(action, params, politica)
    except Exception as exc:
        verificador_acciones.mark_failed(rec.command_id, str(exc)[:200], (time.time() - t0) * 1000)
        raise
    res.setdefault('command_id', rec.command_id)
    status = str(res.get('status', '')).upper()
    if res.get('ok') is True and status == 'VERIFIED':
        verificador_acciones.mark_verified(rec.command_id, {k: v for k, v in res.items() if k != 'text'}, (time.time() - t0) * 1000)
    elif res.get('ok') is True and status in ('SENT', 'RUNNING', 'PENDING', 'DISPATCHED'):
        verificador_acciones.mark_dispatched(rec.command_id, res, (time.time() - t0) * 1000)
    else:
        verificador_acciones.mark_failed(rec.command_id, str(res.get('message', ''))[:200], (time.time() - t0) * 1000)
    return res


BLOQUEADA = 'SKY está bloqueada: decí o escribí tu PIN para volver a usarla.'


def _sesion_bloqueada() -> bool:
    try:
        from neural_core.sentinel_identidad import sesion_bloqueada
        return sesion_bloqueada()
    except Exception:
        return True   # falla cerrado


def permitido_con_sesion(action: str, params: dict, origen: str, politica: dict | None = None) -> bool:
    """v12.6 — última barrera común a voz, HUD, WhatsApp, rutinas y Streamlit: con la sesión del dueño bloqueada,
    sólo pasan las tareas programadas que ya estaban autorizadas como automáticas y son de nivel 1 (avisos, música,
    volumen…). Lo demás espera al PIN. La política por herramienta no cambia al desbloquear."""
    if not _sesion_bloqueada():
        return True
    if origen != 'programada':
        return False
    politica = politica or caps.cargar_politica()
    return caps.nivel_riesgo(action, params) == 1 and not caps.requiere_confirmacion(action, params, politica)


class Handler(BaseHTTPRequestHandler):
    server_version = 'SKY-Desktop-Agent/' + VERSION

    def reply(self, status_code: int, body: dict):
        raw = json.dumps(body, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self) -> bool:
        header = self.headers.get('Authorization', '')
        expected = 'Bearer ' + self.server.secret
        return hmac.compare_digest(header.encode('utf-8'), expected.encode('utf-8'))

    def do_GET(self):
        if not self.authorized():
            return self.reply(401, {'ok': False, 'error': 'No autorizado'})
        split = urlsplit(self.path)
        query = parse_qs(split.query)
        if split.path == '/status':
            return self.reply(200, status())
        if _sesion_bloqueada():
            return self.reply(423, {'ok': False, 'error': BLOQUEADA})
        if split.path == '/verify_action':
            cid = query.get('command_id', [''])[0][:80]
            if not cid:
                return self.reply(400, {'ok': False, 'error': 'Parámetro command_id requerido.'})
            rec = verificador_acciones.get_action(cid)
            if not rec:
                return self.reply(404, {'ok': False, 'error': f'Acción {cid} no encontrada.'})
            # Read-only physical recheck for a previously dispatched app launch.
            # Never claim that RUNNING is VERIFIED without observed evidence.
            if rec.status == 'DISPATCHED' and rec.action == 'launch_app' and rec.target in AUTHORIZED_APPS:
                from neural_core.windows_controller import verify_window_or_process
                details = AUTHORIZED_APPS[rec.target]
                observation = verify_window_or_process(
                    details.get('window_titles', [rec.target]),
                    pid=rec.result.get('pid'), timeout_secs=1.0)
                if observation.get('verified'):
                    verificador_acciones.mark_verified(
                        cid, {'app': rec.target, 'status': 'VERIFIED',
                              'hwnd': observation.get('hwnd'),
                              'pid': rec.result.get('pid')}, rec.execution_time_ms)
            return self.reply(200, {'ok': True, 'record': rec.to_dict()})
        if split.path == '/actions_history':
            return self.reply(200, {'ok': True, 'actions': verificador_acciones.get_recent_actions(limit=30)})
        if split.path == '/tasks':
            from neural_core.task_manager import gestor_tareas
            return self.reply(200, {'ok': True, 'tasks': gestor_tareas.list_tasks(limit=12)})
        return self.reply(404, {'ok': False, 'error': 'Ruta desconocida'})

    def do_POST(self):
        if not self.authorized():
            return self.reply(401, {'ok': False, 'error': 'No autorizado'})
        if self.path != '/action':
            return self.reply(404, {'ok': False, 'error': 'Ruta desconocida'})
        action = '?'
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > MAX_BODY:
                return self.reply(413, {'ok': False, 'error': 'Tamaño inválido'})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Formato inválido')
            action = str(body.get('action', ''))[:40]
            params = body.get('params', {})
            if action not in caps.ACCION_A_CAPACIDAD and action not in caps.ACCIONES_INTERFAZ:
                raise ValueError(f"Acción '{action}' no permitida en esta versión.")
            if not permitido_con_sesion(action, params if isinstance(params, dict) else {},
                                        self.headers.get('X-SKY-ORIGEN', '')):
                audit(action, 'sesion_bloqueada')
                return self.reply(423, {'ok': False, 'error': BLOQUEADA})
            result = execute_action(action, params)
            audit(action, 'ok', _detalle_seguro(action, params if isinstance(params, dict) else {}))
            return self.reply(200, result)
        except Desactivada as exc:
            audit(action, 'desactivada')
            return self.reply(403, {'ok': False, 'error': str(exc)[:250]})
        except (ValueError, RuntimeError, PermissionError, OSError, subprocess.SubprocessError) as exc:
            known = action in caps.ACCION_A_CAPACIDAD or action in caps.ACCIONES_INTERFAZ
            audit(action if known else 'rejected', 'error')
            return self.reply(400, {'ok': False, 'error': str(exc)[:300]})

    def log_message(self, *args):
        pass  # no registrar el token; auditoría por acción


def configurar(args) -> bool:
    """Aplica cambios de política pedidos por CLI. Devuelve True si hubo cambios."""
    cambios = False
    if args.perfil:
        caps.aplicar_perfil(args.perfil, [str(Path(c).expanduser().resolve()) for c in args.carpeta] if args.carpeta else None)
        cambios = True
    pol = caps.cargar_politica_guardada()
    for nombre, lista, agregar in (('activar', args.activar, True), ('desactivar', args.desactivar, False),
                                   ('auto', args.auto, True)):
        if not lista:
            continue
        ids = [x.strip() for x in lista.split(',') if x.strip()]
        malos = [x for x in ids if x not in caps.CAPACIDADES]
        if malos:
            sys.exit('Capacidades desconocidas: ' + ', '.join(malos) + '. Disponibles: ' + ', '.join(caps.CAPACIDADES))
        clave = 'auto_confirm' if nombre == 'auto' else 'enabled'
        for cap in ids:
            if agregar and cap not in pol[clave]:
                pol[clave].append(cap)
            if not agregar:
                pol['enabled'] = [c for c in pol['enabled'] if c != cap]
                pol['auto_confirm'] = [c for c in pol['auto_confirm'] if c != cap]
        if nombre == 'auto':
            for cap in ids:
                if cap not in pol['enabled']:
                    pol['enabled'].append(cap)
        pol['perfil'] = 'personalizado'
        cambios = True
    if args.carpeta and not args.perfil:
        for c in args.carpeta:
            ruta = str(Path(c).expanduser().resolve())
            if not Path(ruta).is_dir():
                sys.exit('No existe la carpeta: ' + ruta)
            if ruta not in pol['allowed_folders']:
                pol['allowed_folders'].append(ruta)
        cambios = True
    if cambios and (args.activar or args.desactivar or args.auto or (args.carpeta and not args.perfil)):
        caps.guardar_politica(pol)
    return cambios


def imprimir_politica() -> None:
    pol = caps.cargar_politica()
    print(f'Perfil: {pol["perfil"]}   (archivo: {caps.POLICY_PATH})')
    for cap in caps.CAPACIDADES.values():
        on = '✔' if cap.id in pol['enabled'] else '·'
        auto = ' (sin confirmación)' if cap.id in pol['auto_confirm'] else ''
        print(f'  {on} {cap.id:<11} {cap.nombre} — {cap.descripcion}{auto}')
    print('Carpetas autorizadas:', ', '.join(pol['allowed_folders']) or 'ninguna')


def _enlazar(preferido: int) -> tuple[ThreadingHTTPServer, int]:
    for p in dict.fromkeys((preferido, 8766, 8767, 18765)):
        try:
            return ThreadingHTTPServer((LISTEN_ADDRESS, p), Handler), p
        except OSError:
            continue
    sys.exit(f'No se pudo enlazar ningún puerto local ({preferido}, 8766, 8767, 18765). '
             'Fijá otro con SKY_DEVICE_PORT y usá el mismo valor en SKY.')


def main(argv=None):
    p = argparse.ArgumentParser(description='SKY Desktop Agent ' + VERSION + ': vos autorizás qué controla SKY.')
    p.add_argument('--perfil', choices=list(caps.PERFILES), help='basico, multimedia o completo')
    p.add_argument('--activar', help='capacidades separadas por coma: ' + ','.join(caps.CAPACIDADES))
    p.add_argument('--desactivar', help='capacidades a desactivar, separadas por coma')
    p.add_argument('--auto', help='capacidades que SKY ejecuta sin pedir clic de confirmación')
    p.add_argument('--carpeta', action='append', help='carpeta autorizada para archivos (repetible)')
    p.add_argument('--ver-politica', action='store_true')
    p.add_argument('--solo-config', action='store_true', help='guardar la política sin iniciar el agente')
    p.add_argument('--mostrar-token', action='store_true', help='mostrar el token de emparejamiento en pantalla')
    args = p.parse_args(argv)
    cambios = configurar(args)
    if cambios or args.ver_politica:
        imprimir_politica()
    if args.solo_config or args.ver_politica:
        return
    secret = token_secret()
    server, port = _enlazar(PORT)
    server.secret = secret
    if port != PORT:
        print(f'[SKY] El puerto {PORT} estaba ocupado; usando {port}. Fijá SKY_DEVICE_PORT={port} en SKY.')
    print(f'{AGENT_NAME} {VERSION} activo en http://127.0.0.1:{port}')
    # v12.6: el token nunca va a los registros. Sólo se muestra en una consola interactiva o con --mostrar-token.
    if args.mostrar_token or (sys.stdout is not None and sys.stdout.isatty()):
        print('Token para emparejar (NO compartir):', secret)
    else:
        print('Token de emparejamiento oculto (está en ~/.neuralt/device_agent.token; usá --mostrar-token).')
    print('Capacidades activas:', ', '.join(caps.cargar_politica()['enabled']),
          '— cambiá con --perfil / --activar (ver --help)')
    print('Para acceso desde otro equipo, instalá Tailscale y usá: tailscale serve ' + str(port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
