"""Hermes Agent (Nous Research) como CONSULTOR de SKY — v12.6.

Hermes piensa, investiga y planifica; SKY ejecuta con su propia identidad, PIN, permisos y agente. Hermes corre
aparte (`hermes gateway` con su API compatible con OpenAI en 127.0.0.1:8642) y SKY sólo le hace preguntas.

Controles, todos en código (no dependen de que el modelo obedezca):
  * Destino fijo de loopback (127.0.0.1), sin redirecciones ni proxies, con la clave API_SERVER_KEY de Hermes.
  * Antes de cada consulta SKY lee `GET /v1/toolsets` y se NIEGA si Hermes tiene activa cualquier herramienta que
    actúe sobre tu equipo o el mundo (terminal, archivos, ejecución de código, navegador, uso de la computadora,
    delegación, tareas programadas, mensajería…). Sólo se aceptan las de la lista SEGURAS.
  * Comprueba en la configuración de Hermes que la plataforma API no cargue servidores MCP (`no_mcp`): la API de
    herramientas de Hermes no los muestra, así que se verifica en su config.yaml. Si no se puede leer, no consulta.
  * Con SKY_LOCAL_ONLY=1 sólo consulta si Hermes usa un modelo local (base_url en loopback).
  * Lo que responde Hermes es TEXTO para vos: SKY nunca ejecuta acciones a partir de esa respuesta.
  * Sólo se envía tu pregunta (no tu memoria, perfil, PIN ni historial de SKY).
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import time
from pathlib import Path
from urllib import error, request
from urllib.parse import urlparse

PUERTO_DEFECTO = 8642
SEGURAS = frozenset({'web', 'vision', 'video', 'skills', 'todo', 'memory', 'session_search', 'clarify',
                     'context_engine', 'x_search', 'tts', 'stt'})
PROVEEDORES_LOCALES = frozenset({'custom', 'ollama', 'lmstudio', 'vllm', 'llamacpp'})
SISTEMA = ('Actuás como CONSULTOR de SKY, el asistente personal de su dueño. No ejecutes acciones ni cambies nada: '
           'investigá, analizá y respondé en español con conclusiones, fuentes cuando las uses y, si corresponde, '
           'pasos sugeridos para que el dueño decida. Si algo requiere actuar, decilo como recomendación.')
MAX_PREGUNTA = 4000
MAX_RESPUESTA = 12000


class HermesNoDisponible(RuntimeError):
    """Falta configuración, Hermes no responde o su configuración no es segura para consultar."""


class _SinRedireccion(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ABRIDOR = request.build_opener(request.ProxyHandler({}), _SinRedireccion())


def habilitado() -> bool:
    return os.getenv('SKY_HERMES_ENABLED', '0').strip().lower() in ('1', 'true', 'si', 'sí', 'yes')


def _clave() -> str:
    clave = os.getenv('SKY_HERMES_KEY', '').strip()
    ruta = os.getenv('SKY_HERMES_KEY_FILE', '').strip()
    if not clave and ruta:
        try:
            clave = Path(ruta).expanduser().read_text(encoding='utf-8').strip()
        except OSError:
            clave = ''
    return clave


def _base() -> str:
    try:
        puerto = int(os.getenv('SKY_HERMES_PORT', str(PUERTO_DEFECTO)))
    except ValueError:
        puerto = PUERTO_DEFECTO
    if not 1024 <= puerto <= 65535:
        puerto = PUERTO_DEFECTO
    return f'http://127.0.0.1:{puerto}'   # nunca un host configurable


def _pedir(metodo: str, ruta: str, cuerpo: dict | None = None, timeout: float = 5.0) -> tuple[int, dict]:
    datos = None if cuerpo is None else json.dumps(cuerpo, ensure_ascii=False).encode('utf-8')
    req = request.Request(_base() + ruta, data=datos, method=metodo,
                          headers={'Authorization': 'Bearer ' + _clave(), 'Content-Type': 'application/json',
                                   'X-Hermes-Session-Key': 'sky-consultor'})
    try:
        with _ABRIDOR.open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read(2_000_000).decode('utf-8', 'replace') or '{}')
    except error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read(20_000).decode('utf-8', 'replace') or '{}')
        except Exception:
            return exc.code, {}


# ------------------------------------------------------------------ configuración local de Hermes

def hermes_home() -> Path:
    propio = os.getenv('HERMES_HOME', '').strip()
    if propio:
        return Path(os.path.expandvars(os.path.expanduser(propio)))
    if os.name == 'nt':
        base = os.getenv('LOCALAPPDATA', '').strip()
        return (Path(base) if base else Path.home() / 'AppData' / 'Local') / 'hermes'
    return Path.home() / '.hermes'


def _config() -> dict | None:
    try:
        import yaml
        datos = yaml.safe_load((hermes_home() / 'config.yaml').read_text(encoding='utf-8'))
        return datos if isinstance(datos, dict) else {}
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _sin_mcp(config: dict) -> bool:
    lista = (config.get('platform_toolsets') or {}).get('api_server')
    if isinstance(lista, str) and lista.strip().startswith('['):
        # `hermes config set` puede guardar la lista como texto: se lee igual que Hermes (literal de Python).
        import ast
        try:
            lista = ast.literal_eval(lista.strip())
        except (ValueError, SyntaxError):
            lista = None
    if isinstance(lista, list) and 'no_mcp' in [str(x) for x in lista]:
        return True
    servidores = config.get('mcp_servers')
    return not servidores   # sin servidores MCP configurados no hay nada que cargar


def _modelo_local(config: dict) -> bool:
    modelo = config.get('model') or {}
    if not isinstance(modelo, dict):
        return False
    proveedor = str(modelo.get('provider', '')).strip().lower()
    base_url = str(modelo.get('base_url', '')).strip()
    if proveedor == 'lmstudio' and not base_url:
        return True
    if proveedor not in PROVEEDORES_LOCALES or not base_url:
        return False
    host = (urlparse(base_url).hostname or '').lower()
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


# ------------------------------------------------------------------ comprobaciones

def herramientas_peligrosas(toolsets: list[dict]) -> list[str]:
    return sorted(str(t.get('name')) for t in toolsets if t.get('enabled') and str(t.get('name')) not in SEGURAS)


def requisitos(probar_red: bool = True) -> list[str]:
    """Qué falta exactamente para consultar a Hermes de forma segura (lista vacía = listo)."""
    falta = []
    if not habilitado():
        falta.append('SKY_HERMES_ENABLED=1 en .env')
    if len(_clave()) < 16:
        falta.append('SKY_HERMES_KEY en .env (la misma API_SERVER_KEY de Hermes, 16 caracteres o más)')
    config = _config()
    if config is None:
        falta.append(f'configuración de Hermes legible en {hermes_home() / "config.yaml"} (o HERMES_HOME)')
    else:
        if not _sin_mcp(config):
            falta.append("que la API de Hermes no cargue MCP: hermes config set platform_toolsets.api_server "
                         "\"['web','memory','skills','session_search','no_mcp']\"")
        if os.getenv('SKY_LOCAL_ONLY', '0') == '1' and not _modelo_local(config):
            falta.append('un modelo local en Hermes (SKY_LOCAL_ONLY=1): provider custom/ollama/lmstudio con base_url '
                         'http://127.0.0.1:…')
    if falta or not probar_red:
        return falta
    try:
        codigo, _ = _pedir('GET', '/health', timeout=2.0)
    except Exception:
        return [f'Hermes corriendo con su API en {_base()} (hermes gateway con API_SERVER_ENABLED=true)']
    if codigo != 200:
        return [f'Hermes respondiendo en {_base()}/health (respondió HTTP {codigo})']
    try:
        codigo, datos = _pedir('GET', '/v1/toolsets', timeout=5.0)
    except Exception as exc:
        return [f'la lista de herramientas de Hermes ({type(exc).__name__})']
    if codigo == 401:
        return ['la clave correcta: SKY_HERMES_KEY no coincide con API_SERVER_KEY de Hermes']
    if codigo != 200 or not isinstance(datos.get('data'), list):
        return [f'la lista de herramientas de Hermes (HTTP {codigo})']
    peligrosas = herramientas_peligrosas(datos['data'])
    if peligrosas:
        return ['desactivar en Hermes (plataforma API) estas herramientas que actúan sobre tu equipo: '
                + ', '.join(peligrosas) + '. Ejemplo: hermes config set platform_toolsets.api_server '
                  "\"['web','memory','skills','session_search','no_mcp']\""]
    return []


def estado() -> dict:
    falta = requisitos()
    return {'listo': not falta, 'falta': falta, 'url': _base(), 'modo': 'consultor',
            'herramientas_permitidas': sorted(SEGURAS)}


# ------------------------------------------------------------------ consulta

def consultar(pregunta: str, timeout: float | None = None) -> dict:
    """Envía SOLO la pregunta a Hermes y devuelve su texto. Lanza HermesNoDisponible con la causa exacta."""
    pregunta = ' '.join(str(pregunta or '').split())[:MAX_PREGUNTA]
    if not pregunta:
        raise ValueError('Decime qué querés preguntarle a Hermes.')
    falta = requisitos()
    if falta:
        raise HermesNoDisponible('Para consultar a Hermes falta: ' + '; '.join(falta) + '.')
    timeout = timeout or float(os.getenv('SKY_HERMES_TIMEOUT_S', '180') or 180)
    inicio = time.perf_counter()
    cuerpo = {'model': os.getenv('SKY_HERMES_MODEL', 'hermes-agent'), 'stream': False,
              'messages': [{'role': 'system', 'content': SISTEMA}, {'role': 'user', 'content': pregunta}]}
    try:
        codigo, datos = _pedir('POST', '/v1/chat/completions', cuerpo, timeout=timeout)
    except Exception as exc:
        _medir(False, inicio, type(exc).__name__)
        raise HermesNoDisponible(f'Hermes no respondió ({type(exc).__name__}).') from exc
    if codigo != 200:
        _medir(False, inicio, f'HTTP {codigo}')
        raise HermesNoDisponible(f'Hermes respondió HTTP {codigo}.')
    try:
        eleccion = datos['choices'][0]
        texto = str(eleccion['message']['content'] or '').strip()
        fin = str(eleccion.get('finish_reason') or '')
    except (KeyError, IndexError, TypeError) as exc:
        _medir(False, inicio, 'respuesta sin formato OpenAI')
        raise HermesNoDisponible('Hermes devolvió una respuesta que no entiendo.') from exc
    if fin in ('error', 'cancelled') or not texto:
        _medir(False, inicio, fin or 'vacía')
        raise HermesNoDisponible('Hermes no pudo completar la consulta' + (f' ({fin}).' if fin else '.'))
    _medir(True, inicio, fin)
    nota = ' (Hermes se quedó sin pasos: la respuesta puede estar incompleta.)' if fin == 'length' else ''
    return {'texto': texto[:MAX_RESPUESTA] + nota, 'incompleta': fin == 'length',
            'ms': int((time.perf_counter() - inicio) * 1000)}


def _medir(ok: bool, inicio: float, detalle: str) -> None:
    try:
        from . import sky_metricas
        sky_metricas.registrar('modelo', 'hermes', ok, (time.perf_counter() - inicio) * 1000, origen='hermes',
                               detalle=detalle[:80])
    except Exception:
        pass


# ------------------------------------------------------------------ voz y texto

_ORDEN = re.compile(r'^(?:sky[\s,]+)?(?:preguntale|pregunta|pregunte|consulta|consultale|consulte|pedile|pide|pidele)'
                    r'(?: a| con)? hermes[\s,:]+(.+)$|'
                    r'^(?:sky[\s,]+)?hermes\s*[,:]\s*(.+)$|'
                    r'^(?:sky[\s,]+)?que hermes (?:investigue|analice|piense|responda|revise)[\s,:]+(.+)$', re.I)


def _norm(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize('NFD', str(t or '').strip())
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn')


def interpretar(texto: str) -> dict | None:
    m = _ORDEN.match(_norm(texto))
    if not m:
        if re.fullmatch(r'(?:sky[\s,]+)?(?:estado de hermes|hermes esta (?:listo|conectado)|como esta hermes)\??',
                        re.sub(r'[¿?¡!]', '', _norm(texto).lower()).strip()):
            e = estado()
            msg = ('Hermes está listo como consultor.' if e['listo'] else
                   'Hermes no está listo. Falta: ' + '; '.join(e['falta']) + '.')
            return {'tipo': 'respuesta', 'mensaje': msg, 'proveedor': 'hermes-consultor'}
        return None
    pregunta = next(g for g in m.groups() if g)
    # Recuperar el texto original (con tildes) del mismo tramo para no deformar la pregunta.
    original = str(texto).strip()
    pregunta = original[len(original) - len(pregunta):] if len(pregunta) <= len(original) else pregunta
    try:
        r = consultar(pregunta)
    except HermesNoDisponible as exc:
        return {'tipo': 'respuesta', 'mensaje': str(exc), 'proveedor': 'hermes-consultor'}
    except ValueError as exc:
        return {'tipo': 'respuesta', 'mensaje': str(exc), 'proveedor': 'hermes-consultor'}
    # Sólo texto: ninguna propuesta, acción ni enlace ejecutable sale de aquí.
    return {'tipo': 'respuesta', 'mensaje': 'Hermes dice: ' + r['texto'], 'proveedor': 'hermes-consultor',
            'consultor': 'Hermes Agent'}
