"""BAQUEANO Control Center: lectura y propuestas GitHub; sin cambios directos a producción.

Los secretos permanecen en variables de entorno y nunca se envían a Gemini.
"""
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import quote
import base64
import json
import os
import re
import secrets
import difflib

SITIO = 'https://baqueanonicaragua.com/'
REPO = 'OscarElieser/APP-BAQUEANO'
GITHUB_API = 'https://api.github.com/repos/' + REPO
SUPABASE_VISTAS = ('destinations','businesses','places','public_ecosystem_metrics')
MAX_CONTENT = 220_000

class IntegracionError(RuntimeError):
    pass


def _json_api(url, token=None, method='GET', data=None, timeout=12):
    headers={'Accept':'application/vnd.github+json','User-Agent':'NeuralT-Personal/4.1'}
    if token:
        headers['Authorization']='Bearer '+token
    if data is not None:
        headers['Content-Type']='application/json'
    raw=json.dumps(data,ensure_ascii=False).encode('utf-8') if data is not None else None
    req=Request(url,data=raw,headers=headers,method=method)
    try:
        with urlopen(req,timeout=timeout) as r:
            return json.load(r)
    except HTTPError as exc:
        try: detail=json.loads(exc.read().decode('utf-8')).get('message','')
        except Exception: detail=''
        raise IntegracionError(f'API respondió HTTP {exc.code}: {detail[:260]}') from exc
    except (URLError,TimeoutError,ValueError,OSError) as exc:
        raise IntegracionError('No fue posible consultar el servicio externo.') from exc


def estado_web():
    """Verificación sólo HTTPS a un dominio fijo: no admite URLs arbitrarias."""
    req=Request(SITIO,headers={'User-Agent':'NeuralT-Monitor/4.1'},method='GET')
    try:
        with urlopen(req,timeout=12) as response:
            raw=response.read(256_000).decode('utf-8',errors='replace')
            return {'url': SITIO, 'http':response.status, 'titulo_detectado':'BAQUEANO' in raw.upper(),
                    'revisado_utc':datetime.now(timezone.utc).isoformat(timespec='seconds')}
    except HTTPError as exc:
        return {'url': SITIO,'http':exc.code,'titulo_detectado':False,'error':'Respuesta HTTP no satisfactoria'}
    except (URLError,TimeoutError,OSError) as exc:
        return {'url': SITIO,'http':None,'titulo_detectado':False,'error':type(exc).__name__}


def github_token():
    return os.getenv('BAQUEANO_GITHUB_TOKEN','').strip()


def resumen_repo():
    data=_json_api(GITHUB_API,token=github_token() or None)
    return {key:data.get(key) for key in ('full_name','default_branch','updated_at','pushed_at','open_issues_count','html_url')}


def listado_repo(carpeta=''):
    carpeta=carpeta.strip().strip('/')
    if carpeta and (not re.fullmatch(r'[\w./-]{1,180}',carpeta) or '..' in carpeta.split('/')):
        raise ValueError('Carpeta no válida')
    url=GITHUB_API+'/contents/'+quote(carpeta,safe='/') if carpeta else GITHUB_API+'/contents'
    data=_json_api(url,token=github_token() or None)
    if not isinstance(data,list):
        raise IntegracionError('La ruta no corresponde a un directorio')
    return [{'nombre':x.get('name'),'ruta':x.get('path'),'tipo':x.get('type')} for x in data[:200]]


def ruta_editable(ruta):
    """Permite sólo archivos de contenido, no configuraciones de despliegue ni secretos."""
    if not isinstance(ruta,str) or len(ruta)>190 or '\\' in ruta:
        return False
    p=ruta.strip('/')
    if p != ruta or '..' in p.split('/') or not re.fullmatch(r'[\w./-]+',p):
        return False
    if not p.startswith(('website/','web/','docs/')):
        return False
    if '/.' in p or p.endswith(('.env','.pem','.key','.p12','.yml','.yaml','.json','.lock','.php','.sh')):
        return False
    return p.endswith(('.html','.css','.js','.md','.txt','.svg'))


def leer_archivo(ruta):
    if not ruta_editable(ruta):
        raise ValueError('Para esta versión sólo se permiten archivos de contenido en web/, website/ o docs/.')
    data=_json_api(GITHUB_API+'/contents/'+quote(ruta,safe='/'),token=github_token() or None)
    if data.get('type')!='file' or data.get('size',0)>MAX_CONTENT:
        raise IntegracionError('Archivo inexistente o demasiado grande')
    if data.get('encoding')!='base64':
        raise IntegracionError('Codificación no compatible')
    try: contenido=base64.b64decode(data['content']).decode('utf-8')
    except (UnicodeDecodeError,ValueError,KeyError) as exc: raise IntegracionError('Archivo no es texto UTF-8') from exc
    return {'ruta':ruta,'contenido':contenido,'sha':data['sha'],'url':data.get('html_url','')}


