"""SKY Device Agent v5.0 — el brazo del Asistente Personal SKY en tu equipo.

Ejecutar en una computadora tuya:  python agente_dispositivo.py
Usar Tailscale Serve para control desde otros equipos; nunca abrir el puerto directamente.

Vos decidís qué puede hacer SKY (la política vive sólo en este equipo):
    python agente_dispositivo.py --perfil multimedia          # música, volumen, apps, avisos
    python agente_dispositivo.py --perfil completo --carpeta ~/Música --carpeta ~/Documentos
    python agente_dispositivo.py --activar clipboard,screenshot
    python agente_dispositivo.py --ver-politica

Capacidades: estado, abrir webs, apps (Spotify, VLC, Office, WhatsApp…), control
multimedia, volumen, reproducir en YouTube/Spotify o archivos locales, notificaciones,
archivos en carpetas autorizadas, capturas, portapapeles y bloqueo de pantalla.
Nunca: comandos de shell arbitrarios, abrir ejecutables/scripts, descargas ni pagos.
"""
from __future__ import annotations
import argparse, hmac, json, os, platform, secrets, subprocess, sys, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime, timezone
from neural_core.dispositivos import APP_OPTIONS
from neural_core import sky_capacidades as caps

CONFIG_DIR = Path.home() / '.neuralt'
TOKEN_PATH = CONFIG_DIR / 'device_agent.token'
AUDIT_PATH = CONFIG_DIR / 'device_agent_audit.jsonl'
# 8766 por defecto: la API de SKY usa 8765 y ambos deben poder correr juntos.
PORT = int(os.getenv('SKY_DEVICE_PORT') or os.getenv('NEURALT_DEVICE_PORT','8766'))
LISTEN_ADDRESS = '127.0.0.1'  # No publicar HTTP sin TLS fuera de localhost
MAX_BODY = 32_768
VERSION = '5.0'


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


def audit(action, result, detail=''):
    """Registro local por acción. Nunca guarda el token ni el texto del portapapeles."""
    try:
        CONFIG_DIR.mkdir(mode=0o700,parents=True,exist_ok=True)
        with AUDIT_PATH.open('a',encoding='utf-8') as file:
            file.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'action':action,
                                   'result':result,'detail':str(detail)[:120]},ensure_ascii=False)+'\n')
    except OSError:
        pass


def _detalle_seguro(action, params):
    if action=='launch_app': return params.get('app','')
    if action in ('media_control','volume'): return params.get('command','')
    if action=='play_media': return params.get('service','archivo' if params.get('path') else '')
    return ''


def status(politica=None):
    politica=politica or caps.cargar_politica()
    return {'ok':True,'device':platform.node() or 'Equipo local','agent_version':VERSION,
            'platform':platform.system(),'system_version':platform.release(),
            'capabilities':caps.acciones_habilitadas(politica),
            'profile':politica['perfil'],
            'enabled':politica['enabled'],
            'auto_confirm':politica['auto_confirm'],
            'allowed_apps':caps.apps_disponibles(politica),
            'allowed_folders':len(politica['allowed_folders']),
            'system':caps.info_sistema(),
            'timestamp':datetime.now(timezone.utc).isoformat()}


