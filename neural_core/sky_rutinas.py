"""SKY v12.1 — Recordatorios, alarmas y rutinas.

Todo vive en tu equipo: ~/.neuralt/sky_agenda.json (recordatorios y rutinas) y
~/.neuralt/sky_avisos.json (avisos que el HUD lee en voz alta).

Órdenes:
    "recuérdame en 10 minutos sacar la ropa"     "recordame a las 5 llamar a mamá"
    "recuérdame mañana a las 8 la reunión"        "pon una alarma a las 6:30"
    "despiértame a las 7"                          "qué recordatorios tengo"
    "buenos días"  (rutina por defecto: saludo, recordatorios del día y correos nuevos)

Las rutinas con hora se ejecutan solas en el horario indicado. Sus pasos de tipo
'accion' respetan la política del agente: lo que no es automático queda pendiente
de confirmación en el HUD.
"""
from __future__ import annotations

import json
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timedelta
from pathlib import Path

AGENDA_PATH = Path.home() / '.neuralt' / 'sky_agenda.json'
AVISOS_PATH = Path.home() / '.neuralt' / 'sky_avisos.json'
_LOCK = threading.Lock()
MAX_RECORDATORIOS = 200
MAX_AVISOS = 60

RUTINA_BUENOS_DIAS = {
    'id': 'buenos-dias', 'nombre': 'Buenos días', 'frases': ['buenos dias', 'buen dia', 'buenas'],
    'hora': None, 'dias': [],
    'pasos': [{'tipo': 'saludo'}, {'tipo': 'recordatorios_hoy'}, {'tipo': 'correo_resumen'}],
}


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s).lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def _leer(path: Path, defecto):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data if isinstance(data, type(defecto)) else defecto
    except (OSError, ValueError):
        return defecto


