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
    try:
        from .sky_capacidades import parada_activa
        if parada_activa():
            return []   # SENTINEL: con la parada de emergencia activa no corre ninguna automatización
    except Exception:
        return []
    with _LOCK:
        data = agenda()
        for r in data['rutinas']:
            hora = r.get('hora')
            if not hora or not re.fullmatch(r'\d{1,2}:\d{2}', str(hora)) or r.get('activa') is False:
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


PASOS_SIMPLES = ('saludo', 'recordatorios_hoy', 'correo_resumen', 'correo_borradores', 'intereses', 'borradores_pendientes')


def validar_pasos(pasos_crudos) -> list[dict]:
    """Pasos admitidos en rutinas, skills y tareas programadas (v12.3). Todo lo demás se descarta."""
    from .sky_capacidades import ACCION_A_CAPACIDAD
    pasos = []
    for p in list(pasos_crudos or [])[:12]:
        tipo = p.get('tipo') if isinstance(p, dict) else None
        texto = ' '.join(str(p.get('texto', '') if isinstance(p, dict) else '').split())
        if tipo in PASOS_SIMPLES:
            pasos.append({'tipo': tipo})
        elif tipo == 'decir' and texto:
            pasos.append({'tipo': 'decir', 'texto': texto[:300]})
        elif tipo == 'orden' and texto:
            pasos.append({'tipo': 'orden', 'texto': texto[:200]})
        elif tipo in ('noticias', 'aprender') and str(p.get('tema', '')).strip():
            pasos.append({'tipo': tipo, 'tema': ' '.join(str(p['tema']).split())[:100]})
        elif tipo == 'kpi':
            pasos.append({'tipo': 'kpi', 'diagnostico': bool(p.get('diagnostico'))})
        elif tipo == 'skill' and re.fullmatch(r'[a-z0-9-]{1,40}', str(p.get('id', ''))):
            pasos.append({'tipo': 'skill', 'id': str(p['id'])})
        elif tipo == 'accion' and isinstance(p.get('params', {}), dict) and p.get('action') in ACCION_A_CAPACIDAD:
            pasos.append({'tipo': 'accion', 'action': p['action'], 'params': p.get('params', {}),
                          'description': str(p.get('description', p['action']))[:120]})
    if not pasos:
        raise ValueError('No hay pasos válidos.')
    return pasos


def activar_rutina(rutina_id: str, activa: bool) -> dict | None:
    with _LOCK:
        data = agenda()
        for r in data['rutinas']:
            if r.get('id') == rutina_id:
                r['activa'] = bool(activa)
                _escribir(AGENDA_PATH, data)
                return r
    return None


def borrar_rutina(rutina_id: str) -> bool:
    with _LOCK:
        data = agenda()
        antes = len(data['rutinas'])
        data['rutinas'] = [r for r in data['rutinas'] if r.get('id') != rutina_id]
        _escribir(AGENDA_PATH, data)
        return len(data['rutinas']) != antes


def guardar_rutina(rutina: dict) -> dict:
    """Crea o reemplaza una rutina validada (pasos: saludo, recordatorios_hoy, correo_resumen, decir, accion)."""
    nombre = ' '.join(str(rutina.get('nombre', '')).split())[:60]
    if not nombre:
        raise ValueError('La rutina necesita un nombre.')
    pasos = validar_pasos(rutina.get('pasos', []))
    if not pasos:
        raise ValueError('La rutina no tiene pasos válidos.')
    hora = rutina.get('hora')
    if hora is not None and not re.fullmatch(r'([01]?\d|2[0-3]):[0-5]\d', str(hora)):
        raise ValueError('Hora inválida (usá HH:MM).')
    item = {'id': re.sub(r'[^a-z0-9-]+', '-', _norm(nombre)).strip('-')[:40] or uuid.uuid4().hex[:8],
            'nombre': nombre, 'frases': [_norm(f)[:60] for f in rutina.get('frases', []) if str(f).strip()][:6] or [_norm(nombre)],
            'hora': hora, 'dias': [d for d in rutina.get('dias', []) if isinstance(d, int) and 0 <= d <= 6], 'pasos': pasos,
            'activa': rutina.get('activa', True) is not False}
    with _LOCK:
        data = agenda()
        data['rutinas'] = [r for r in data['rutinas'] if r.get('id') != item['id']] + [item]
        _escribir(AGENDA_PATH, data)
    return item


def _orden(texto: str) -> dict:
    """Un paso «orden»: se interpreta con las reglas (sin IA) y se ejecuta según los permisos del dueño."""
    from . import sky_asistente_personal as asis
    propuesta = asis.interpretar(texto)
    if propuesta:
        return {'tipo': 'accion', 'propuesta': propuesta}
    r = interpretar(texto)
    if r:
        return asis.resolver_especial(r)
    try:
        from . import sky_home_assistant as casa
        orden = casa.interpretar(texto)
        if orden:
            return {'tipo': 'casa', 'propuesta': orden}
    except Exception:
        pass
    return {'tipo': 'error', 'mensaje': f'No entendí la orden «{texto}».'}