def launch_app(app, politica=None):
    politica=politica or caps.cargar_politica()
    if app not in APP_OPTIONS:
        if app in caps.CATALOGO_APPS or app in politica.get('custom_apps',{}):
            if 'apps_extra' not in politica['enabled']:
                raise ValueError('Activá la capacidad apps_extra para abrir '+app+'.')
            return caps.abrir_app(app,politica)
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
            webbrowser.open('https://www.google.com')
            return app
        success=False
        for cmd in mapping[app]:
            try:
                subprocess.Popen([cmd],shell=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                success=True; break
            except FileNotFoundError: continue
        if not success: raise RuntimeError('No hay una aplicación compatible instalada.')
    return app


class Desactivada(ValueError):
    """La capacidad existe pero el dueño no la activó en su política."""


def execute_action(action,params,politica=None):
    """Ejecuta sólo acciones del registro que el dueño activó.
    Nunca ejecuta comandos de shell, scripts, descargas, rutas fuera de lo autorizado ni pagos."""
    if not isinstance(params,dict): raise ValueError('Parámetros inválidos.')
    if action not in caps.ACCION_A_CAPACIDAD: raise ValueError('Acción no permitida.')
    politica=politica or caps.cargar_politica()
    if action=='launch_app':
        app=str(params.get('app',''))[:40]
        if app not in APP_OPTIONS and app not in caps.CATALOGO_APPS and app not in politica.get('custom_apps',{}):
            raise ValueError('Esta aplicación no está permitida en el agente.')
    if not caps.accion_habilitada(action,politica,params):
        cap='apps_extra' if action=='launch_app' else caps.capacidad_de(action)
        raise Desactivada(f'La capacidad "{cap}" está desactivada. Activala en tu equipo con: '
                          f'python agente_dispositivo.py --activar {cap}')
    if action=='status': return status(politica)
    if action=='launch_app':
        nombre=launch_app(str(params.get('app','')),politica)
        return {'ok':True,'message':'Se solicitó abrir la aplicación '+str(nombre)}
    if action=='open_url':
        url=caps.validar_url_https(params.get('url',''))
        opened=webbrowser.open(url,new=2)
        return {'ok':bool(opened),'message':'Se solicitó abrir la página en el navegador.'}
    if action=='media_control':
        caps.control_multimedia(str(params.get('command','')))
        return {'ok':True,'message':'Control multimedia: '+params['command']}
    if action=='volume':
        nivel=params.get('level')
        if nivel is not None:
            try: nivel=int(nivel)
            except (TypeError,ValueError): raise ValueError('Nivel de volumen inválido.')
        r=caps.volumen(str(params.get('command','')),nivel)
        return {'ok':True,'message':'Volumen: '+r}
    if action=='play_media':
        if params.get('path'):
            ruta=caps.abrir_ruta(str(params['path']),politica,solo_media=True)
            return {'ok':True,'message':'Reproduciendo '+Path(ruta).name}
        url=caps.url_busqueda_media(params.get('query',''),str(params.get('service','youtube')))
        webbrowser.open(url,new=2)
        servicio={'youtube':'YouTube','youtube_music':'YouTube Music','spotify':'Spotify'}[str(params.get('service','youtube'))]
        return {'ok':True,'message':'Abriendo '+servicio+': '+str(params.get('query',''))[:80],'url':url}
    if action=='notify':
        caps.notificar(params.get('title','SKY'),params.get('message',''))
        return {'ok':True,'message':'Notificación mostrada.'}
    if action=='open_path':
        ruta=caps.abrir_ruta(str(params.get('path','')),politica)
        return {'ok':True,'message':'Abriendo '+Path(ruta).name}
    if action=='list_path':
        return {'ok':True,**caps.listar_ruta(str(params.get('path','')),politica)}
    if action=='screenshot':
        return {'ok':True,'message':'Captura guardada.',**caps.captura_pantalla()}
    if action=='clipboard_get':
        return {'ok':True,'text':caps.portapapeles_leer()}
    if action=='clipboard_set':
        n=caps.portapapeles_escribir(params.get('text',''))
        return {'ok':True,'message':f'Copiados {n} caracteres al portapapeles.'}
    if action=='lock_screen':
        caps.bloquear_pantalla()
        return {'ok':True,'message':'Equipo bloqueado.'}
    raise ValueError('Acción no permitida.')


class Handler(BaseHTTPRequestHandler):
    server_version='SKY-Device-Agent/'+VERSION
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
        return hmac.compare_digest(header.encode('utf-8'), expected.encode('utf-8'))
    def do_GET(self):
        if not self.authorized(): return self.reply(401,{'ok':False,'error':'No autorizado'})
        if self.path=='/status': return self.reply(200,status())
        return self.reply(404,{'ok':False,'error':'Ruta desconocida'})
    def do_POST(self):
        if not self.authorized(): return self.reply(401,{'ok':False,'error':'No autorizado'})
        if self.path!='/action': return self.reply(404,{'ok':False,'error':'Ruta desconocida'})
        action='?'
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>MAX_BODY: return self.reply(413,{'ok':False,'error':'Tamaño inválido'})
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict): raise ValueError('Formato inválido')
            action=str(body.get('action',''))[:40]
            params=body.get('params',{})
            if action not in caps.ACCION_A_CAPACIDAD: raise ValueError('Acción no permitida')
            result=execute_action(action,params)
            audit(action,'ok',_detalle_seguro(action,params if isinstance(params,dict) else {}))
            return self.reply(200,result)
        except Desactivada as exc:
            audit(action,'desactivada')
            return self.reply(403,{'ok':False,'error':str(exc)[:250]})
        except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
            audit('rejected' if action not in caps.ACCION_A_CAPACIDAD else action,'error')
            return self.reply(400,{'ok':False,'error':str(exc)[:250]})
    def log_message(self,*args): pass  # no registrar el token; auditoría por acción