def _escribir(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def agenda() -> dict:
    data = _leer(AGENDA_PATH, {})
    data.setdefault('recordatorios', [])
    if not isinstance(data.get('rutinas'), list) or not data['rutinas']:
        data['rutinas'] = [dict(RUTINA_BUENOS_DIAS)]
    return data


# ------------------------------------------------------------------ interpretación

_NUM = {'un': 1, 'una': 1, 'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6, 'siete': 7,
        'ocho': 8, 'nueve': 9, 'diez': 10, 'once': 11, 'doce': 12, 'quince': 15, 'veinte': 20,
        'treinta': 30, 'cuarenta': 40, 'cuarenta y cinco': 45, 'media': 30}


def _numero(s: str) -> int | None:
    s = s.strip()
    if s.isdigit():
        return int(s)
    return _NUM.get(s)


def _hora(h: int, m: int, sufijo: str, ahora: datetime, manana: bool, preferir_tarde: bool = True) -> datetime | None:
    sufijo = sufijo.replace('.', '').replace(' ', '')
    if sufijo in ('pm', 'delatarde', 'delanoche') and h < 12:
        h += 12
    if sufijo in ('am', 'delamanana') and h == 12:
        h = 0
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    cuando = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
    if manana:
        cuando += timedelta(days=1)
    elif cuando <= ahora:
        # "a las 5" cuando ya pasaron las 5 a.m.: probar 5 p.m. hoy; si no, mañana
        if preferir_tarde and not sufijo and h < 12 and cuando.replace(hour=h + 12) > ahora:
            cuando = cuando.replace(hour=h + 12)
        else:
            cuando += timedelta(days=1)
    return cuando


def interpretar(texto: str, ahora: datetime | None = None) -> dict | None:
    """Recordatorio, alarma o consulta de agenda; None si no lo es."""
    ahora = ahora or datetime.now()
    t = _norm(texto).strip(' .!?¿¡')
    t = re.sub(r'^(?:sky|oye sky|hey sky)[\s,]+', '', t)
    if re.search(r'\b(que|cuales)\s+(recordatorios|alarmas|pendientes)\b.*\b(tengo|hay)\b|\b(mis|ver)\s+(recordatorios|alarmas)\b', t):
        return {'tipo': 'agenda', 'description': 'Consultar recordatorios y alarmas'}
    m = re.match(r'^(?:pon|pone|programa|activa|crea)(?:me)?\s+(?:una\s+)?alarma\s+(?:a\s+las|para\s+las|a\s+la|para\s+la)\s+'
                 r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.?\s?m\.?|p\.?\s?m\.?|de la manana|de la tarde|de la noche)?(?:\s+de\s+manana|\s+manana)?$', t) \
        or re.match(r'^(?:despiertame|despertame)\s+(?:manana\s+)?a\s+las?\s+(\d{1,2})(?::(\d{2}))?\s*'
                    r'(am|pm|de la manana|de la tarde|de la noche)?$', t)
    if m:
        manana = 'manana' in t.split('alarma')[-1] or t.startswith(('despiertame manana', 'despertame manana'))
        cuando = _hora(int(m.group(1)), int(m.group(2) or 0), m.group(3) or '', ahora, manana, preferir_tarde=False)
        if cuando:
            return {'tipo': 'recordatorio', 'clase': 'alarma', 'texto': 'Alarma', 'cuando': cuando.isoformat(timespec='minutes'),
                    'description': 'Alarma para ' + _humano(cuando, ahora)}
    m = re.match(r'^(?:recuerdame|recordame|recuerdeme|avisame)\s+(.+)$', t)
    if not m:
        return None
    resto = m.group(1)
    cuando, sobra, relativo = None, resto, False
    mm = re.match(r'^en\s+(\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte|treinta|cuarenta|media)\s*'
                  r'(minutos?|mins?|horas?|hora)\s*(?:y\s+media)?\s*(.*)$', resto)
    if mm:
        n = _numero(mm.group(1)) or 0
        delta = timedelta(hours=n) if mm.group(2).startswith('hora') else timedelta(minutes=n)
        if mm.group(1) == 'media':
            delta = timedelta(minutes=30)
        if 'y media' in resto[:30] and mm.group(2).startswith('hora'):
            delta += timedelta(minutes=30)
        cuando, sobra, relativo = ahora + delta, mm.group(3), True
    else:
        mm = re.match(r'^(manana\s+)?a\s+las?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|de la manana|de la tarde|de la noche)?\s*(.*)$', resto) \
            or re.match(r'^(manana\s+)?a\s+la\s+(una)()\s*(am|pm|de la manana|de la tarde|de la noche)?\s*(.*)$', resto)
        if mm:
            h = 1 if mm.group(2) == 'una' else int(mm.group(2))
            cuando = _hora(h, int(mm.group(3) or 0), mm.group(4) or '', ahora, bool(mm.group(1)))
            sobra = mm.group(5)
    if not cuando or cuando - ahora > timedelta(days=370):
        return None
    sobra = re.sub(r'^(?:que\s+|de\s+|para\s+)', '', sobra.strip(' ,.')).strip()
    if not sobra:
        sobra = 'Recordatorio'
    original = _recuperar(texto, sobra)
    return {'tipo': 'recordatorio', 'clase': 'recordatorio', 'texto': original[:300],
            'cuando': cuando.isoformat(timespec='seconds' if relativo else 'minutes'),
            'description': f'Recordarte «{original[:80]}» {_humano(cuando, ahora)}'}


def _recuperar(original: str, normalizado: str) -> str:
    o = _norm(original)
    i = o.find(normalizado)
    if i >= 0 and len(o) == len(original):
        return original[i:i + len(normalizado)]
    return normalizado


def _humano(cuando: datetime, ahora: datetime) -> str:
    dia = 'hoy' if cuando.date() == ahora.date() else 'mañana' if cuando.date() == (ahora + timedelta(days=1)).date() \
        else cuando.strftime('el %d/%m')
    return f'{dia} a las {cuando:%H:%M}'


# ------------------------------------------------------------------ recordatorios

def crear(texto: str, cuando: str, clase: str = 'recordatorio') -> dict:
    momento = datetime.fromisoformat(cuando)
    texto = ' '.join(str(texto).split())[:300] or 'Recordatorio'
    if clase not in ('recordatorio', 'alarma'):
        raise ValueError('Tipo de recordatorio inválido.')
    with _LOCK:
        data = agenda()
        pendientes = [r for r in data['recordatorios'] if not r.get('hecho')]
        if len(pendientes) >= MAX_RECORDATORIOS:
            raise ValueError('Tenés demasiados recordatorios pendientes.')
        item = {'id': uuid.uuid4().hex[:12], 'texto': texto, 'cuando': momento.isoformat(timespec='seconds'),
                'clase': clase, 'creado': datetime.now().isoformat(timespec='seconds'), 'hecho': False}
        data['recordatorios'] = (data['recordatorios'] + [item])[-500:]
        _escribir(AGENDA_PATH, data)
    return item


