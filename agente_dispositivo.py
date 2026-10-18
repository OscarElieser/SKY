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
from neural_core.dispositivos import APP_OPTIONS

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
    return {'ok':True,'device':platform.node() or 'Equipo local',
            'platform':platform.system(),'system_version':platform.release(),
            'capabilities':['status','open_url','launch_app'],
            'allowed_apps':APP_OPTIONS,
            'timestamp':datetime.now(timezone.utc).isoformat()}


def launch_app(app):
    if app not in APP_OPTIONS:
        raise ValueError('Esta aplicación no está permitida en el agente.')
    system=platform.system().lower()
    if system=='windows':
        mapping={'calculator':['calc.exe'],'text_editor':['notepad.exe'],
                 'file_manager':['explorer.exe'],'browser':['explorer.exe','https://www.google.com']}
        subprocess.Popen(mapping[app],shell=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    elif system=='darwin':
        mapping={'calculator':'Calculator','text_editor':'TextEdit','file_manager':'Finder','browser':'Safari'}
        subprocess.Popen(['open','-a',mapping[app]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
        mapping={'calculator':['gnome-calculator','kcalc','mate-calc','galculator'],
                 'text_editor':['gedit','kate','mousepad','xed'],
                 'file_manager':['nautilus','thunar','dolphin','nemo'],
                 'browser':['xdg-open']}
        if app=='browser':
            return webbrowser.open('https://www.google.com')
        success=False
        for cmd in mapping[app]:
            try:
                subprocess.Popen([cmd],shell=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                success=True; break
            except FileNotFoundError: continue
        if not success: raise RuntimeError('No hay una aplicación compatible instalada.')
    return True


def execute_action(action,params):
    """Never executes shell commands, scripts, downloads, arbitrary paths or payments."""
    if not isinstance(params,dict): raise ValueError('Parámetros inválidos.')
    if action=='status': return status()
    if action=='launch_app':
        app=params.get('app','')
        launch_app(app)
        return {'ok':True,'message':'Se solicitó abrir la aplicación '+app}
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
            if action not in ('status','launch_app','open_url'): raise ValueError('Acción no permitida')
            result=execute_action(action,body.get('params',{}))
            audit(action,'ok')
            return self.reply(200,result)
        except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
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
