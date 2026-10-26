"""Registro de módulos de SKY (v12.6): qué hay, qué falta, en qué estado está y activación bajo demanda.

Reutiliza lo que ya existía en vez de crear otro catálogo:
  * Las 26 integraciones de `sky_integraciones.INTEGRACIONES` (con sus variables de entorno exactas).
  * El estado de los servicios que publica el supervisor (`~/.neuralt/sky_supervisor.json`).
  * Los cargadores reales de cada motor pesado (faster-whisper, Ollama, exportación 3D, adaptador SKY).

Estados: disponible · no_configurado · cargando · activo · degradado · error.
Reglas:
  * Al arrancar no se carga ningún modelo pesado ni se llama a servicios externos: cada motor se activa cuando lo
    pedís («SKY, activá el reconocimiento local») o cuando una función lo usa por primera vez.
  * Límite de concurrencia (SKY_MODULOS_CONCURRENCIA, 1 por defecto) y de memoria: no se carga si la RAM libre no
    alcanza para el módulo más una reserva (SKY_MODULOS_RESERVA_MB, 1024).
  * Si un módulo falla queda en «error» con la causa; el resto de SKY sigue funcionando.
  * Ningún módulo publica, envía mensajes ni ejecuta acciones externas por activarse.
  * Nunca se cambia el modelo que elegiste (OLLAMA_MODEL): sólo se precarga ese.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import threading
import time
import unicodedata
import urllib.request
from pathlib import Path
from typing import Callable

ESTADOS = ('disponible', 'no_configurado', 'cargando', 'activo', 'degradado', 'error')
_LOCK = threading.Lock()
_VIVO: dict[str, dict] = {}          # estado de carga en ESTE proceso (API)
_SEM: threading.BoundedSemaphore | None = None


def _semaforo() -> threading.BoundedSemaphore:
    global _SEM
    if _SEM is None:
        try:
            n = max(1, int(os.getenv('SKY_MODULOS_CONCURRENCIA', '1')))
        except ValueError:
            n = 1
        _SEM = threading.BoundedSemaphore(n)
    return _SEM


def _paquete(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


# ------------------------------------------------------------------ motores pesados (cargadores reales)

def _req_stt() -> list[str]:
    from .sky_stt_local import capabilities
    c = capabilities()
    falta = []
    if not c['installed']:
        falta.append('paquete faster-whisper (pip install faster-whisper)')
    if not c['model_present']:
        falta.append('modelo local en SKY_STT_MODEL_DIR (carpeta con model.bin y config.json)')
    return falta


def _cargar_stt() -> str:
    from .sky_stt_local import cargar
    cargar()
    return 'modelo faster-whisper en memoria'


def _descargar_stt() -> None:
    from .sky_stt_local import descargar
    descargar()


def _activo_stt() -> bool:
    from .sky_stt_local import cargado
    return cargado()


def _ollama_base() -> str:
    return os.getenv('OLLAMA_API_BASE', 'http://127.0.0.1:11434').rstrip('/')


def _req_ollama() -> list[str]:
    from .sky_cerebro import modelo
    try:
        with urllib.request.urlopen(_ollama_base() + '/api/tags', timeout=1.0) as r:
            modelos = [m.get('name', '') for m in json.loads(r.read(200_000)).get('models', [])]
    except Exception:
        return ['Ollama corriendo en ' + _ollama_base() + ' (instalalo desde ollama.com y abrilo)']
    elegido = modelo()
    if not any(m == elegido or m.split(':')[0] == elegido for m in modelos):
        return [f'el modelo {elegido} (ollama pull {elegido})']
    return []


def _cargar_ollama() -> str:
    """Precarga EL modelo que elegiste (OLLAMA_MODEL) sin generar texto; Ollama lo mantiene 10 minutos."""
    from .sky_cerebro import modelo
    elegido = modelo()
    cuerpo = json.dumps({'model': elegido, 'prompt': '', 'keep_alive': os.getenv('SKY_OLLAMA_KEEP_ALIVE', '10m')}).encode()
    req = urllib.request.Request(_ollama_base() + '/api/generate', data=cuerpo,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=float(os.getenv('SKY_OLLAMA_CARGA_S', '180'))) as r:
        r.read(4096)
    return f'{elegido} cargado en Ollama'


def _activo_ollama() -> bool:
    from .sky_cerebro import modelo
    try:
        with urllib.request.urlopen(_ollama_base() + '/api/ps', timeout=1.0) as r:
            cargados = [m.get('name', '') for m in json.loads(r.read(200_000)).get('models', [])]
        elegido = modelo()
        return any(m == elegido or m.split(':')[0] == elegido for m in cargados)
    except Exception:
        return False


def _req_3d() -> list[str]:
    return [] if _paquete('trimesh') and _paquete('numpy') else ['paquete trimesh (pip install trimesh)']


def _cargar_3d() -> str:
    import metaverse.export3d  # noqa: F401  (trimesh + scipy)
    return 'exportador GLB listo'


def _activo_3d() -> bool:
    import sys
    return 'metaverse.export3d' in sys.modules


def _req_hermes() -> list[str]:
    from .sky_hermes import requisitos
    return requisitos()


def _req_entrenado() -> list[str]:
    from .sky_trained_inference import readiness
    r = readiness()
    falta = []
    if not r['configured']:
        falta.append('SKY_TRAINED_RELEASE_DIR con un adaptador LoRA entrenado y su manifiesto')
    if not r['owner_approved']:
        falta.append('tu aprobación explícita (SKY_TRAINED_ENABLED=1)')
    if r['configured'] and not r['released_to_sky']:
        falta.append('una evaluación aprobada del adaptador (evaluation_passed y eval_loss_improved)')
    if not _paquete('torch') or not _paquete('peft') or not _paquete('transformers'):
        falta.append('paquetes torch, transformers y peft (requirements_sky_training.txt)')
    return falta


def _cargar_entrenado() -> str:
    from .sky_trained_inference import _load, _release
    rel = _release()
    if not rel:
        raise RuntimeError('No hay adaptador configurado')
    _load(str(rel[0]))
    return 'adaptador SKY cargado en la GPU'


def _req_tts() -> list[str]:
    from .sky_tts import disponible
    return [] if disponible() else ['Piper y una voz .onnx (los instala el instalador de SKY; SKY_PIPER_BIN y SKY_PIPER_VOZ)']


# ------------------------------------------------------------------ servicios (los maneja el supervisor)

def _ruta_supervisor() -> Path:
    return Path(os.getenv('SKY_SUPERVISOR_DIR') or (Path.home() / '.neuralt')) / 'sky_supervisor.json'


def _servicios_supervisor() -> dict:
    try:
        d = json.loads(_ruta_supervisor().read_text(encoding='utf-8'))
        return d.get('servicios', {}) if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _req_voz() -> list[str]:
    raiz = Path(__file__).resolve().parents[1]
    falta = []
    if not (raiz / 'modelos' / 'vosk-model-es').is_dir():
        falta.append('modelo Vosk en modelos/vosk-model-es')
    for mod in ('vosk', 'sounddevice', 'pyttsx3'):
        if not _paquete(mod):
            falta.append(f'paquete {mod} (pip install {mod})')
    return falta


def _req_whatsapp() -> list[str]:
    from .sky_whatsapp import estado
    e = estado()
    return [] if e.get('configurado') else ['variables ' + ', '.join(e.get('faltan') or ['SKY_WA_*']) + ' en .env']


def _req_agente() -> list[str]:
    from .sky_asistente_personal import token_agente_local
    return [] if len(token_agente_local()) >= 32 else ['token del agente (iniciá agente_dispositivo.py una vez)']


# ------------------------------------------------------------------ catálogo

def _m(id_: str, nombre: str, tipo: str, alias: tuple, requisitos: Callable[[], list] | None = None,
       cargar: Callable[[], str] | None = None, descargar: Callable[[], None] | None = None,
       activo: Callable[[], bool] | None = None, ram_mb: int = 0, servicio: str = '', esencial: bool = False) -> dict:
    return {'id': id_, 'nombre': nombre, 'tipo': tipo, 'alias': alias, 'requisitos': requisitos, 'cargar': cargar,
            'descargar': descargar, 'activo': activo, 'ram_mb': ram_mb, 'servicio': servicio, 'esencial': esencial}


def _nucleo() -> list[dict]:
    return [
        _m('api', 'API propia de SKY', 'servicio', ('api', 'nucleo'), servicio='api', esencial=True),
        _m('agente', 'Agente del equipo', 'servicio', ('agente', 'agente del equipo'), _req_agente, servicio='agent',
           esencial=True),
        _m('voz_manos_libres', 'Escucha manos libres (Vosk)', 'servicio', ('manos libres', 'escucha', 'vosk', 'microfono'),
           _req_voz, servicio='voice'),
        _m('whatsapp', 'Puente de WhatsApp', 'servicio', ('whatsapp',), _req_whatsapp, servicio='whatsapp'),
        _m('stt_local', 'Reconocimiento de voz local (faster-whisper)', 'motor',
           ('reconocimiento local', 'reconocimiento de voz', 'whisper', 'faster whisper', 'transcripcion'),
           _req_stt, _cargar_stt, _descargar_stt, _activo_stt, ram_mb=900),
        _m('tts_piper', 'Voz local (Piper)', 'motor', ('piper', 'voz local', 'sintesis de voz'), _req_tts),
        _m('ollama', 'Modelo local (Ollama)', 'motor', ('ollama', 'modelo local', 'ia local', 'cerebro local'),
           _req_ollama, _cargar_ollama, None, _activo_ollama, ram_mb=int(os.getenv('SKY_OLLAMA_RAM_MB', '5000') or 5000)),
        _m('export3d', 'Exportación 3D (GLB)', 'motor', ('3d', 'exportacion 3d', 'trimesh', 'glb'),
           _req_3d, _cargar_3d, None, _activo_3d, ram_mb=150),
        _m('hermes', 'Hermes Agent (consultor)', 'integracion', ('hermes', 'hermes agent'), _req_hermes),
        _m('sky_entrenado', 'Adaptador SKY entrenado (LoRA)', 'motor', ('adaptador', 'modelo entrenado', 'lora'),
           _req_entrenado, _cargar_entrenado, ram_mb=6000),
    ]


def catalogo() -> list[dict]:
    from .sky_integraciones import INTEGRACIONES
    mods = _nucleo()
    propios = {m['id'] for m in mods} | {'piper', 'whisper', 'agente', 'whatsapp', 'ollama', 'hermes-agent'}
    for iid, nombre, via, variables, uso, nota, _docs in INTEGRACIONES:
        if iid in propios:
            continue
        mods.append({'id': iid, 'nombre': nombre, 'tipo': 'integracion', 'alias': (iid.replace('_', ' '), nombre.lower()),
                     'requisitos': (lambda v=variables, vi=via, no=nota: _req_integracion(v, vi, no)),
                     'cargar': None, 'descargar': None, 'activo': None, 'ram_mb': 0, 'servicio': '',
                     'esencial': False, 'uso': uso})
    return mods


def _req_integracion(variables: list, via: str, nota: str) -> list[str]:
    if via == 'sin_api':
        return ['no tiene API pública: ' + nota]
    if via == 'oauth':
        return ['integración OAuth pendiente en SKY: ' + nota]
    return [f'{v} en .env' for v in variables if not (os.getenv(v, '').strip() or os.getenv(v + '_FILE', '').strip())]


def _buscar(id_: str) -> dict | None:
    return next((m for m in catalogo() if m['id'] == id_), None)


# ------------------------------------------------------------------ estado

def estado(id_: str) -> dict:
    m = _buscar(id_)
    if not m:
        raise KeyError(id_)
    base = {'id': m['id'], 'nombre': m['nombre'], 'tipo': m['tipo'], 'esencial': m['esencial'],
            'puede_activar': bool(m['cargar']), 'pesado': m['ram_mb'] >= 500, 'falta': [], 'detalle': ''}
    try:
        falta = list(m['requisitos']()) if m['requisitos'] else []
    except Exception as exc:
        return {**base, 'estado': 'error', 'detalle': f'no pude comprobar requisitos: {type(exc).__name__}'}
    base['falta'] = falta
    vivo = _VIVO.get(m['id'], {})
    if m['servicio']:
        if m['id'] == 'api':
            return {**base, 'estado': 'activo', 'detalle': 'respondiendo (esta misma API)'}
        sup = _servicios_supervisor().get(m['servicio'])
        if falta:
            return {**base, 'estado': 'no_configurado', 'detalle': 'falta: ' + '; '.join(falta)}
        if not sup:
            return {**base, 'estado': 'disponible', 'detalle': 'configurado; no lo está supervisando el lanzador'}
        e = sup.get('estado', '')
        mapa = {'activo': 'activo', 'externo': 'activo', 'cargando': 'cargando', 'degradado': 'degradado',
                'no_configurado': 'no_configurado', 'error': 'error', 'detenido': 'disponible'}
        return {**base, 'estado': mapa.get(e, 'error'), 'detalle': sup.get('causa', ''), 'reinicios': sup.get('reinicios', 0)}
    if vivo.get('estado') in ('cargando', 'error'):
        return {**base, 'estado': vivo['estado'], 'detalle': vivo.get('detalle', '')}
    if falta:
        return {**base, 'estado': 'no_configurado', 'detalle': 'falta: ' + '; '.join(falta)}
    try:
        if m['activo'] and m['activo']():
            return {**base, 'estado': 'activo', 'detalle': vivo.get('detalle', 'cargado en memoria')}
    except Exception:
        pass
    if vivo.get('estado') == 'activo' and not m['activo']:
        return {**base, 'estado': 'activo', 'detalle': vivo.get('detalle', '')}
    return {**base, 'estado': 'disponible',
            'detalle': 'listo para activar bajo demanda' if m['cargar'] else 'configurado; se usa cuando hace falta'}


def listar() -> dict:
    filas = []
    for m in catalogo():
        try:
            filas.append(estado(m['id']))
        except Exception as exc:   # un módulo roto no rompe el listado
            filas.append({'id': m['id'], 'nombre': m['nombre'], 'tipo': m['tipo'], 'estado': 'error',
                          'detalle': type(exc).__name__, 'falta': []})
    cuenta = {e: sum(1 for f in filas if f['estado'] == e) for e in ESTADOS}
    return {'modulos': filas, 'resumen': cuenta}


# ------------------------------------------------------------------ activación bajo demanda

def _ram_libre_mb() -> int | None:
    try:
        import psutil
        return int(psutil.virtual_memory().available / 1_048_576)
    except Exception:
        return None


def activar(id_: str, esperar: bool = False, aviso: Callable[[str], None] | None = None) -> dict:
    """Carga un motor pesado en segundo plano. Devuelve el estado inmediato ('cargando', 'activo', 'no_configurado'…)."""
    m = _buscar(id_)
    if not m:
        raise KeyError(id_)
    actual = estado(id_)
    if actual['estado'] in ('activo', 'cargando', 'no_configurado'):
        return {**actual, 'mensaje': _frase(actual)}
    if m['servicio']:
        return {**actual, 'mensaje': f"{m['nombre']} lo inicia y supervisa el lanzador de SKY."}
    if not m['cargar']:
        return {**actual, 'mensaje': f"{m['nombre']} no necesita activarse: se usa cuando hace falta."}
    libre, reserva = _ram_libre_mb(), int(os.getenv('SKY_MODULOS_RESERVA_MB', '1024') or 1024)
    if libre is not None and m['ram_mb'] and libre < m['ram_mb'] + reserva:
        return {**actual, 'estado': 'degradado',
                'mensaje': f"No cargo {m['nombre']}: hay {libre} MB libres y necesita unos {m['ram_mb']} MB más "
                           f"{reserva} MB de reserva. Cerrá programas o liberá otro módulo."}
    sem = _semaforo()
    if not sem.acquire(blocking=False):
        return {**actual, 'mensaje': 'Ya estoy cargando otro módulo; pedímelo de nuevo en un momento.'}
    with _LOCK:
        _VIVO[id_] = {'estado': 'cargando', 'detalle': 'cargando…', 'desde': time.time()}

    def trabajo():
        inicio = time.perf_counter()
        try:
            detalle = m['cargar']() or 'activo'
            with _LOCK:
                _VIVO[id_] = {'estado': 'activo', 'detalle': detalle}
            _metrica(id_, True, inicio, detalle)
            if aviso:
                aviso(f"{m['nombre']} está activo ({(time.perf_counter() - inicio):.1f} s).")
        except Exception as exc:
            with _LOCK:
                _VIVO[id_] = {'estado': 'error', 'detalle': f'{type(exc).__name__}: {str(exc)[:200]}'}
            _metrica(id_, False, inicio, type(exc).__name__)
            if aviso:
                aviso(f"No pude activar {m['nombre']}: {str(exc)[:160]}")
        finally:
            sem.release()

    hilo = threading.Thread(target=trabajo, name=f'sky-modulo-{id_}', daemon=True)
    hilo.start()
    if esperar:
        hilo.join()
    r = estado(id_)
    return {**r, 'mensaje': _frase(r)}


def descargar(id_: str) -> dict:
    m = _buscar(id_)
    if not m:
        raise KeyError(id_)
    if m['descargar']:
        m['descargar']()
    with _LOCK:
        _VIVO.pop(id_, None)
    r = estado(id_)
    return {**r, 'mensaje': f"Liberé {m['nombre']}." if m['descargar'] else f"{m['nombre']} no se puede liberar desde SKY."}


def _metrica(id_: str, ok: bool, inicio: float, detalle: str) -> None:
    try:
        from . import sky_metricas
        sky_metricas.registrar('servicio', 'modulo_' + id_, ok, (time.perf_counter() - inicio) * 1000, detalle=detalle[:120])
    except Exception:
        pass


# ------------------------------------------------------------------ preparación de la API

def preparacion_api() -> dict:
    """Readiness de la API: lo mínimo para atender (sin datos personales en la respuesta)."""
    componentes = {}

    def probar(nombre, fn):
        inicio = time.perf_counter()
        try:
            fn()
            componentes[nombre] = {'ok': True, 'ms': round((time.perf_counter() - inicio) * 1000, 1)}
        except Exception as exc:
            componentes[nombre] = {'ok': False, 'error': type(exc).__name__}

    def memoria():
        from . import storage
        import sqlite3
        with sqlite3.connect(storage.DB, timeout=3) as c:
            c.execute('select 1')

    def seguridad():
        from .sentinel_identidad import estado_sesion
        estado_sesion()

    def metricas():
        from . import sky_metricas
        sky_metricas.registrar('servicio', 'preparacion', True)

    probar('memoria', memoria)
    probar('seguridad', seguridad)
    probar('metricas', metricas)
    return {'listo': all(c['ok'] for c in componentes.values()), 'componentes': componentes}


# ------------------------------------------------------------------ voz y texto

def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'^(?:oye |hey |ok )?sky[\s,]+', '', s.strip())
    return ' '.join(re.sub(r'[^\w\s]', ' ', s).split())


def _resolver_alias(texto: str) -> dict | None:
    t = _norm(texto)
    mejor = None
    for m in catalogo():
        for a in (m['id'].replace('_', ' '),) + tuple(m['alias']):
            a = _norm(a)
            if a and re.search(r'(?<!\w)' + re.escape(a) + r'(?!\w)', t) and (not mejor or len(a) > mejor[1]):
                mejor = (m, len(a))
    return mejor[0] if mejor else None


def _objetivo(resto: str, dijo_modulo: bool) -> dict | None:
    """Con la palabra «módulo» vale cualquier alias; sin ella, sólo el nombre exacto de un motor
    («activá el reconocimiento local»), para no capturar órdenes como «activá la escucha continua»."""
    if dijo_modulo:
        return _resolver_alias(resto)
    r = _norm(resto)
    for m in catalogo():
        if m['tipo'] == 'motor' and r in {_norm(a) for a in (m['id'].replace('_', ' '),) + tuple(m['alias'])}:
            return m
    return None


def _frase(e: dict) -> str:
    nombres = {'disponible': 'disponible', 'no_configurado': 'sin configurar', 'cargando': 'cargando',
               'activo': 'activo', 'degradado': 'degradado', 'error': 'con error'}
    txt = f"{e['nombre']}: {nombres.get(e['estado'], e['estado'])}."
    if e.get('falta'):
        txt += ' Falta: ' + '; '.join(e['falta']) + '.'
    elif e.get('detalle') and e['estado'] != 'disponible':
        txt += ' ' + str(e['detalle']).rstrip('.') + '.'
    return txt


def _resp(msg: str, **extra) -> dict:
    return {'tipo': 'respuesta', 'mensaje': msg, 'proveedor': 'sky-modulos', **extra}


def interpretar(texto: str) -> dict | None:
    t = _norm(texto)
    if re.fullmatch(r'(?:muestra(?:me)?|mostra(?:me)?|dame|cual es|como esta|revisa)? ?(?:el )?estado de (?:los |tus )?modulos|'
                    r'(?:que|cuales) modulos (?:tenes|tienes|hay|estan activos)|modulos', t):
        d = listar()
        r = d['resumen']
        problemas = [f for f in d['modulos'] if f['tipo'] != 'integracion' and f['estado'] in ('error', 'degradado', 'no_configurado')]
        msg = (f"Módulos: {r['activo']} activos, {r['disponible']} disponibles, {r['no_configurado']} sin configurar, "
               f"{r['cargando']} cargando, {r['degradado']} degradados y {r['error']} con error.")
        if problemas:
            msg += ' ' + ' '.join(_frase(p) for p in problemas[:5])
        return _resp(msg, modulo='modulos')
    m = re.fullmatch(r'(?:activa|activar|carga|cargar|encende|enciende|prende|inicia|precarga)(?: el| la)?( modulo(?: de)?)? (.+)', t)
    if m:
        mod = _objetivo(m.group(2), bool(m.group(1)))
        if not mod:
            return None   # puede ser otra orden («activá la alarma»): que la atiendan las demás reglas
        def avisar(txt):
            try:
                from .sky_rutinas import avisar as _av
                _av(txt, 'modulos')
            except Exception:
                pass
        r = activar(mod['id'], aviso=avisar)
        if r['estado'] == 'cargando':
            return _resp(f"Estoy cargando {mod['nombre']}; te aviso cuando esté listo.", modulo='modulos')
        return _resp(r['mensaje'], modulo='modulos')
    m = re.fullmatch(r'(?:libera|liberar|descarga|descargar|apaga)(?: el| la)?( modulo(?: de)?)? (.+)', t)
    if m:
        mod = _objetivo(m.group(2), bool(m.group(1)))
        if not mod or not mod['cargar']:
            return None
        return _resp(descargar(mod['id'])['mensaje'], modulo='modulos')
    m = re.fullmatch(r'(?:que le falta a|que falta para|estado del? modulo(?: de)?|como esta el modulo(?: de)?) (.+)', t)
    if m:
        mod = _resolver_alias(m.group(1))
        if mod:
            return _resp(_frase(estado(mod['id'])), modulo='modulos')
    return None