def pendientes() -> list[dict]:
    return sorted((r for r in agenda()['recordatorios'] if not r.get('hecho')), key=lambda r: r['cuando'])


def borrar(item_id: str) -> bool:
    with _LOCK:
        data = agenda()
        antes = len(data['recordatorios'])
        data['recordatorios'] = [r for r in data['recordatorios'] if r.get('id') != item_id]
        _escribir(AGENDA_PATH, data)
        return len(data['recordatorios']) != antes


def vencidos(ahora: datetime | None = None) -> list[dict]:
    """Devuelve y marca como hechos los recordatorios cuya hora llegó."""
    ahora = ahora or datetime.now()
    salida = []
    with _LOCK:
        data = agenda()
        for r in data['recordatorios']:
            try:
                if not r.get('hecho') and datetime.fromisoformat(r['cuando']) <= ahora:
                    r['hecho'] = True
                    salida.append(dict(r))
            except (KeyError, ValueError):
                r['hecho'] = True
        if salida:
            _escribir(AGENDA_PATH, data)
    return salida


def resumen_hoy(ahora: datetime | None = None) -> str:
    ahora = ahora or datetime.now()
    hoy = [r for r in pendientes() if datetime.fromisoformat(r['cuando']).date() == ahora.date()]
    if not hoy:
        return 'No tenés recordatorios para hoy.'
    partes = [f"a las {datetime.fromisoformat(r['cuando']):%H:%M}, {r['texto']}" for r in hoy[:6]]
    return 'Hoy tenés: ' + '; '.join(partes) + '.'


def describir_agenda() -> str:
    items = pendientes()
    if not items:
        return 'No tenés recordatorios ni alarmas pendientes.'
    ahora = datetime.now()
    return 'Tenés ' + str(len(items)) + ': ' + '; '.join(
        f"{r['texto']} {_humano(datetime.fromisoformat(r['cuando']), ahora)}" for r in items[:8]) + '.'


# ------------------------------------------------------------------ avisos para el HUD

def avisar(texto: str, origen: str = 'sky') -> dict:
    aviso = {'id': uuid.uuid4().hex[:12], 'texto': ' '.join(str(texto).split())[:500], 'origen': origen,
             'at': datetime.now().isoformat(timespec='seconds'), 'visto': False}
    with _LOCK:
        lista = _leer(AVISOS_PATH, [])
        _escribir(AVISOS_PATH, (lista + [aviso])[-MAX_AVISOS:])
    return aviso


def avisos_nuevos() -> list[dict]:
    with _LOCK:
        lista = _leer(AVISOS_PATH, [])
        nuevos = [a for a in lista if not a.get('visto')]
        if nuevos:
            for a in lista:
                a['visto'] = True
            _escribir(AVISOS_PATH, lista)
    return nuevos


# ------------------------------------------------------------------ rutinas

def rutina_por_frase(texto: str) -> dict | None:
    t = _norm(texto).strip(' .!?¿¡,')
    t = re.sub(r'^(?:sky|oye sky|hey sky)[\s,]+', '', t)
    t = re.sub(r'[\s,]+(?:sky|oscar)$', '', t)
    for r in agenda()['rutinas']:
        if any(t == _norm(f) or t == 'rutina ' + _norm(r.get('nombre', '')) for f in r.get('frases', [])):
            return r
        if t in ('ejecuta la rutina ' + _norm(r.get('nombre', '')), 'activa la rutina ' + _norm(r.get('nombre', ''))):
            return r
    return None


def rutinas_programadas(ahora: datetime | None = None) -> list[dict]:
    """Rutinas cuya hora llegó hoy y todavía no corrieron (marca la ejecución)."""
    ahora = ahora or datetime.now()
    salida = []
    with _LOCK:
        data = agenda()
        for r in data['rutinas']:
            hora = r.get('hora')
            if not hora or not re.fullmatch(r'\d{1,2}:\d{2}', str(hora)):
                continue
            dias = r.get('dias') or list(range(7))
            if ahora.weekday() not in dias:
                continue
            h, m = (int(x) for x in str(hora).split(':'))
            objetivo = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
            if objetivo <= ahora < objetivo + timedelta(minutes=30) and r.get('ultima') != ahora.date().isoformat():
                r['ultima'] = ahora.date().isoformat()
                salida.append(dict(r))
        if salida:
            _escribir(AGENDA_PATH, data)
    return salida


