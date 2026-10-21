"""SKY Device Agent v4.3: control opt-in de funciones expresamente permitidas.

Ejecutar en una computadora tuya: python agente_dispositivo.py
Usar Tailscale Serve para control desde otros equipos; nunca abrir el puerto directamente.
"""
from __future__ import annotations
import hmac, json, os, platform, secrets, subprocess, sys, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
from neural_core.dispositivos import APP_OPTIONS, MEDIA_KEYS, WINDOW_SUBACTIONS
from neural_core.sky_notes_local import NOTE_ACTIONS, run_note_action
from neural_core.windows_controller import (
    launch_authorized_app, list_user_windows, focus_user_window,
    minimize_user_window, restore_user_window
)

CONFIG_DIR = Path.home() / '.neuralt'
TOKEN_PATH = CONFIG_DIR / 'device_agent.token'
AUDIT_PATH = CONFIG_DIR / 'device_agent_audit.jsonl'
PORT = int(os.getenv('SKY_DEVICE_PORT') or os.getenv('NEURALT_DEVICE_PORT','8765'))
LISTEN_ADDRESS = '127.0.0.1'  # No publicar HTTP sin TLS fuera de localhost


def token_secret():
    env=(os.getenv('SKY_DEVICE_TOKEN') or os.getenv('NEURALT_DEVICE_TOKEN','')).strip()
    if env: return env
    CONFIG_DIR.mkdir(mode=0o700,parents=True,exist_ok=True)
    if TOKEN_PATH.exists(): return TOKEN_PATH.read_text(encoding='utf-8').strip()
    key=secrets.token_urlsafe(36)
    try:
        with TOKEN_PATH.open('x',encoding='utf-8') as h: h.write(key+'\n')
        TOKEN_PATH.chmod(0o600)
    except FileExistsError:
        return TOKEN_PATH.read_text(encoding='utf-8').strip()
    return key


def audit(action, result):
    CONFIG_DIR.mkdir(mode=0o700,parents=True,exist_ok=True)
    with AUDIT_PATH.open('a',encoding='utf-8') as file:
        file.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'action':action,'result':result},ensure_ascii=False)+'\n')


def status():
    caps = ['status', 'open_url', 'launch_app', 'media_key']
    if os.getenv('SKY_WINDOW_ACTIONS') == '1':
        caps.append('window_action')
    if os.getenv('SKY_NOTES_ENABLED') == '1':
        caps.extend(sorted(NOTE_ACTIONS))
    return {'ok': True, 'device': platform.node() or 'Equipo local',
            'platform': platform.system(), 'system_version': platform.release(),
            'capabilities': caps,
            'allowed_apps': APP_OPTIONS,
            'timestamp': datetime.now(timezone.utc).isoformat()}


def launch_app(app):
    return launch_authorized_app(app)


def send_media_key(key: str) -> None:
    """Envía una tecla multimedia nativa. No simula que exista reproducción real."""
    if key not in MEDIA_KEYS:
        raise ValueError('Tecla multimedia no autorizada.')
    if platform.system().lower() != 'windows':
        raise RuntimeError('El control multimedia local requiere Windows en esta fase.')
    # Virtual-Key Codes públicos de Windows; sin PowerShell, shell ni inyección de texto.
    codes = {'play_pause':0xB3, 'next_track':0xB0, 'previous_track':0xB1,
             'volume_up':0xAF, 'volume_down':0xAE, 'mute':0xAD}
    import ctypes
    user32 = ctypes.windll.user32
    user32.keybd_event(codes[key], 0, 0, 0)
    user32.keybd_event(codes[key], 0, 0x0002, 0)


def execute_action(action,params):
    """Never executes shell commands, scripts, downloads, arbitrary paths or payments."""
    if not isinstance(params,dict): raise ValueError('Parámetros inválidos.')
    if action=='status': return status()
    if action=='launch_app':
        app=params.get('app','')
        res=launch_app(app)
        return res if isinstance(res, dict) else {'ok':True,'message':'Se solicitó abrir la aplicación '+app}
    if action=='window_action':
        subaction=params.get('subaction','list')
        if subaction not in WINDOW_SUBACTIONS:
            raise ValueError('Subacción de ventana no autorizada.')
        if subaction=='list':
            return {'ok':True,'windows':list_user_windows()}
        if subaction=='focus':
            return focus_user_window(params.get('target',''))
        if subaction=='minimize':
            return minimize_user_window(params.get('target'))
        if subaction=='restore':
            return restore_user_window(params.get('target'))
    if action in NOTE_ACTIONS:
        return run_note_action(action, params)
    if action=='media_key':
        key=params.get('key')
        send_media_key(key)
        return {'ok':True,'message':'Tecla multimedia enviada; estado del reproductor no verificable.'}
    if action=='open_url':
        url=str(params.get('url',''))
        p=urlsplit(url)
        if p.scheme!='https' or not p.hostname or p.username or p.password or len(url)>2000:
            raise ValueError('Sólo se admiten páginas HTTPS normales.')
        opened=webbrowser.open(url,new=2)
        return {'ok':bool(opened),'message':'Se solicitó abrir la página en el navegador.'}
    raise ValueError('Acción no permitida.')


class Handler(BaseHTTPRequestHandler):
    server_version='SKY-Device-Agent/4.3'
    def reply(self,status_code,body):
        raw=json.dumps(body,ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(raw)
    def authorized(self):
        header=self.headers.get('Authorization','')
        expected='Bearer '+self.server.secret
        return hmac.compare_digest(header, expected)
    def do_GET(self):
        if not self.authorized(): return self.reply(401,{'ok':False,'error':'No autorizado'})
        if self.path=='/status': return self.reply(200,status())
        return self.reply(404,{'ok':False,'error':'Ruta desconocida'})
    def do_POST(self):
        if not self.authorized(): return self.reply(401,{'ok':False,'error':'No autorizado'})
        if self.path!='/action': return self.reply(404,{'ok':False,'error':'Ruta desconocida'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>8192: return self.reply(413,{'ok':False,'error':'Tamaño inválido'})
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict): raise ValueError('Formato inválido')
            action=body.get('action','')
            if action not in ('status','launch_app','open_url','media_key',*NOTE_ACTIONS): raise ValueError('Acción no permitida')
            result=execute_action(action,body.get('params',{}))
            audit(action,'ok')
            return self.reply(200,result)
        except (ValueError,RuntimeError,PermissionError,OSError,subprocess.SubprocessError) as exc:
            audit('rejected','error')
            return self.reply(400,{'ok':False,'error':str(exc)[:250]})
    def log_message(self,*args): pass  # no registrar el token; auditoría por acción


def main():
    secret=token_secret()
    server=ThreadingHTTPServer((LISTEN_ADDRESS,PORT),Handler)
    server.secret=secret
    print(f'SKY Device Agent activo en http://127.0.0.1:{PORT}')
    print('Token para emparejar (NO compartir):', secret)
    print('Para acceso desde otro equipo, instala Tailscale y utiliza: tailscale serve '+str(PORT))
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
