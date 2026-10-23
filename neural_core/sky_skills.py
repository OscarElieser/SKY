"""SKY v12.3 — Skills (procedimientos de varios pasos) y tareas programadas por voz.

Una skill es un archivo ~/.neuralt/skills/<id>.json:
    {"nombre": "Modo trabajo", "descripcion": "...", "frases": ["modo trabajo"],
     "pasos": [{"tipo": "orden", "texto": "abre Word"}, {"tipo": "orden", "texto": "pon lofi para estudiar"}]}
Pasos: orden, decir, saludo, recordatorios_hoy, correo_resumen, correo_borradores, borradores_pendientes,
noticias{tema}, aprender{tema}, intereses, kpi{diagnostico}, skill{id}, accion{action, params}.
Todo pasa por los permisos del dueño: lo que no es automático queda pendiente y nada de nivel 3 se ejecuta solo.

Por voz:
    "qué skills tienes"                     "ejecuta la skill resumen del día"
    "crea una skill modo trabajo que abra Word, ponga lofi para estudiar y baje el volumen al 30"
    "olvida la skill modo trabajo"
    "todos los días a las 8 prepara las respuestas de los correos"
    "de lunes a viernes a las 7:30 haz el resumen del día"
    "qué tareas programadas tengo"          "pausa la tarea resumen del día"   "activa…"   "borra la tarea…"
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

MAX_SKILLS = 60

INTEGRADAS = [
    {'id': 'resumen-del-dia', 'nombre': 'Resumen del día', 'integrada': True,
     'descripcion': 'Saludo, recordatorios de hoy, correos nuevos, borradores pendientes y novedades de tus temas.',
     'frases': ['resumen del dia', 'que tenemos para hoy', 'que tengo para hoy'],
     'pasos': [{'tipo': 'saludo'}, {'tipo': 'recordatorios_hoy'}, {'tipo': 'correo_resumen'},
               {'tipo': 'borradores_pendientes'}, {'tipo': 'intereses'}]},
    {'id': 'preparar-respuestas-correo', 'nombre': 'Preparar respuestas de correo', 'integrada': True,
     'descripcion': 'Redacta borradores para los correos no leídos. No envía nada: cada envío lo aprobás vos.',
     'frases': ['prepara las respuestas de los correos', 'preparame las respuestas de los correos', 'responder correos',
                'prepara respuestas de correo'],
     'pasos': [{'tipo': 'correo_borradores'}]},
    {'id': 'novedades-de-mis-temas', 'nombre': 'Novedades de mis temas', 'integrada': True,
     'descripcion': 'Lee las noticias de los temas que sigo y las guarda.',
     'frases': ['novedades de mis temas', 'que hay de nuevo en mis temas'],
     'pasos': [{'tipo': 'intereses'}]},
    {'id': 'revisar-rendimiento', 'nombre': 'Revisar rendimiento', 'integrada': True,
     'descripcion': 'Diagnóstico con mis KPIs reales.',
     'frases': ['revisa tu rendimiento', 'revision de rendimiento'],
     'pasos': [{'tipo': 'kpi', 'diagnostico': True}]},
]

DIAS = {'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3, 'viernes': 4, 'sabado': 5, 'domingo': 6}


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'^(?:oye |hey |ok )?sky[\s,]+', '', s.strip())
    return ' '.join(re.sub(r'[^\w\s:,]', ' ', s).split())


def _slug(nombre: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', _norm(nombre)).strip('-')[:40]


def carpeta() -> Path:
    return Path.home() / '.neuralt' / 'skills'


def _propias() -> list[dict]:
    salida = []
    d = carpeta()
    if not d.is_dir():
        return salida
    for f in sorted(d.glob('*.json'))[:MAX_SKILLS]:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            from .sky_rutinas import validar_pasos
            salida.append({'id': f.stem, 'nombre': str(data.get('nombre') or f.stem)[:60],
                           'descripcion': str(data.get('descripcion', ''))[:300],
                           'frases': [_norm(x)[:60] for x in data.get('frases', []) if str(x).strip()][:6],
                           'pasos': validar_pasos(data.get('pasos')), 'integrada': False})
        except (OSError, ValueError, AttributeError):
            continue   # un archivo roto no rompe a SKY
    return salida


def listar() -> list[dict]:
    propias = _propias()
    ids = {s['id'] for s in propias}
    return [s for s in INTEGRADAS if s['id'] not in ids] + propias


def obtener(skill_id: str) -> dict | None:
    return next((s for s in listar() if s['id'] == skill_id), None)


def buscar(texto: str) -> dict | None:
    t = _norm(texto).strip(' ,')
    t = re.sub(r'^(?:la |el )?(?:skill |habilidad |rutina )?', '', t)
    for s in listar():
        if t in (s['id'].replace('-', ' '), _norm(s['nombre'])) or t in s['frases']:
            return s
    return None


def guardar(skill: dict) -> dict:
    from .sky_rutinas import validar_pasos
    nombre = ' '.join(str(skill.get('nombre', '')).split())[:60]
    sid = _slug(nombre)
    if not sid:
        raise ValueError('La skill necesita un nombre.')
    if any(s['id'] == sid for s in INTEGRADAS):
        raise ValueError('Ese nombre es de una skill integrada; elegí otro.')
    if not (carpeta() / f'{sid}.json').exists() and len(_propias()) >= MAX_SKILLS:
        raise ValueError(f'Llegaste al máximo de {MAX_SKILLS} skills.')
    data = {'nombre': nombre, 'descripcion': str(skill.get('descripcion', ''))[:300],
            'frases': [_norm(x)[:60] for x in (skill.get('frases') or [nombre]) if str(x).strip()][:6],
            'pasos': validar_pasos(skill.get('pasos'))}
    carpeta().mkdir(mode=0o700, parents=True, exist_ok=True)
    (carpeta() / f'{sid}.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'id': sid, **data, 'integrada': False}


def borrar(skill_id: str) -> bool:
    if not re.fullmatch(r'[a-z0-9-]{1,40}', skill_id or ''):
        return False
    try:
        (carpeta() / f'{skill_id}.json').unlink()
        return True
    except FileNotFoundError:
        return False


def ejecutar(skill: dict) -> dict:
    from .sky_rutinas import ejecutar_rutina
    return ejecutar_rutina(skill)


# ------------------------------------------------------------------ pasos desde lenguaje natural

_INFINITIVO = [(r'^abra\b', 'abre'), (r'^ponga\b', 'pon'), (r'^baje\b', 'baja'), (r'^suba\b', 'sube'), (r'^busque\b', 'busca'),
               (r'^reproduzca\b', 'reproduce'), (r'^cierre\b', 'cierra'), (r'^organice\b', 'organiza'), (r'^encienda\b', 'enciende'),
               (r'^apague\b', 'apaga'), (r'^prepare\b', 'prepara'), (r'^lea\b', 'lee'), (r'^tome\b', 'toma'), (r'^silencie\b', 'silencia'),
               (r'^bloquee\b', 'bloquea'), (r'^diga\b', 'di'), (r'^active\b', 'activa'), (r'^muestre\b', 'muestra')]


def _a_imperativo(orden: str) -> str:
    for patron, rep in _INFINITIVO:
        orden = re.sub(patron, rep, orden)
    return orden


def pasos_desde_texto(texto: str) -> tuple[list[dict], list[str]]:
    """«abra Word, ponga lofi y baje el volumen al 30» → pasos. Devuelve (pasos, órdenes no entendidas)."""
    from . import sky_asistente_personal as asis, sky_rutinas
    partes = [p.strip(' ,.') for p in re.split(r',|\by luego\b|\bluego\b|\bdespues\b|\by\b(?= (?:abr|pon|baj|sub|busc|reprod|cierr|organ|enciend|apag|prepar|le|tom|silenc|bloque|dig|activ|muestr|di |haz))', texto) if p.strip(' ,.')]
    pasos, no_entendidas = [], []
    for parte in partes[:12]:
        orden = _a_imperativo(parte)
        sk = buscar(orden) or buscar(re.sub(r'^(?:haz|ejecuta|corre|usa)(?: el| la)? ', '', orden))
        if sk:
            pasos.append({'tipo': 'skill', 'id': sk['id']})
            continue
        m = re.match(r'^(?:di|dime|decime) (?:que )?(.+)$', orden)
        if m:
            pasos.append({'tipo': 'decir', 'texto': m.group(1)})
            continue
        if asis.interpretar(orden) or sky_rutinas.interpretar(orden):
            pasos.append({'tipo': 'orden', 'texto': orden})
        else:
            no_entendidas.append(parte)
    return pasos, no_entendidas


# ------------------------------------------------------------------ tareas programadas

def _hora(t: str) -> str | None:
    m = re.search(r'\ba las (\d{1,2})(?::(\d{2}))?(?: (?:en punto|y media|y cuarto))?\s*(am|a m|pm|p m|de la manana|de la tarde|de la noche|de la madrugada)?', t)
    if not m:
        return None
    h, mi, suf = int(m.group(1)), int(m.group(2) or 0), m.group(3) or ''
    if 'y media' in m.group(0):
        mi = 30
    elif 'y cuarto' in m.group(0):
        mi = 15
    if suf in ('pm', 'p m', 'de la tarde', 'de la noche') and h < 12:
        h += 12
    if suf in ('am', 'a m', 'de la manana', 'de la madrugada') and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    return f'{h:02d}:{mi:02d}'


def _dias(t: str) -> list[int] | None:
    if re.search(r'\b(?:todos los dias|cada dia|diariamente|a diario)\b', t):
        return list(range(7))
    if re.search(r'\b(?:de lunes a viernes|entre semana|dias laborales|dias de semana)\b', t):
        return [0, 1, 2, 3, 4]
    if re.search(r'\b(?:fines de semana|fin de semana)\b', t):
        return [5, 6]
    encontrados = [DIAS[d] for d in re.findall(r'\b(lunes|martes|miercoles|jueves|viernes|sabados?|domingos?)\b', t)
                   for d in [d.rstrip('s') if d.rstrip('s') in DIAS else d]]
    return sorted(set(encontrados)) or None


NOMBRE_DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábados', 'domingos']


def describir_dias(dias: list[int]) -> str:
    if not dias or len(dias) == 7:
        return 'todos los días'
    if dias == [0, 1, 2, 3, 4]:
        return 'de lunes a viernes'
    if dias == [5, 6]:
        return 'los fines de semana'
    return 'los ' + ', '.join(NOMBRE_DIAS[d] for d in dias)


def programadas() -> list[dict]:
    from .sky_rutinas import agenda
    return [r for r in agenda()['rutinas'] if r.get('hora')]


def describir_programadas() -> str:
    lista = programadas()
    if not lista:
        return 'No tenés tareas programadas. Probá: «todos los días a las 8 prepara las respuestas de los correos».'
    partes = [f"{r['nombre']} a las {r['hora']} {describir_dias(r.get('dias') or [])}" + ('' if r.get('activa', True) else ' (pausada)')
              for r in lista]
    return f'Tenés {len(lista)} tareas programadas: ' + '; '.join(partes) + '.'


def _buscar_programada(nombre: str) -> dict | None:
    q = _norm(nombre).strip()
    q = re.sub(r'^(?:la |el )?(?:tarea (?:programada )?(?:de |del )?)?', '', q)
    for r in programadas():
        if q and (q == _norm(r['nombre']) or q == r['id'].replace('-', ' ') or q in _norm(r['nombre'])):
            return r
    return None


def _resp(msg: str, **extra) -> dict:
    return {'tipo': 'respuesta', 'mensaje': msg, 'proveedor': 'sky-skills', **extra}


def interpretar(texto: str) -> dict | None:
    t = _norm(texto).strip(' ,')
    if not t:
        return None
    from . import sky_rutinas
    if re.fullmatch(r'(?:que|cuales) skills (?:tienes|tenes|hay|sabes)', t):
        return _resp('Mis skills: ' + '; '.join(f"{s['nombre']} ({s['descripcion'] or 'sin descripción'})" for s in listar()) + '.',
                     modulo='auto')
    if re.fullmatch(r'(?:que|cuales) (?:tareas programadas|tareas automaticas|automatizaciones) (?:tengo|hay|tienes)|'
                    r'(?:muestra(?:me)?|mostra(?:me)?|abre|ver) (?:mis |las )?(?:tareas programadas|automatizaciones|skills)', t):
        return _resp(describir_programadas(), modulo='auto')
    m = re.fullmatch(r'(?:ejecuta|corre|usa|haz) (?:la |el )?(?:skill|habilidad) (.{2,60})', t)
    if m:
        sk = buscar(m.group(1))
        if not sk:
            return None   # puede ser una habilidad del catálogo o del Skill Builder
        res = ejecutar(sk)
        return _resp(f"{sk['nombre']}. " + (res['mensaje'] or 'Listo.'), acciones=res['acciones'], skill=sk['id'])
    m = re.fullmatch(r'(?:crea|creame|nueva|agrega) (?:una )?(?:skill|habilidad) (?:llamada |que se llame )?(.{2,60}?) '
                     r'(?:que|para que) (.{3,500})', t)
    if m:
        from .sky_aprendizaje import _recuperar
        pasos, malas = pasos_desde_texto(_recuperar(texto, m.group(2)))
        if malas:
            return _resp('No entendí estas partes: «' + '», «'.join(malas) + '». Decilas como órdenes, por ejemplo «abra Word». '
                         'Si necesitás algo nuevo que SKY todavía no sabe hacer, decí «diseña una habilidad para …».')
        try:
            sk = guardar({'nombre': _recuperar(texto, m.group(1)), 'frases': [m.group(1)], 'pasos': pasos})
        except ValueError as exc:
            return _resp(str(exc))
        return _resp(f"Creé la skill «{sk['nombre']}» con {len(pasos)} pasos. Decí «{sk['nombre']}» para usarla.", modulo='auto')
    m = re.fullmatch(r'(?:olvida|borra|elimina) (?:la )?(?:skill|habilidad) (.{2,60})', t)
    if m:
        sk = buscar(m.group(1))
        if sk and sk.get('integrada'):
            return _resp('Esa skill es integrada; no se puede borrar.')
        return _resp('Listo, la borré.' if sk and borrar(sk['id']) else 'No encontré esa skill.')
    m = re.fullmatch(r'(pausa|deten|desactiva|activa|reanuda|borra|elimina|cancela) (?:la )?tarea (?:programada )?(?:de |del )?(.{2,60})', t)
    if m:
        r = _buscar_programada(m.group(2))
        if not r:
            return _resp('No encontré esa tarea programada.')
        if m.group(1) in ('borra', 'elimina', 'cancela'):
            sky_rutinas.borrar_rutina(r['id'])
            return _resp(f"Borré la tarea «{r['nombre']}».", modulo='auto')
        activa = m.group(1) in ('activa', 'reanuda')
        sky_rutinas.activar_rutina(r['id'], activa)
        return _resp(f"{'Activé' if activa else 'Pausé'} la tarea «{r['nombre']}».", modulo='auto')
    # «todos los días a las 8 prepara las respuestas de los correos»
    hora, dias = _hora(t), _dias(t)
    if hora and dias and not re.match(r'^(?:recuerdame|recordame|pon una alarma|despiertame)', t):
        resto = re.sub(r'\ba las \d{1,2}(?::\d{2})?(?: (?:en punto|y media|y cuarto))?\s*(?:am|a m|pm|p m|de la manana|de la tarde|de la noche|de la madrugada)?', ' ', t)
        resto = re.sub(r'\b(?:todos los dias|cada dia|diariamente|a diario|de lunes a viernes|entre semana|dias laborales|dias de semana|'
                       r'los fines de semana|fines de semana|el fin de semana|fin de semana|(?:cada |los |el )?(?:lunes|martes|miercoles|jueves|viernes|sabados?|domingos?)(?: y| ,)?)\b', ' ', resto)
        resto = ' '.join(resto.replace(',', ' ').split())
        resto = re.sub(r'^(?:quiero que |programa(?:me)? (?:que )?|que )', '', resto)
        if not resto:
            return None
        sk = buscar(resto) or buscar(re.sub(r'^(?:haz|ejecuta|corre|usa|prepara|preparame|dame|da)(?: el| la| los| las)? ', '', resto))
        if sk:
            pasos, nombre = [{'tipo': 'skill', 'id': sk['id']}], sk['nombre']
        else:
            pasos, malas = pasos_desde_texto(resto)
            if malas or not pasos:
                return _resp('Para programarla necesito entender la tarea: «' + '», «'.join(malas or [resto]) +
                             '» no la reconozco. Usá una skill («qué skills tienes») o una orden como «pon lofi».')
            from .sky_aprendizaje import _recuperar
            nombre = _recuperar(texto, resto)[:60]
            nombre = nombre[:1].upper() + nombre[1:]
        try:
            item = sky_rutinas.guardar_rutina({'nombre': nombre, 'frases': [], 'hora': hora, 'dias': dias, 'pasos': pasos})
        except ValueError as exc:
            return _resp(str(exc))
        return _resp(f"Programado: «{item['nombre']}» a las {hora} {describir_dias(dias)}. "
                     'Las acciones que no autorizaste como automáticas quedarán esperando tu confirmación.', modulo='auto', programada=item)
    sk = buscar(t)
    if sk and (sk.get('integrada') is False or t in sk['frases']):
        res = ejecutar(sk)
        return _resp(f"{sk['nombre']}. " + (res['mensaje'] or 'Listo.'), acciones=res['acciones'], skill=sk['id'])
    m = re.fullmatch(r'(?:envia|manda|enviar) (?:el )?borrador (?:numero )?(\d{1,2})', t)
    if m:
        from . import sky_borradores
        lista = sky_borradores.listar()
        i = int(m.group(1)) - 1
        if not 0 <= i < len(lista):
            return _resp('No tengo ese borrador. ' + sky_borradores.describir())
        b = lista[i]
        return {'tipo': 'correo', 'borrador': {k: b[k] for k in ('para', 'asunto', 'cuerpo', 'en_respuesta_a')},
                'borrador_id': b['id'], 'requiere_confirmacion': True, 'mensaje': f"Enviar a {b['de'] or b['para']}: {b['asunto']}"}
    if re.fullmatch(r'(?:que|cuales) borradores tengo|(?:muestra(?:me)?|mostra(?:me)?|lee(?:me)?) (?:los |mis )?borradores', t):
        from . import sky_borradores
        return _resp(sky_borradores.describir(), modulo='auto')
    return None
