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
}
APP_OPTIONS = ['calculator', 'text_editor', 'file_manager', 'browser']
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
    """Propose only, never execute: returns action/params or None for chat."""
    clean=norm(text.strip())
    if not clean: return None
    if re.search(r'\b(estado|informacion|informacion del|diagnostico|como esta)\b.*\b(equipo|pc|computadora|ordenador|dispositivo)\b',clean):
        return {'action':'status','params':{},'description':'Consultar estado del equipo'}
    if re.search(r'\b(abre|abri|abrir|inicia|iniciar|ejecuta|ejecutar)\b',clean):
        for term,app in [('calculadora','calculator'),('bloc de notas','text_editor'),('editor de texto','text_editor'),('archivos','file_manager'),('explorador de archivos','file_manager')]:
            if term in clean: return {'action':'launch_app','params':{'app':app},'description':f'Abrir {term}'}
        sites={'youtube':'https://www.youtube.com','google':'https://www.google.com',
               'baqueano':'https://baqueanonicaragua.com','wikipedia':'https://www.wikipedia.org'}
        for term,url in sites.items():
            if term in clean:
                return {'action':'open_url','params':{'url':url},'description':f'Abrir {url}'}
        m=re.search(r'https?://[^\s,;]+',text,re.I)
        if m:
            return {'action':'open_url','params':{'url':m.group(0)},'description':'Abrir URL indicada'}
    return None