def guardar_rutina(rutina: dict) -> dict:
    """Crea o reemplaza una rutina validada (pasos: saludo, recordatorios_hoy, correo_resumen, decir, accion)."""
    nombre = ' '.join(str(rutina.get('nombre', '')).split())[:60]
    if not nombre:
        raise ValueError('La rutina necesita un nombre.')
    pasos = []
    for p in rutina.get('pasos', [])[:12]:
        tipo = p.get('tipo') if isinstance(p, dict) else None
        if tipo in ('saludo', 'recordatorios_hoy', 'correo_resumen'):
            pasos.append({'tipo': tipo})
        elif tipo == 'decir' and str(p.get('texto', '')).strip():
            pasos.append({'tipo': 'decir', 'texto': str(p['texto'])[:300]})
        elif tipo == 'accion' and isinstance(p.get('params', {}), dict):
            from .sky_capacidades import ACCION_A_CAPACIDAD
            if p.get('action') in ACCION_A_CAPACIDAD:
                pasos.append({'tipo': 'accion', 'action': p['action'], 'params': p.get('params', {}),
                              'description': str(p.get('description', p['action']))[:120]})
    if not pasos:
        raise ValueError('La rutina no tiene pasos válidos.')
    hora = rutina.get('hora')
    if hora is not None and not re.fullmatch(r'([01]?\d|2[0-3]):[0-5]\d', str(hora)):
        raise ValueError('Hora inválida (usá HH:MM).')
    item = {'id': re.sub(r'[^a-z0-9-]+', '-', _norm(nombre)).strip('-')[:40] or uuid.uuid4().hex[:8],
            'nombre': nombre, 'frases': [_norm(f)[:60] for f in rutina.get('frases', []) if str(f).strip()][:6] or [_norm(nombre)],
            'hora': hora, 'dias': [d for d in rutina.get('dias', []) if isinstance(d, int) and 0 <= d <= 6], 'pasos': pasos}
    with _LOCK:
        data = agenda()
        data['rutinas'] = [r for r in data['rutinas'] if r.get('id') != item['id']] + [item]
        _escribir(AGENDA_PATH, data)
    return item


def ejecutar_rutina(rutina: dict, ahora: datetime | None = None) -> dict:
    """Arma lo que SKY dice y ejecuta. Las acciones pasan por la política del agente."""
    ahora = ahora or datetime.now()
    frases, acciones = [], []
    for p in rutina.get('pasos', []):
        tipo = p.get('tipo')
        if tipo == 'saludo':
            momento = 'Buenos días' if ahora.hour < 12 else 'Buenas tardes' if ahora.hour < 19 else 'Buenas noches'
            frases.append(f'{momento}, Oscar. Son las {ahora:%H:%M}.')
        elif tipo == 'recordatorios_hoy':
            frases.append(resumen_hoy(ahora))
        elif tipo == 'correo_resumen':
            try:
                from . import sky_correo
                if sky_correo.configurado():
                    frases.append(sky_correo.resumen_para_voz())
            except Exception:
                frases.append('No pude revisar tu correo.')
        elif tipo == 'decir':
            frases.append(p.get('texto', ''))
        elif tipo == 'accion':
            acciones.append({'action': p['action'], 'params': p.get('params', {}), 'description': p.get('description', p['action'])})
    resultados = []
    for a in acciones:
        try:
            from .sky_asistente_personal import ejecutar_local_si_autorizado
            hecho = ejecutar_local_si_autorizado(a)
        except Exception as exc:
            hecho = {'ok': False, 'error': str(exc)[:120]}
        if hecho is None:
            from .voz_inbox import add_inbox
            add_inbox('rutina ' + rutina.get('nombre', ''), a)
            resultados.append({'description': a['description'], 'estado': 'pendiente'})
        else:
            resultados.append({'description': a['description'], 'estado': 'ok' if hecho.get('ok', True) else 'error'})
    if any(r['estado'] == 'pendiente' for r in resultados):
        frases.append('Dejé algunas acciones pendientes de tu confirmación.')
    return {'mensaje': ' '.join(f for f in frases if f), 'acciones': resultados}