def vista_diff(antes,despues,ruta):
    return '\n'.join(difflib.unified_diff(antes.splitlines(),despues.splitlines(),
                       fromfile='actual/'+ruta,tofile='propuesta/'+ruta,lineterm=''))


def propuesta_pr(ruta, nuevo, titulo, actual_sha, confirmacion):
    """Crear rama Y PR de revisión, NO actualiza main ni despliega producción.

    El texto revisado debe tener un SHA de archivo esperado para evitar sobrescribir versiones.
    """
    if confirmacion != 'CREAR PROPUESTA':
        raise PermissionError('Debes confirmar escribiendo CREAR PROPUESTA.')
    token=github_token()
    if not token:
        raise IntegracionError('Falta BAQUEANO_GITHUB_TOKEN con acceso al repositorio.')
    if not ruta_editable(ruta) or not isinstance(nuevo,str) or not (1<=len(nuevo.encode('utf-8'))<=MAX_CONTENT):
        raise ValueError('Ruta o contenido inválidos.')
    if not re.fullmatch(r'[a-f0-9]{40}',actual_sha):
        raise ValueError('SHA de archivo no válido.')
    if not (8<=len(titulo.strip())<=120):
        raise ValueError('Título no válido (8–120 caracteres).')
    repo=_json_api(GITHUB_API,token=token)
    base=repo.get('default_branch')
    if not base: raise IntegracionError('No se identificó la rama base')
    # Se comprueba el SHA antes de crear la rama. Si cambió, es necesario revisar otra vez.
    vigente=leer_archivo(ruta)
    if vigente['sha'] != actual_sha:
        raise IntegracionError('El archivo cambió desde tu última lectura. Actualiza la vista previa.')
    rama=f'neuralt/revision-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4)}'
    ref=_json_api(GITHUB_API+'/git/ref/heads/'+quote(base,safe=''),token=token)
    sha_base=ref['object']['sha']
    _json_api(GITHUB_API+'/git/refs',token=token,method='POST',data={'ref':'refs/heads/'+rama,'sha':sha_base})
    _json_api(GITHUB_API+'/contents/'+quote(ruta,safe='/'),token=token,method='PUT',data={
        'message':'NeuralT: '+titulo.strip(),'content':base64.b64encode(nuevo.encode('utf-8')).decode(),
        'sha':actual_sha,'branch':rama})
    pr=_json_api(GITHUB_API+'/pulls',token=token,method='POST',data={
        'title':titulo.strip(),'head':rama,'base':base,
        'body':'Propuesta creada desde NeuralT para revisión manual. No fusionar sin probar la web y comprobar las diferencias.'})
    return {'rama':rama,'pull_request':pr.get('html_url'),'numero':pr.get('number'),'publicado':False}


def supabase_publico(tabla,limite=15):
    """Lectura REST con clave PUBLICABLE: Supabase aplica permisos/RLS del rol anon."""
    if tabla not in SUPABASE_VISTAS:
        raise ValueError('Vista fuera del catálogo de lectura permitido.')
    url=os.getenv('BAQUEANO_SUPABASE_URL','').rstrip('/')
    key=os.getenv('BAQUEANO_SUPABASE_PUBLISHABLE_KEY','')
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',url) or not key:
        raise IntegracionError('Configura URL y clave publicable de Supabase en el archivo .env.')
    limite=max(1,min(int(limite),25))
    endpoint=f'{url}/rest/v1/{tabla}?select=*&limit={limite}'
    req=Request(endpoint,headers={'apikey':key, 'Accept':'application/json','User-Agent':'NeuralT-Personal/4.1'})
    try:
        with urlopen(req,timeout=12) as response:
            contenido=response.read(220_000)
            data=json.loads(contenido)
            if not isinstance(data,list): raise IntegracionError('Respuesta de tabla no es una lista')
            return data
    except HTTPError as exc:
        raise IntegracionError(f'La consulta fue denegada o la vista no existe (HTTP {exc.code}). Revisa RLS y permisos.') from exc
    except (URLError,OSError,ValueError) as exc:
        raise IntegracionError('No se pudo consultar Supabase.') from exc