def ejecutar_rutina(rutina: dict, ahora: datetime | None = None, _nivel: int = 0) -> dict:
    """Arma lo que SKY dice y ejecuta. Las acciones pasan por la política del agente:
    lo que no es automático queda pendiente de tu confirmación. Nada de nivel 3 se ejecuta solo."""
    ahora = ahora or datetime.now()
    frases, acciones, casas = [], [], []
    for p in rutina.get('pasos', []):
        tipo = p.get('tipo')
        try:
            if tipo == 'saludo':
                momento = 'Buenos días' if ahora.hour < 12 else 'Buenas tardes' if ahora.hour < 19 else 'Buenas noches'
                frases.append(f'{momento}, Oscar. Son las {ahora:%H:%M}.')
            elif tipo == 'recordatorios_hoy':
                frases.append(resumen_hoy(ahora))
            elif tipo == 'correo_resumen':
                from . import sky_correo
                if sky_correo.configurado():
                    frases.append(sky_correo.resumen_para_voz())
            elif tipo == 'correo_borradores':
                from . import sky_correo, sky_borradores
                if not sky_correo.configurado():
                    frases.append('No preparé borradores: el correo no está configurado.')
                else:
                    r = sky_borradores.preparar()
                    if r['nuevos']:
                        frases.append(f"Te preparé {len(r['nuevos'])} borradores de respuesta; esperan tu aprobación.")
                    elif r['error']:
                        frases.append('No pude redactar borradores: ' + r['error'])
                    else:
                        frases.append('No hay correos nuevos para responder.')
            elif tipo == 'borradores_pendientes':
                from . import sky_borradores
                frases.append(sky_borradores.describir())
            elif tipo == 'decir':
                frases.append(p.get('texto', ''))
            elif tipo == 'kpi':
                from . import sky_metricas
                datos = sky_metricas.resumen('hoy', ahora)
                frases.append(sky_metricas.diagnosticar(datos) if p.get('diagnostico') else sky_metricas.describir(datos))
            elif tipo == 'noticias':
                from . import sky_aprendizaje
                items = sky_aprendizaje.noticias_de(p['tema'], 3)
                frases.append(f"Sobre {p['tema']}: " + '; '.join(i['titular'] for i in items) + '.' if items
                              else f"No encontré noticias de {p['tema']}.")
            elif tipo == 'aprender':
                from . import sky_aprendizaje
                frases.append(f"Aprendí sobre {p['tema']}: " + sky_aprendizaje.aprender_tema(p['tema'])['resumen'])
            elif tipo == 'intereses':
                from . import sky_aprendizaje
                hechos = sky_aprendizaje.actualizar_intereses(ahora, maximo=5)
                if hechos:
                    frases.append('Novedades de tus temas: ' + '; '.join(hechos) + '.')
            elif tipo == 'skill' and _nivel < 3:
                from . import sky_skills
                sk = sky_skills.obtener(p['id'])
                if sk:
                    sub = ejecutar_rutina(sk, ahora, _nivel + 1)
                    frases.append(sub['mensaje'])
                    casas.extend(sub['acciones'])
                else:
                    frases.append(f"No encontré la skill «{p['id']}».")
            elif tipo == 'accion':
                acciones.append({'action': p['action'], 'params': p.get('params', {}), 'description': p.get('description', p['action'])})
            elif tipo == 'orden':
                r = _orden(p['texto'])
                if r['tipo'] == 'accion':
                    acciones.append(r['propuesta'])
                elif r['tipo'] == 'casa':
                    casas.append(_casa_paso(r['propuesta']))
                elif r.get('mensaje'):
                    frases.append(r['mensaje'])
        except Exception as exc:   # un paso que falla no frena la rutina, pero se informa
            frases.append(f'No pude completar un paso ({tipo}): {str(exc)[:100]}.')
    resultados = list(casas)
    for a in acciones:
        try:
            from .sky_asistente_personal import ejecutar_local_si_autorizado
            hecho = ejecutar_local_si_autorizado(a, origen='programada')
        except Exception as exc:
            hecho = {'ok': False, 'error': str(exc)[:120]}
        from .sky_asistente_personal import describir_resultado
        estado, _ = describir_resultado(hecho)
        if hecho is None:
            from .voz_inbox import add_inbox
            add_inbox('rutina ' + rutina.get('nombre', ''), a)
            resultados.append({'description': a['description'], 'estado': 'pendiente'})
        else:
            # v12.6: 'verificada' ≠ 'enviada' ≠ 'bloqueada'; antes todo lo que no fallaba se informaba como 'ok'.
            resultados.append({'description': a['description'],
                               'estado': {'verificada': 'ok', 'enviada': 'enviada'}.get(estado, estado if estado == 'bloqueada' else 'error')})
    if _nivel == 0 and any(r['estado'] == 'pendiente' for r in resultados):
        frases.append('Dejé algunas acciones pendientes de tu confirmación.')
    if _nivel == 0 and any(r['estado'] == 'bloqueada' for r in resultados):
        frases.append('Algunas acciones esperan tu PIN: SKY estaba bloqueada.')
    if _nivel == 0 and any(r['estado'] == 'no_ejecutada' for r in resultados):
        frases.append('Hay órdenes de la casa que no ejecuté porque necesitan tu confirmación en el momento.')
    return {'mensaje': ' '.join(f for f in frases if f), 'acciones': resultados}


def _casa_paso(orden: dict) -> dict:
    from . import sky_capacidades as caps
    if orden.get('requiere_confirmacion') or caps.parada_activa():
        # La casa no tiene bandeja de pendientes: lo sensible (cerraduras, clima, cortinas) se pide en el momento.
        return {'description': orden['description'], 'estado': 'no_ejecutada',
                'motivo': 'requiere tu confirmación: pedímelo directamente'}
    try:
        from . import sky_home_assistant as casa
        res = casa.ejecutar(orden['service'], orden['entity_ids'], orden.get('data', {}))
        return {'description': orden['description'], 'estado': 'ok' if res.get('ok', True) else 'error'}
    except Exception as exc:
        return {'description': orden['description'], 'estado': 'error', 'error': str(exc)[:120]}
