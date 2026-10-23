"""sky-business-manager — proyectos y emprendimientos: tareas, responsables, fechas, avance y atrasos.

    "crea el proyecto Tienda online"                      "agrega la tarea diseñar el logo al proyecto tienda online para el viernes"
    "marca hecha la tarea diseñar el logo"                "cómo va el proyecto tienda online"
    "qué proyectos tengo"                                  "qué tareas están atrasadas"
    "archiva el proyecto tienda online"
Datos en ~/.neuralt/sky_proyectos.json (tu PC).
"""
from __future__ import annotations

import json
import re
import threading
import unicodedata
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

_LOCK = threading.Lock()
DIAS = {'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3, 'viernes': 4, 'sabado': 5, 'domingo': 6}


def ruta() -> Path:
    return Path.home() / '.neuralt' / 'sky_proyectos.json'


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '').lower())
    return ' '.join(re.sub(r'[^\w\s/-]', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).split())


def _datos() -> dict:
    try:
        d = json.loads(ruta().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) and isinstance(d.get('proyectos'), list) else {'proyectos': []}
    except (OSError, ValueError):
        return {'proyectos': []}


def _guardar(d: dict) -> None:
    p = ruta()
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(p)


def fecha_desde_texto(t: str, hoy: date | None = None) -> str | None:
    hoy = hoy or date.today()
    if re.search(r'\bhoy\b', t):
        return hoy.isoformat()
    if re.search(r'\bpasado manana\b', t):
        return (hoy + timedelta(days=2)).isoformat()
    if re.search(r'\bmanana\b', t):
        return (hoy + timedelta(days=1)).isoformat()
    m = re.search(r'\b(?:el )?(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b', t)
    if m:
        delta = (DIAS[m.group(1)] - hoy.weekday()) % 7 or 7
        return (hoy + timedelta(days=delta)).isoformat()
    m = re.search(r'\ben (\d{1,2}) (dias|semanas)\b', t)
    if m:
        n = int(m.group(1)) * (7 if m.group(2) == 'semanas' else 1)
        return (hoy + timedelta(days=n)).isoformat()
    m = re.search(r'\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b', t)
    if m:
        try:
            return date(int(m.group(3) or hoy.year), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    return None


def _buscar(d: dict, nombre: str) -> dict | None:
    q = _norm(nombre)
    activos = [p for p in d['proyectos'] if not p.get('archivado')]
    return next((p for p in activos if _norm(p['nombre']) == q), None) or \
        next((p for p in activos if q and q in _norm(p['nombre'])), None)


def crear(nombre: str) -> dict:
    nombre = ' '.join(str(nombre).split())[:80]
    if len(nombre) < 2:
        raise ValueError('El proyecto necesita un nombre.')
    with _LOCK:
        d = _datos()
        if _buscar(d, nombre) and _norm(_buscar(d, nombre)['nombre']) == _norm(nombre):
            raise ValueError(f'Ya existe el proyecto «{nombre}».')
        p = {'id': uuid.uuid4().hex[:8], 'nombre': nombre, 'creado': date.today().isoformat(), 'tareas': [], 'archivado': False}
        d['proyectos'].append(p)
        _guardar(d)
    return p


def agregar_tarea(proyecto: str, tarea: str, vence: str | None = None, responsable: str = '') -> dict:
    with _LOCK:
        d = _datos()
        p = _buscar(d, proyecto)
        if not p:
            raise KeyError(proyecto)
        t = {'id': uuid.uuid4().hex[:8], 'texto': ' '.join(tarea.split())[:200], 'vence': vence, 'hecha': False,
             'responsable': responsable[:60]}
        p['tareas'].append(t)
        _guardar(d)
    return {**t, 'proyecto': p['nombre']}


def marcar_hecha(tarea: str) -> dict | None:
    q = _norm(tarea)
    with _LOCK:
        d = _datos()
        for p in d['proyectos']:
            for t in p['tareas']:
                if not t['hecha'] and q and (q == _norm(t['texto']) or q in _norm(t['texto'])):
                    t['hecha'], t['hecha_en'] = True, date.today().isoformat()
                    _guardar(d)
                    try:
                        from . import sky_metricas
                        sky_metricas.registrar('tarea', 'proyecto_completada', True, detalle=p['nombre'][:60])
                    except Exception:
                        pass
                    return {**t, 'proyecto': p['nombre']}
    return None


def resumen(proyecto: dict, hoy: date | None = None) -> dict:
    hoy = (hoy or date.today()).isoformat()
    total = len(proyecto['tareas'])
    hechas = sum(1 for t in proyecto['tareas'] if t['hecha'])
    atrasadas = [t for t in proyecto['tareas'] if not t['hecha'] and t.get('vence') and t['vence'] < hoy]
    proximas = sorted((t for t in proyecto['tareas'] if not t['hecha'] and t.get('vence') and t['vence'] >= hoy),
                      key=lambda t: t['vence'])[:3]
    return {'nombre': proyecto['nombre'], 'total': total, 'hechas': hechas,
            'avance': round(hechas / total * 100) if total else 0, 'atrasadas': atrasadas, 'proximas': proximas,
            'pendientes': [t for t in proyecto['tareas'] if not t['hecha']]}


def describir(proyecto: dict, hoy: date | None = None) -> str:
    r = resumen(proyecto, hoy)
    if not r['total']:
        return f"El proyecto «{r['nombre']}» todavía no tiene tareas."
    txt = f"«{r['nombre']}» va al {r['avance']} %: {r['hechas']} de {r['total']} tareas hechas."
    if r['atrasadas']:
        txt += ' Atrasadas: ' + '; '.join(f"{t['texto']} (vencía {t['vence']})" for t in r['atrasadas'][:4]) + '.'
    if r['proximas']:
        txt += ' Próximas: ' + '; '.join(f"{t['texto']} ({t['vence']})" for t in r['proximas']) + '.'
    return txt


def _orig(texto: str, fragmento: str) -> str:
    from .sky_aprendizaje import _recuperar
    return _recuperar(texto, fragmento) if fragmento else fragmento


def _resp(msg: str) -> dict:
    return {'tipo': 'respuesta', 'mensaje': msg, 'proveedor': 'sky-business-manager'}


def interpretar(texto: str, hoy: date | None = None) -> dict | None:
    t = _norm(texto)
    t = re.sub(r'^(?:oye |hey )?sky\s+', '', t)
    m = re.fullmatch(r'(?:crea|crear|nuevo|empieza) (?:un |el )?(?:nuevo )?proyecto (?:llamado |que se llame )?(.{2,80})', t)
    if m:
        try:
            p = crear(_orig(texto, m.group(1)))
        except ValueError as exc:
            return _resp(str(exc))
        return _resp(f"Creé el proyecto «{p['nombre']}». Agregale tareas: «agrega la tarea X al proyecto {p['nombre']} para el viernes».")
    m = re.fullmatch(r'(?:agrega|anade|suma|pon) (?:la )?tarea (.{2,200}?) (?:al|en el|para el) proyecto (.{2,80}?)'
                     r'(?: (?:para|antes del?|el|hasta el?) (.{2,30}))?(?: (?:a cargo de|responsable) (.{2,40}))?', t)
    if m:
        vence = fecha_desde_texto(m.group(3) or '', hoy) if m.group(3) else None
        try:
            r = agregar_tarea(m.group(2), _orig(texto, m.group(1)), vence, _orig(texto, m.group(4) or ''))
        except KeyError:
            return _resp(f'No tengo un proyecto llamado «{m.group(2)}». Decí «crea el proyecto {m.group(2)}».')
        return _resp(f"Agregué «{r['texto']}» a «{r['proyecto']}»" + (f", para el {vence}." if vence else '.'))
    m = re.fullmatch(r'(?:marca|marcar) (?:como )?(?:hecha|terminada|completada|lista) (?:la tarea )?(.{2,200})|'
                     r'(?:termine|complete|hice) (?:la tarea )?(.{2,200})', t)
    if m:
        r = marcar_hecha(m.group(1) or m.group(2))
        return _resp(f"Hecho: «{r['texto']}» en «{r['proyecto']}»." if r else 'No encontré esa tarea pendiente.')
    m = re.fullmatch(r'como (?:va|vamos con|esta) (?:el )?proyecto (.{2,80})|(?:avance|estado) del proyecto (.{2,80})', t)
    if m:
        p = _buscar(_datos(), m.group(1) or m.group(2))
        return _resp(describir(p, hoy) if p else 'No encontré ese proyecto.')
    if re.fullmatch(r'(?:que|cuales) proyectos tengo|mis proyectos|(?:muestra(?:me)?|lista) (?:mis |los )?proyectos', t):
        activos = [p for p in _datos()['proyectos'] if not p.get('archivado')]
        if not activos:
            return _resp('No tenés proyectos. Decí «crea el proyecto Tienda online».')
        return _resp('Tus proyectos: ' + '; '.join(f"{p['nombre']} ({resumen(p, hoy)['avance']} %)" for p in activos) + '.')
    if re.fullmatch(r'(?:que|cuales) tareas (?:estan|tengo|hay) atrasadas|tareas atrasadas', t):
        atrasadas = [(p['nombre'], x) for p in _datos()['proyectos'] if not p.get('archivado') for x in resumen(p, hoy)['atrasadas']]
        if not atrasadas:
            return _resp('No tenés tareas atrasadas.')
        return _resp(f'Tenés {len(atrasadas)} atrasadas: ' + '; '.join(f"{x['texto']} ({n}, vencía {x['vence']})" for n, x in atrasadas[:6]) + '.')
    m = re.fullmatch(r'(?:archiva|cierra|termina) (?:el )?proyecto (.{2,80})', t)
    if m:
        with _LOCK:
            d = _datos()
            p = _buscar(d, m.group(1))
            if p:
                p['archivado'] = True
                _guardar(d)
        return _resp(f"Archivé «{p['nombre']}»." if p else 'No encontré ese proyecto.')
    return None