def configurar(args) -> bool:
    """Aplica cambios de política pedidos por CLI. Devuelve True si hubo cambios."""
    cambios=False
    if args.perfil:
        caps.aplicar_perfil(args.perfil,[str(Path(c).expanduser()) for c in args.carpeta] if args.carpeta else None)
        cambios=True
    pol=caps.cargar_politica()
    for nombre,lista,agregar in (('activar',args.activar,True),('desactivar',args.desactivar,False),
                                 ('auto',args.auto,True)):
        if not lista: continue
        ids=[x.strip() for x in lista.split(',') if x.strip()]
        malos=[x for x in ids if x not in caps.CAPACIDADES]
        if malos: sys.exit('Capacidades desconocidas: '+', '.join(malos)+'. Disponibles: '+', '.join(caps.CAPACIDADES))
        clave='auto_confirm' if nombre=='auto' else 'enabled'
        for cap in ids:
            if agregar and cap not in pol[clave]: pol[clave].append(cap)
            if not agregar:
                pol['enabled']=[c for c in pol['enabled'] if c!=cap]
                pol['auto_confirm']=[c for c in pol['auto_confirm'] if c!=cap]
        if nombre=='auto':
            for cap in ids:
                if cap not in pol['enabled']: pol['enabled'].append(cap)
        pol['perfil']='personalizado'; cambios=True
    if args.carpeta and not args.perfil:
        for c in args.carpeta:
            ruta=str(Path(c).expanduser().resolve())
            if not Path(ruta).is_dir(): sys.exit('No existe la carpeta: '+ruta)
            if ruta not in pol['allowed_folders']: pol['allowed_folders'].append(ruta)
        cambios=True
    if cambios and not args.perfil: caps.guardar_politica(pol)
    return cambios


def imprimir_politica():
    pol=caps.cargar_politica()
    print(f'Perfil: {pol["perfil"]}   (archivo: {caps.POLICY_PATH})')
    for cap in caps.CAPACIDADES.values():
        on='✔' if cap.id in pol['enabled'] else '·'
        auto=' (sin confirmación)' if cap.id in pol['auto_confirm'] else ''
        print(f'  {on} {cap.id:<11} {cap.nombre} — {cap.descripcion}{auto}')
    print('Carpetas autorizadas:',', '.join(pol['allowed_folders']) or 'ninguna')


def main(argv=None):
    p=argparse.ArgumentParser(description='SKY Device Agent '+VERSION+': vos autorizás qué controla SKY.')
    p.add_argument('--perfil',choices=list(caps.PERFILES),help='basico, multimedia o completo')
    p.add_argument('--activar',help='capacidades separadas por coma: '+','.join(caps.CAPACIDADES))
    p.add_argument('--desactivar',help='capacidades a desactivar, separadas por coma')
    p.add_argument('--auto',help='capacidades que SKY ejecuta sin pedir clic de confirmación')
    p.add_argument('--carpeta',action='append',help='carpeta autorizada para archivos (repetible)')
    p.add_argument('--ver-politica',action='store_true')
    p.add_argument('--solo-config',action='store_true',help='guardar la política sin iniciar el agente')
    args=p.parse_args(argv)
    cambios=configurar(args)
    if cambios or args.ver_politica: imprimir_politica()
    if args.solo_config or args.ver_politica: return
    secret=token_secret()
    server=ThreadingHTTPServer((LISTEN_ADDRESS,PORT),Handler)
    server.secret=secret
    print(f'SKY Device Agent {VERSION} activo en http://127.0.0.1:{PORT}')
    print('Token para emparejar (NO compartir):', secret)
    print('Capacidades activas:', ', '.join(caps.cargar_politica()['enabled']),
          '— cambiá con --perfil / --activar (ver --help)')
    print('Para acceso desde otro equipo, instala Tailscale y utiliza: tailscale serve '+str(PORT))
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
