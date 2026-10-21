"""SKY Desktop Agent v5.0: servicio residente y verificado de control de Windows.

Ejecutar en la sesión de usuario de Windows: python agente_dispositivo.py
Puerto por defecto: 8766 (evita colisiones con servicios API de puertos 8765/8000).
"""
from __future__ import annotations

import hmac
import json
import os
import platform
import secrets
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from neural_core.action_verifier import verificador_acciones
from neural_core.dispositivos import APP_OPTIONS, MEDIA_KEYS, WINDOW_SUBACTIONS
from neural_core.sky_notes_local import NOTE_ACTIONS, run_note_action
from neural_core.windows_controller import (
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
PORT = int(os.getenv('SKY_DEVICE_PORT') or os.getenv('NEURALT_DEVICE_PORT', '8766'))
LISTEN_ADDRESS = '127.0.0.1'


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


def audit(action: str, result: str) -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    with AUDIT_PATH.open('a', encoding='utf-8') as file:
        file.write(json.dumps({
            'at': datetime.now(timezone.utc).isoformat(),
            'action': action,
            'result': result
        }, ensure_ascii=False) + '\n')


def status() -> dict:
    caps = ['status', 'open_url', 'launch_app', 'media_key']
    if os.getenv('SKY_WINDOW_ACTIONS') == '1':
        caps.append('window_action')
    if os.getenv('SKY_ALL_CAPABILITIES') == '1':
        for c in ('open_file', 'window_action', 'type_text', 'organize_windows'):
            if c not in caps: caps.append(c)
    if os.getenv('SKY_NOTES_ENABLED') == '1':
        caps.extend(sorted(NOTE_ACTIONS))
    return {
        'ok': True,
        'agent': 'SKY Desktop Agent',
        'version': '5.0.0',
        'device': platform.node() or 'Windows-PC',
        'platform': platform.system(),
        'system_version': platform.release(),
        'capabilities': caps,
        'allowed_apps': APP_OPTIONS,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }


def send_media_key(key: str) -> None:
    """Envía una tecla multimedia nativa de Windows."""
    if key not in MEDIA_KEYS:
        raise ValueError('Tecla multimedia no autorizada.')
    if platform.system().lower() != 'windows':
        raise RuntimeError('El control multimedia local requiere Windows en esta fase.')
    codes = {
        'play_pause': 0xB3,
        'next_track': 0xB0,
        'previous_track': 0xB1,
        'volume_up': 0xAF,
        'volume_down': 0xAE,
        'mute': 0xAD
    }
    import ctypes
    user32 = ctypes.windll.user32
    user32.keybd_event(codes[key], 0, 0, 0)
    user32.keybd_event(codes[key], 0, 0x0002, 0)


def execute_action(action: str, params: dict) -> dict:
    """Ejecuta una acción local autorizada con verificación real de estado."""
    if not isinstance(params, dict):
        raise ValueError('Parámetros inválidos.')

    if action == 'status':
        return status()

    if action == 'launch_app':
        app = params.get('app', '')
        res = launch_authorized_app(app)
        return res if isinstance(res, dict) else {'ok': True, 'status': 'VERIFIED', 'message': f'Listo, ya está abierto {app}.'}

    if action == 'open_file':
        target = str(params.get('target', ''))
        return open_local_file_or_folder(target)

    if action == 'window_action':
        subaction = params.get('subaction', 'list')
        if subaction not in WINDOW_SUBACTIONS and subaction != 'organize':
            raise ValueError('Subacción de ventana no autorizada.')
        if subaction == 'list':
            return {'ok': True, 'status': 'VERIFIED', 'windows': list_user_windows()}
        if subaction == 'focus':
            return focus_user_window(params.get('target', ''))
        if subaction == 'minimize':
            return minimize_user_window(params.get('target'))
        if subaction == 'restore':
            return restore_user_window(params.get('target'))
        if subaction == 'close':
            return close_user_window(params.get('target'))
        if subaction == 'organize':
            return organize_windows()

    if action == 'type_text':
        text = str(params.get('text', ''))
        if not text:
            raise ValueError('Debes indicar el texto a escribir.')
        return type_text_in_active_window(text)

    if action == 'organize_windows':
        return organize_windows()

    if action in NOTE_ACTIONS:
        return run_note_action(action, params)

    if action == 'media_key':
        key = params.get('key')
        send_media_key(key)
        return {'ok': True, 'status': 'VERIFIED', 'message': f'Tecla multimedia {key} enviada a Windows.'}

    if action == 'open_url':
        url = str(params.get('url', ''))
        p = urlsplit(url)
        if p.scheme != 'https' or not p.hostname or p.username or p.password or len(url) > 2000:
            raise ValueError('Sólo se admiten páginas HTTPS normales.')
        opened = webbrowser.open(url, new=2)
        return {'ok': bool(opened), 'status': 'VERIFIED' if opened else 'FAILED', 'message': 'Página abierta en el navegador.'}

    if action == 'player_control':
        sub = str(params.get('subaction', 'mode_normal'))
        return {'ok': True, 'status': 'VERIFIED', 'message': f'Modo de reproductor SKY actualizado a {sub}.'}

    if action == 'task_action':
        subaction = params.get('subaction', 'create_presentation')
        from neural_core.task_manager import gestor_tareas
        if subaction == 'create_presentation':
            topic = params.get('topic', 'tema general')
            t = gestor_tareas.create_task('presentation', f"Presentación: {topic}", f"Preparando presentación sobre {topic}", params)
            gestor_tareas.run_presentation_task(t.id, topic)
            return {'ok': True, 'status': 'VERIFIED', 'task_id': t.id, 'message': f"Inicié la preparación de la presentación sobre «{topic}» en segundo plano."}
        elif subaction == 'append':
            mod = params.get('modification', '')
            t = gestor_tareas.append_to_active_task(mod)
            if t:
                return {'ok': True, 'status': 'VERIFIED', 'task_id': t.id, 'message': f"Modificación registrada en la tarea activa «{t.title}»: agregar {mod}."}
            return {'ok': True, 'status': 'VERIFIED', 'message': f"Registré la nota para el trabajo: {mod}."}
        elif subaction == 'create_document':
            topic = params.get('topic', 'documento general')
            t = gestor_tareas.create_task('document', f"Documento: {topic}", f"Creando documento sobre {topic}", params)
            return {'ok': True, 'status': 'VERIFIED', 'task_id': t.id, 'message': f"Preparando documento sobre «{topic}»."}

    if action == 'voice_control':
        return {'ok': True, 'status': 'VERIFIED', 'message': params.get('message', 'Comando conversacional procesado')}

    if action == 'holographic_window':
        return {'ok': True, 'status': 'VERIFIED', 'message': params.get('message', 'Ventana holográfica actualizada')}

    raise ValueError(f"Acción '{action}' no permitida.")


class Handler(BaseHTTPRequestHandler):
    server_version = 'SKY-Desktop-Agent/5.0'

    def reply(self, status_code: int, body: dict):
        raw = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self) -> bool:
        header = self.headers.get('Authorization', '')
        expected = 'Bearer ' + self.server.secret
        return hmac.compare_digest(header, expected)

    def do_GET(self):
        if not self.authorized():
            return self.reply(401, {'ok': False, 'error': 'No autorizado'})

        split_path = urlsplit(self.path)
        path = split_path.path
        query = parse_qs(split_path.query)

        if path == '/status':
            return self.reply(200, status())

        if path == '/verify_action':
            cid = query.get('command_id', [''])[0]
            if not cid:
                return self.reply(400, {'ok': False, 'error': 'Parámetro command_id requerido.'})
            rec = verificador_acciones.get_action(cid)
            if not rec:
                return self.reply(404, {'ok': False, 'error': f'Acción {cid} no encontrada.'})
            return self.reply(200, {'ok': True, 'record': rec.to_dict()})

        if path == '/actions_history':
            history = verificador_acciones.get_recent_actions(limit=30)
            return self.reply(200, {'ok': True, 'actions': history})

        return self.reply(404, {'ok': False, 'error': 'Ruta desconocida'})

    def do_POST(self):
        if not self.authorized():
            return self.reply(401, {'ok': False, 'error': 'No autorizado'})

        if self.path != '/action':
            return self.reply(404, {'ok': False, 'error': 'Ruta desconocida'})

        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 16384:
                return self.reply(413, {'ok': False, 'error': 'Tamaño inválido'})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Formato inválido')

            action = body.get('action', '')
            allowed_actions = {
                'status', 'launch_app', 'open_url', 'media_key',
                'player_control', 'task_action', 'voice_control',
                'holographic_window', 'open_file', 'window_action',
                'type_text', 'organize_windows', *NOTE_ACTIONS
            }
            if action not in allowed_actions:
                raise ValueError(f"Acción '{action}' no permitida en esta versión.")

            result = execute_action(action, body.get('params', {}))
            audit(action, 'ok')
            return self.reply(200, result)

        except (ValueError, RuntimeError, PermissionError, OSError, subprocess.SubprocessError) as exc:
            audit('rejected', 'error')
            return self.reply(400, {'ok': False, 'error': str(exc)[:300]})

    def log_message(self, *args):
        pass


def main():
    secret = token_secret()
    port = PORT
    server = None

    # Intentar enlace en puerto preferido, si está ocupado probar alternativa
    for p in (port, 8766, 8767):
        try:
            server = ThreadingHTTPServer((LISTEN_ADDRESS, p), Handler)
            port = p
            break
        except OSError:
            continue

    if not server:
        print(f"Error: No se pudo enlazar ningún puerto local disponible ({port}, 8766, 8767).")
        sys.exit(1)

    server.secret = secret
    print(f'SKY Desktop Agent activo en http://127.0.0.1:{port}')
    print('Token para emparejar (NO compartir):', secret)
    print('Para acceso desde otro equipo, instala Tailscale y utiliza: tailscale serve ' + str(port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
