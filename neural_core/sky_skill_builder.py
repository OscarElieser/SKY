"""SKY v12.4 — SKY SKILL BUILDER: SKY detecta lo que le falta, propone una habilidad, la programa, la prueba
aislada y SÓLO la instala cuando el dueño la aprueba (con los permisos que él acepte).

Ciclo:
    necesidad ─► propuesta (manifiesto + código + pruebas, redactados por la IA configurada)
              ─► revisión estática (lista cerrada de módulos, sin archivos/red/eval/atributos «_»)
              ─► pruebas en un proceso aislado (sky_sandbox_runner) ─► «probada» o «fallida»
              ─► aprobación del dueño en el HUD (nivel 3) ─► «instalada» (versión fija)
              ─► uso: «<disparador> …» ─► datos de internet aprobados ─► proceso aislado ─► respuesta / órdenes
Garantías:
  * No instala paquetes ni código externo; sólo módulos puros de la biblioteca estándar.
  * No modifica el núcleo de SKY ni sus controles: el código vive en ~/.neuralt/builder/<id>/v<N>/ y se ejecuta aislado.
  * Las órdenes que devuelve una habilidad pasan por los mismos permisos y confirmaciones que tus órdenes.
  * Cada versión queda guardada: se puede volver a una anterior o desinstalar. Por voz se puede desactivar,
    nunca aprobar.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

_LOCK = threading.Lock()
MAX_CODIGO = 20_000
TIEMPO_PROCESO = 15
MAX_FUENTE = 300_000
PERMISOS_VALIDOS = re.compile(r'^(?:acciones|internet:[a-z0-9.-]{3,80})$')
NOMBRES_PROHIBIDOS = {'open', 'exec', 'eval', 'compile', '__import__', 'globals', 'locals', 'vars', 'getattr', 'setattr',
                      'delattr', 'input', 'breakpoint', 'help', 'exit', 'quit', 'memoryview', 'type', '__builtins__',
                      'print', 'dir'}
from .sky_sandbox_runner import PERMITIDOS as MODULOS_PERMITIDOS  # noqa: E402


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'^(?:oye |hey |ok )?sky[\s,]+', '', s.strip())
    return ' '.join(re.sub(r'[^\w\s]', ' ', s).split())


def base() -> Path:
    return Path.home() / '.neuralt' / 'builder'


def _estado() -> dict:
    try:
        d = json.loads((base() / 'estado.json').read_text(encoding='utf-8'))
        return d if isinstance(d, dict) and isinstance(d.get('skills'), dict) else {'skills': {}, 'necesidades': {}}
    except (OSError, ValueError):
        return {'skills': {}, 'necesidades': {}}


def _guardar(d: dict) -> None:
    base().mkdir(mode=0o700, parents=True, exist_ok=True)
    p = base() / 'estado.json'
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(p)


def _registro(evento: str, detalle: str) -> None:
    """Auditoría del builder: qué se propuso, probó, aprobó o quitó (sin código ni datos personales)."""
    base().mkdir(mode=0o700, parents=True, exist_ok=True)
    with (base() / 'auditoria.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'at': datetime.now().isoformat(timespec='seconds'), 'evento': evento, 'detalle': detalle[:200]},
                           ensure_ascii=False) + '\n')


# ------------------------------------------------------------------ necesidades detectadas

_PEDIDO = re.compile(r'^(?:haz|hace|hazme|crea|creame|calcula|calculame|convierte|organiza|planifica|genera|traduce|resume|'
                     r'analiza|compara|busca|ordena|cuenta|mide|registra|lleva|controla|avisame|necesito que|quiero que|'
                     r'podrias|puedes|me ayudas a)\b')


def registrar_necesidad(texto: str) -> None:
    """Se llama cuando SKY no tuvo una herramienta para un pedido. Sólo guarda la frase normalizada y cuántas veces."""
    t = _norm(texto)
    if not t or len(t) > 160 or not _PEDIDO.match(t):
        return
    with _LOCK:
        d = _estado()
        nec = d.setdefault('necesidades', {})
        item = nec.setdefault(t, {'veces': 0, 'primera': datetime.now().isoformat(timespec='seconds')})
        item['veces'] += 1
        item['ultima'] = datetime.now().isoformat(timespec='seconds')
        if len(nec) > 200:
            for k in sorted(nec, key=lambda k: nec[k].get('ultima', ''))[:len(nec) - 200]:
                nec.pop(k, None)
        _guardar(d)


def necesidades(limite: int = 10) -> list[dict]:
    nec = _estado().get('necesidades', {})
    return [{'frase': k, **v} for k, v in sorted(nec.items(), key=lambda kv: (-kv[1]['veces'], kv[1].get('ultima', '')))][:limite]


# ------------------------------------------------------------------ revisión estática

def validar_codigo(codigo: str) -> list[str]:
    """Devuelve la lista de problemas (vacía = aceptable). No ejecuta nada."""
    problemas = []
    if not isinstance(codigo, str) or not codigo.strip():
        return ['El código está vacío.']
    if len(codigo) > MAX_CODIGO:
        return [f'El código supera {MAX_CODIGO} caracteres.']
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as exc:
        return [f'Error de sintaxis en la línea {exc.lineno}: {exc.msg}']
    tiene_ejecutar = False
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for a in nodo.names:
                if a.name.split('.')[0] not in MODULOS_PERMITIDOS:
                    problemas.append(f'Importa «{a.name}», que no está permitido.')
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level or (nodo.module or '').split('.')[0] not in MODULOS_PERMITIDOS:
                problemas.append(f'Importa desde «{nodo.module}», que no está permitido.')
        elif isinstance(nodo, ast.Name) and nodo.id in NOMBRES_PROHIBIDOS:
            problemas.append(f'Usa «{nodo.id}», que no está permitido.')
        elif isinstance(nodo, ast.Name) and nodo.id.startswith('__'):
            problemas.append(f'Usa el nombre interno «{nodo.id}».')
        elif isinstance(nodo, ast.Attribute) and nodo.attr.startswith('_'):
            problemas.append(f'Accede al atributo interno «{nodo.attr}».')
        elif isinstance(nodo, (ast.Global, ast.Nonlocal)):
            problemas.append('No se permiten variables global/nonlocal.')
        elif isinstance(nodo, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
            problemas.append('No se permite código asíncrono.')
        elif isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) and re.search(r'\{[^{}]*\.\s*_', nodo.value):
            problemas.append('Un texto con formato intenta acceder a atributos internos.')
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name == 'ejecutar' and len(nodo.args.args) == 2:
            tiene_ejecutar = True
    if not tiene_ejecutar:
        problemas.append('Falta la función de nivel superior ejecutar(entrada, contexto).')
    return sorted(set(problemas))


def validar_manifiesto(m: dict) -> tuple[dict, list[str]]:
    problemas = []
    if not isinstance(m, dict):
        return {}, ['El manifiesto debe ser un objeto JSON.']
    nombre = ' '.join(str(m.get('nombre', '')).split())[:60]
    sid = re.sub(r'[^a-z0-9]+', '-', _norm(m.get('id') or nombre)).strip('-')[:40]
    if not sid or not nombre:
        problemas.append('Falta el nombre de la habilidad.')
    disparadores = [_norm(x)[:60] for x in (m.get('disparadores') or []) if len(_norm(x)) >= 4][:6]
    if not disparadores:
        problemas.append('Faltan disparadores (frases con las que empieza el pedido, de al menos 4 letras).')
    reservados = ('sky', 'para todo', 'detente', 'emergencia', 'aprueba', 'instala', 'recuerda', 'olvida')
    if any(d in reservados or d.startswith(('para todo', 'aprueba', 'instala')) for d in disparadores):
        problemas.append('Un disparador usa una frase reservada de SKY.')
    permisos = [p for p in (m.get('permisos') or []) if isinstance(p, str)]
    malos = [p for p in permisos if not PERMISOS_VALIDOS.match(p)]
    if malos:
        problemas.append('Permisos no válidos: ' + ', '.join(malos[:5]))
    fuentes = []
    for f in (m.get('fuentes') or [])[:5]:
        url = str((f or {}).get('url', ''))
        partes = urllib.parse.urlsplit(url.replace('{entrada}', 'x'))
        nombre_f = re.sub(r'[^a-z0-9_]', '', str((f or {}).get('nombre', '')).lower())[:30]
        if partes.scheme != 'https' or not partes.hostname or not nombre_f:
            problemas.append(f'Fuente inválida: {url[:80]} (sólo https y con nombre).')
        elif f'internet:{partes.hostname}' not in permisos:
            problemas.append(f'La fuente {partes.hostname} necesita el permiso internet:{partes.hostname}.')
        else:
            fuentes.append({'nombre': nombre_f, 'url': url[:300]})
    pruebas = [p for p in (m.get('pruebas') or []) if isinstance(p, dict) and isinstance(p.get('entrada'), str)][:10]
    if not pruebas:
        problemas.append('Faltan pruebas (al menos una con «entrada» y «espera»).')
    limpio = {'id': sid, 'nombre': nombre, 'descripcion': str(m.get('descripcion', ''))[:300], 'disparadores': disparadores,
              'permisos': sorted(set(permisos) - set(malos)), 'fuentes': fuentes,
              'pruebas': [{'entrada': p['entrada'][:300], 'contexto': p.get('contexto') if isinstance(p.get('contexto'), dict) else {},
                           'espera': [str(x)[:120] for x in (p.get('espera') or [])][:5]} for p in pruebas]}
    return limpio, problemas


# ------------------------------------------------------------------ ejecución aislada

def ejecutar_aislado(codigo: str, casos: list[dict], timeout: int = TIEMPO_PROCESO) -> dict:
    runner = Path(__file__).with_name('sky_sandbox_runner.py')
    entorno = {k: os.environ[k] for k in ('SYSTEMROOT', 'WINDIR', 'PATH', 'LANG') if k in os.environ}
    entorno['PYTHONIOENCODING'] = 'utf-8'
    with tempfile.TemporaryDirectory(prefix='sky_habilidad_') as tmp:
        try:
            proc = subprocess.run([sys.executable, '-I', '-S', str(runner)], input=json.dumps({'codigo': codigo, 'casos': casos}),
                                  capture_output=True, text=True, timeout=timeout, cwd=tmp, env=entorno, encoding='utf-8')
        except subprocess.TimeoutExpired:
            return {'ok': False, 'error': f'Superó el tiempo máximo de {timeout} s.', 'resultados': []}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'ok': False, 'error': 'El proceso aislado terminó sin respuesta (¿límite de memoria o CPU?).', 'resultados': []}


def probar(manifiesto: dict, codigo: str) -> dict:
    problemas = validar_codigo(codigo)
    if problemas:
        return {'aprobada': False, 'estatica': problemas, 'pruebas': []}
    r = ejecutar_aislado(codigo, [{'entrada': p['entrada'], 'contexto': p['contexto']} for p in manifiesto['pruebas']])
    if not r.get('ok'):
        return {'aprobada': False, 'estatica': [], 'pruebas': [], 'error': r.get('error', '')}
    detalle = []
    for p, res in zip(manifiesto['pruebas'], r['resultados']):
        decir = (res.get('salida') or {}).get('decir', '') if res.get('ok') else ''
        faltan = [e for e in p['espera'] if _norm(e) not in _norm(decir)]
        detalle.append({'entrada': p['entrada'], 'ok': bool(res.get('ok')) and not faltan, 'decir': decir[:300],
                        'error': res.get('error', '') or (('No dijo: ' + ', '.join(faltan)) if faltan else '')})
    return {'aprobada': bool(detalle) and all(d['ok'] for d in detalle), 'estatica': [], 'pruebas': detalle}


# ------------------------------------------------------------------ propuestas

PLANTILLA = '''Sos el programador del SKY Skill Builder. Diseñá UNA habilidad para SKY (asistente personal en español).
Pedido del dueño: «{pedido}».
Reglas estrictas:
- Python puro. Sólo podés importar: {modulos}. Nada de archivos, red, os, sys, subprocess, eval, exec, open, print, getattr ni atributos que empiecen con «_».
- Definí def ejecutar(entrada: str, contexto: dict) -> dict que devuelva {{"decir": "respuesta en español"}} y opcionalmente
  "acciones": [{{"orden": "frase en español que SKY ya entiende, ej. abre la calculadora"}}] (máximo 5, requiere el permiso "acciones").
- Si necesitás datos de internet, declaralos en "fuentes" con URLs https fijas de APIs públicas sin clave (podés usar {{entrada}} en la URL)
  y el permiso "internet:<dominio>"; los datos llegan ya descargados en contexto["fuentes"]["<nombre>"] (dict JSON o texto).
- Incluí de 2 a 4 pruebas con "entrada", "contexto" (con fuentes simuladas si usás internet) y "espera" (fragmentos que debe contener "decir").
Respondé SOLO un JSON con: {{"manifiesto": {{"nombre", "descripcion", "disparadores": [frases con las que empieza el pedido],
"permisos": [], "fuentes": [{{"nombre", "url"}}], "pruebas": []}}, "codigo": "…"}}'''


def _redactar(pedido: str, proveedor: str = 'auto') -> dict:
    from .providers import reply
    texto = str(reply([{'role': 'system', 'content': 'Respondés únicamente JSON válido.'},
                       {'role': 'user', 'content': PLANTILLA.format(pedido=pedido[:500], modulos=', '.join(MODULOS_PERMITIDOS))}],
                      proveedor, max_output_tokens=4000))
    m = re.search(r'\{.*\}', texto, re.S)
    if not m:
        raise ValueError('La IA no devolvió una propuesta en JSON.')
    datos = json.loads(m.group(0))
    if not isinstance(datos, dict) or 'codigo' not in datos:
        raise ValueError('La propuesta no trae código.')
    return datos


def guardar_propuesta(manifiesto_crudo: dict, codigo: str, pedido: str = '') -> dict:
    """Guarda una nueva versión (de la IA o escrita por el dueño), la revisa y la prueba. Nunca la instala."""
    manifiesto, problemas = validar_manifiesto(manifiesto_crudo)
    if problemas and not manifiesto.get('id'):
        raise ValueError('; '.join(problemas))
    with _LOCK:
        d = _estado()
        info = d['skills'].get(manifiesto['id'], {'versiones': 0, 'creado': datetime.now().isoformat(timespec='seconds')})
        version = int(info.get('versiones', 0)) + 1
    reporte = {'aprobada': False, 'estatica': problemas, 'pruebas': []} if problemas else probar(manifiesto, codigo)
    carpeta = base() / manifiesto['id'] / f'v{version}'
    carpeta.mkdir(mode=0o700, parents=True, exist_ok=True)
    (carpeta / 'skill.json').write_text(json.dumps({**manifiesto, 'version': version, 'pedido': pedido[:300]}, ensure_ascii=False, indent=2), encoding='utf-8')
    (carpeta / 'skill.py').write_text(codigo, encoding='utf-8')
    (carpeta / 'reporte.json').write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding='utf-8')
    with _LOCK:
        d = _estado()
        info = d['skills'].setdefault(manifiesto['id'], {'creado': datetime.now().isoformat(timespec='seconds')})
        info.update(versiones=version, ultima=version, nombre=manifiesto['nombre'],
                    estado_ultima='probada' if reporte['aprobada'] else 'fallida')
        info.setdefault('estado', 'propuesta')
        _guardar(d)
    _registro('propuesta', f"{manifiesto['id']} v{version} {'probada' if reporte['aprobada'] else 'fallida'}")
    return {'id': manifiesto['id'], 'version': version, 'manifiesto': manifiesto, 'reporte': reporte}


def proponer(pedido: str, proveedor: str = 'auto', intentos: int = 2) -> dict:
    """Bucle reflexivo acotado: propone, verifica, aprende y corrige SIN instalar.

    La memoria es local y sólo contiene etiquetas de resultados; ni el texto
    privado de las pruebas ni sus stack traces se envían en reintentos.
    """
    from . import sky_reflective_core as reflection
    import hashlib
    import sqlite3

    pedido = ' '.join(str(pedido).split())[:500]
    if len(pedido) < 6:
        raise ValueError('Contame qué tiene que hacer la habilidad.')
    if isinstance(intentos, bool) or not isinstance(intentos, int):
        raise ValueError('Cantidad de intentos inválida.')
    max_intentos = min(3, max(1, intentos))
    try:
        consejos = reflection.recall(pedido, limit=2)
    except (OSError, ValueError, sqlite3.Error):
        consejos = []
    consejo_inicial = ' '.join(c['lesson'] for c in consejos)[:350]

    ultimo = None
    resumen_fallo = ''
    codigos_vistos = set()
    for intento in range(max_intentos):
        consigna = pedido
        if intento == 0 and consejo_inicial:
            consigna += '\nLecciones de pruebas locales anteriores: ' + consejo_inicial
        if ultimo is not None:
            consigna += '\nTu versión anterior falló en las pruebas. ' + resumen_fallo + ' Corregila.'
        datos = _redactar(consigna, proveedor)
        codigo = str(datos.get('codigo', ''))
        huella = hashlib.sha256(codigo.encode('utf-8')).hexdigest()
        if huella in codigos_vistos:
            break  # No repetir indefinidamente una propuesta idéntica.
        codigos_vistos.add(huella)
        ultimo = guardar_propuesta(datos.get('manifiesto') or {}, codigo, pedido)
        try:
            reflection.record(pedido, ultimo['reporte'])
        except (OSError, ValueError, sqlite3.Error):
            pass  # La memoria optativa nunca bloquea la revisión y las pruebas.
        if ultimo['reporte']['aprobada']:
            break
        resumen_fallo = reflection.safe_feedback(ultimo['reporte'])

    try:
        with _LOCK:
            d = _estado()
            d.get('necesidades', {}).pop(_norm(pedido), None)
            _guardar(d)
    except Exception:
        pass
    return ultimo


def cargar(sid: str, version: int | None = None) -> tuple[dict, str, dict]:
    if not re.fullmatch(r'[a-z0-9-]{1,40}', sid or ''):
        raise KeyError(sid)
    info = _estado()['skills'].get(sid)
    if not info:
        raise KeyError(sid)
    v = int(version or info.get('ultima') or 1)
    carpeta = base() / sid / f'v{v}'
    m = json.loads((carpeta / 'skill.json').read_text(encoding='utf-8'))
    codigo = (carpeta / 'skill.py').read_text(encoding='utf-8')
    reporte = json.loads((carpeta / 'reporte.json').read_text(encoding='utf-8'))
    return m, codigo, reporte


def listar() -> list[dict]:
    salida = []
    for sid, info in _estado()['skills'].items():
        try:
            m, codigo, rep = cargar(sid)
        except (KeyError, OSError, ValueError):
            continue
        salida.append({'id': sid, 'nombre': info.get('nombre', sid), 'estado': info.get('estado', 'propuesta'),
                       'version_instalada': info.get('version_instalada'), 'ultima': info.get('ultima'),
                       'estado_ultima': info.get('estado_ultima'), 'permisos_aprobados': info.get('permisos_aprobados', []),
                       'manifiesto': m, 'codigo': codigo, 'reporte': rep})
    return salida


# ------------------------------------------------------------------ aprobación del dueño (sólo HUD / API con llave)

def aprobar(sid: str, version: int, permisos: list[str]) -> dict:
    m, codigo, _ = cargar(sid, version)
    pedidos = set(m.get('permisos', []))
    permisos = sorted(set(permisos or []))
    if not set(permisos) <= pedidos:
        raise ValueError('Sólo podés conceder permisos que la habilidad declaró.')
    reporte = probar(m, codigo)                         # se vuelve a probar en el momento de aprobar
    if not reporte['aprobada']:
        raise ValueError('La habilidad no pasa sus pruebas: no se puede instalar.')
    with _LOCK:
        d = _estado()
        info = d['skills'][sid]
        info.update(estado='instalada', version_instalada=int(version), permisos_aprobados=permisos,
                    instalada=datetime.now().isoformat(timespec='seconds'))
        _guardar(d)
    _registro('aprobada', f'{sid} v{version} permisos={",".join(permisos) or "ninguno"}')
    try:
        from . import sky_metricas
        sky_metricas.registrar('servicio', 'habilidad_instalada', True, detalle=f'{sid} v{version}')
    except Exception:
        pass
    return {'id': sid, 'estado': 'instalada', 'version': int(version), 'permisos': permisos}


def desactivar(sid: str) -> bool:
    with _LOCK:
        d = _estado()
        info = d['skills'].get(sid)
        if not info or info.get('estado') != 'instalada':
            return False
        info['estado'] = 'desactivada'
        info['permisos_aprobados'] = []
        _guardar(d)
    _registro('desactivada', sid)
    return True


def eliminar(sid: str) -> bool:
    with _LOCK:
        d = _estado()
        if sid not in d['skills']:
            return False
        d['skills'].pop(sid)
        _guardar(d)
    shutil.rmtree(base() / sid, ignore_errors=True)
    _registro('eliminada', sid)
    return True


# ------------------------------------------------------------------ uso

def _fuentes(m: dict, permisos: list[str], entrada: str) -> dict:
    datos = {}
    if os.getenv('SKY_INTERNET', '1').strip() == '0':
        return datos
    for f in m.get('fuentes', []):
        url = f['url'].replace('{entrada}', urllib.parse.quote(entrada[:200]))
        host = urllib.parse.urlsplit(url).hostname or ''
        if urllib.parse.urlsplit(url).scheme != 'https' or f'internet:{host}' not in permisos:
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'SKY-IA/12.4 (habilidad ' + m['id'] + ')'})
            with urllib.request.urlopen(req, timeout=10) as r:
                crudo = r.read(MAX_FUENTE + 1)[:MAX_FUENTE].decode('utf-8', 'replace')
            try:
                datos[f['nombre']] = json.loads(crudo)
            except ValueError:
                datos[f['nombre']] = crudo
        except Exception:
            datos[f['nombre']] = None
    return datos


def instaladas() -> list[tuple[dict, dict]]:
    salida = []
    for sid, info in _estado()['skills'].items():
        if info.get('estado') == 'instalada' and info.get('version_instalada'):
            try:
                m, _, _ = cargar(sid, info['version_instalada'])
                salida.append((m, info))
            except (KeyError, OSError, ValueError):
                continue
    return salida


def ejecutar_si_coincide(texto: str) -> dict | None:
    t = _norm(texto)
    from .sky_capacidades import parada_activa
    if parada_activa() and any(t == d or t.startswith(d + ' ') for m, _ in instaladas() for d in m['disparadores']):
        return {'tipo': 'respuesta', 'proveedor': 'sky-sentinel',
                'mensaje': 'SKY está en parada de emergencia: las habilidades instaladas están suspendidas.'}
    for m, info in instaladas():
        disp = next((d for d in m['disparadores'] if t == d or t.startswith(d + ' ')), None)
        if not disp:
            continue
        entrada = t[len(disp):].strip()
        from .sky_aprendizaje import _recuperar
        entrada = _recuperar(texto, entrada) if entrada else ''
        _, codigo, _ = cargar(m['id'], info['version_instalada'])
        if validar_codigo(codigo):                       # el archivo cambió en disco: no se ejecuta
            return {'tipo': 'error', 'mensaje': f"La habilidad «{m['nombre']}» fue modificada fuera de SKY; aprobala de nuevo."}
        inicio = time.perf_counter()
        r = ejecutar_aislado(codigo, [{'entrada': entrada, 'contexto': {'fuentes': _fuentes(m, info['permisos_aprobados'], entrada),
                                                                        'hoy': datetime.now().isoformat(timespec='seconds')}}], timeout=12)
        res = (r.get('resultados') or [{}])[0]
        try:
            from . import sky_metricas
            sky_metricas.registrar('accion', 'habilidad:' + m['id'][:30], bool(r.get('ok') and res.get('ok')),
                                   (time.perf_counter() - inicio) * 1000, detalle=r.get('error') or res.get('error', ''))
        except Exception:
            pass
        if not r.get('ok') or not res.get('ok'):
            return {'tipo': 'error', 'mensaje': f"La habilidad «{m['nombre']}» falló: " + (r.get('error') or res.get('error', ''))[:200]}
        salida = res['salida']
        acciones = []
        if salida['acciones'] and 'acciones' in info['permisos_aprobados']:
            from .sky_rutinas import ejecutar_rutina
            acciones = ejecutar_rutina({'nombre': m['nombre'], 'pasos': [{'tipo': 'orden', 'texto': a['orden']} for a in salida['acciones']]})['acciones']
        return {'tipo': 'respuesta', 'mensaje': salida['decir'] or 'Listo.', 'proveedor': 'habilidad:' + m['id'],
                'acciones': acciones, 'habilidad': m['id']}
    return None


# ------------------------------------------------------------------ órdenes por voz

def interpretar(texto: str) -> dict | None:
    t = _norm(texto)
    m = re.fullmatch(r'(?:disena|diseña|programa|desarrolla|propon|propone|construye|crea)(?:me)? (?:una )?(?:nueva )?habilidad (?:para|que) (.{6,400})', t)
    if m:
        from .sky_aprendizaje import _recuperar
        pedido = _recuperar(texto, m.group(1))
        try:
            p = proponer(pedido)
        except Exception as exc:
            return {'tipo': 'respuesta', 'proveedor': 'sky-skill-builder', 'modulo': 'habilidades',
                    'mensaje': 'No pude diseñarla: ' + str(exc)[:200] + '. Para programar habilidades necesito un modelo de IA (Ollama, Claude, GPT o Gemini).'}
        rep = p['reporte']
        if rep['aprobada']:
            perm = ', '.join(p['manifiesto']['permisos']) or 'ninguno'
            msg = (f"Diseñé la habilidad «{p['manifiesto']['nombre']}» (v{p['version']}) y pasó sus {len(rep['pruebas'])} pruebas "
                   f"aisladas. Pide estos permisos: {perm}. Revisala y aprobala en Módulos → Habilidades; hasta entonces no está instalada.")
        else:
            msg = (f"Diseñé «{p['manifiesto']['nombre']}», pero no pasó la revisión o las pruebas, así que no se puede instalar. "
                   'Mirá el detalle en Módulos → Habilidades.')
        return {'tipo': 'respuesta', 'proveedor': 'sky-skill-builder', 'modulo': 'habilidades', 'mensaje': msg, 'propuesta_habilidad': p['id']}
    if re.fullmatch(r'(?:que|cuales) habilidades me faltan|que necesidades (?:detectaste|tienes)|que no sabes hacer', t):
        nec = necesidades(6)
        if not nec:
            return {'tipo': 'respuesta', 'proveedor': 'sky-skill-builder', 'mensaje': 'Todavía no detecté pedidos que no pueda resolver.'}
        return {'tipo': 'respuesta', 'proveedor': 'sky-skill-builder', 'modulo': 'habilidades',
                'mensaje': 'Me pediste cosas para las que no tengo habilidad: ' + '; '.join(f"«{n['frase']}» ({n['veces']} veces)" for n in nec) +
                           '. Decí «diseña una habilidad para …» y la preparo para que la apruebes.'}
    m = re.fullmatch(r'(?:aprueba|instala|activa) (?:la )?habilidad (.{2,60})', t)
    if m:
        return {'tipo': 'respuesta', 'proveedor': 'sky-skill-builder', 'modulo': 'habilidades',
                'mensaje': 'Por seguridad, las habilidades nuevas sólo se aprueban en Módulos → Habilidades, viendo su código, pruebas y permisos.'}
    m = re.fullmatch(r'(?:desactiva|deshabilita|revoca(?: los permisos de)?|quitale los permisos a) (?:la )?habilidad (.{2,60})', t)
    if m:
        q = _norm(m.group(1))
        for item in listar():
            if q in (item['id'].replace('-', ' '), _norm(item['nombre'])):
                ok = desactivar(item['id'])
                return {'tipo': 'respuesta', 'proveedor': 'sky-skill-builder',
                        'mensaje': f"Desactivé «{item['nombre']}» y le quité sus permisos." if ok else 'Esa habilidad no estaba activa.'}
        return None   # puede ser una habilidad nativa del catálogo
    return None
