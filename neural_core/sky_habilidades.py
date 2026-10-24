"""SKY v12.4 — Catálogo de habilidades: una sola SKY con habilidades que se activan, desactivan y amplían.

    nativas      código de SKY revisado en el repositorio (sky-travel, sky-business-manager, …)
    builder      habilidades que diseñó el SKY Skill Builder y vos aprobaste (aisladas, con permisos)
    skills       procedimientos de pasos (v12.3, carpeta ~/.neuralt/skills)

«qué habilidades tienes», «desactiva la habilidad viajes», «activa la habilidad viajes», «haz una auditoría de seguridad»,
«recomiéndame mejoras». El estado (activa/inactiva) vive en ~/.neuralt/sky_habilidades.json.
"""
from __future__ import annotations

import json
import os
import re
import stat
import unicodedata
from pathlib import Path


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'^(?:oye |hey |ok )?sky[\s,]+', '', s.strip())
    return ' '.join(re.sub(r'[^\w\s]', ' ', s).split())


# ------------------------------------------------------------------ habilidades nativas

def _travel(texto):
    from . import hab_viajes
    return hab_viajes.interpretar(texto)


def _business(texto):
    from . import hab_proyectos
    return hab_proyectos.interpretar(texto)


def _smart_home(texto):
    t = _norm(texto)
    if re.fullmatch(r'(?:estado|como esta|resumen) de (?:la |mi )?casa|que hay encendido(?: en (?:la )?casa)?', t):
        from . import sky_home_assistant as casa
        if not casa.configurado():
            return {'tipo': 'respuesta', 'proveedor': 'sky-smart-home',
                    'mensaje': 'Tu casa no está conectada: configurá SKY_HA_URL y SKY_HA_TOKEN (Home Assistant).'}
        r = casa.resumen()
        if not r.get('ok'):
            return {'tipo': 'error', 'mensaje': 'No pude leer tu casa: ' + r.get('error', '')[:160]}
        encendidas = [e.get('name') or e['entity_id'] for e in r.get('entidades', [])
                      if str(e.get('state')) in ('on', 'open', 'unlocked', 'heat', 'cool', 'heat_cool')]
        return {'tipo': 'respuesta', 'proveedor': 'sky-smart-home',
                'mensaje': f"Tu casa tiene {len(r.get('entidades', []))} dispositivos. Encendidos o abiertos: " +
                           (', '.join(encendidas[:12]) or 'ninguno') + '.'}
    return None


def _self_monitor(texto):
    t = _norm(texto)
    if re.fullmatch(r'(?:recomiendame|recomienda|sugiere|sugiereme|propone|proponeme) mejoras|que (?:puedes|podes) mejorar|como (?:puedes|podes) mejorar', t):
        return {'tipo': 'respuesta', 'proveedor': 'sky-self-monitor', 'mensaje': recomendaciones(), 'modulo': 'kpi'}
    return None


def _security(texto):
    t = _norm(texto)
    if re.fullmatch(r'(?:haz|hace|corre) (?:una )?auditoria de seguridad|revisa (?:la |tu )?seguridad|auditoria de seguridad|que tan segura estas', t):
        a = auditoria()
        return {'tipo': 'respuesta', 'proveedor': 'sky-security', 'mensaje': a['texto'], 'auditoria': a}
    return None


def _music(texto):
    t = _norm(texto)
    m = re.fullmatch(r'(?:escribe|escribime|escribeme|compon|componeme|componme|crea|creame|hazme|haz) (?:una |la )?(?:cancion|letra(?: de cancion)?|tema musical) '
                     r'(?:sobre|de|para|acerca de) (.{3,300}?)(?: (?:en|estilo|al estilo|con estilo) ([\w ]{3,60}))?', t)
    if not m:
        return None
    from . import sky_creativo
    from .sky_aprendizaje import _recuperar
    try:
        c = sky_creativo.escribir_cancion(_recuperar(texto, m.group(1)), m.group(2) or '')
    except Exception as exc:
        return {'tipo': 'error', 'mensaje': 'No pude escribir la canción: ' + str(exc)[:160]}
    return {'tipo': 'respuesta', 'proveedor': 'sky-music', 'cancion': c,
            'mensaje': f"Te escribí «{c['titulo']}». Estilo: {c['estilo']}. La guardé en creaciones/musica/{c['archivo']}; "
                       'para escucharla, pegá letra y estilo en tu plataforma de música (Suno no tiene API pública).\n\n' + c['letra'][:1800]}


def _creative(texto):
    t = _norm(texto)
    from . import sky_creativo
    from .sky_aprendizaje import _recuperar
    m = re.fullmatch(r'(?:genera|generame|crea|creame|dibuja|dibujame|haz|hazme) (?:una |la )?(?:imagen|ilustracion|foto|dibujo) (?:de |con |sobre )?(.{3,600}?)'
                     r'(?: con (openai|firefly|adobe))?', t)
    if m:
        proveedor = {'adobe': 'firefly'}.get(m.group(2) or '', m.group(2) or '')
        try:
            r = sky_creativo.generar_imagen(_recuperar(texto, m.group(1)), proveedor)
        except (RuntimeError, ValueError) as exc:
            return {'tipo': 'error', 'mensaje': str(exc)[:300]}
        return {'tipo': 'respuesta', 'proveedor': 'sky-creative', 'imagen': r['archivo'],
                'mensaje': f"Listo, generé la imagen con {'OpenAI' if r['proveedor'] == 'openai' else 'Adobe Firefly'}. Está en creaciones/imagenes/{r['archivo']}."}
    m = re.fullmatch(r'(?:crea|creame|haz|hazme|prepara|preparame|genera) (?:una )?presentacion (?:en|con) gamma (?:sobre|de|acerca de) (.{3,400})|'
                     r'(?:crea|creame|haz|hazme|prepara|preparame|genera) (?:una )?presentacion (?:sobre|de|acerca de) (.{3,400}?) (?:en|con) gamma', t)
    if m:
        tema = _recuperar(texto, m.group(1) or m.group(2))
        try:
            r = sky_creativo.crear_presentacion_gamma(tema, al_terminar=sky_creativo.avisar_presentacion)
        except (RuntimeError, ValueError) as exc:
            return {'tipo': 'error', 'mensaje': str(exc)[:300]}
        return {'tipo': 'respuesta', 'proveedor': 'sky-creative',
                'mensaje': f'Gamma está armando la presentación sobre {tema}. Te aviso con el enlace cuando esté lista.'}
    return None


NATIVAS = [
    {'id': 'sky-travel', 'nombre': 'Viajes', 'descripcion': 'Presupuesto por rubro y día, clima previsto (Open-Meteo), cambio de moneda e itinerario.',
     'ejemplos': ['planifica un viaje a Granada de 3 días con 200 dólares'], 'requiere': [], 'interpretar': _travel},
    {'id': 'sky-business-manager', 'nombre': 'Proyectos y negocio', 'descripcion': 'Proyectos con tareas, fechas, avance y atrasos.',
     'ejemplos': ['crea el proyecto Tienda online', 'cómo va el proyecto tienda online', 'qué tareas están atrasadas'],
     'requiere': [], 'interpretar': _business},
    {'id': 'sky-smart-home', 'nombre': 'Casa inteligente', 'descripcion': 'Luces, escenas, clima y cerraduras con Home Assistant.',
     'ejemplos': ['estado de la casa', 'enciende la luz de la sala'], 'requiere': ['home_assistant'], 'interpretar': _smart_home},
    {'id': 'sky-self-monitor', 'nombre': 'Automonitoreo', 'descripcion': 'KPIs reales, problemas detectados y mejoras recomendadas.',
     'ejemplos': ['qué está fallando', 'recomiéndame mejoras'], 'requiere': [], 'interpretar': _self_monitor},
    {'id': 'sky-security', 'nombre': 'Seguridad', 'descripcion': 'Auditoría de permisos, accesos, habilidades instaladas y datos.',
     'ejemplos': ['haz una auditoría de seguridad'], 'requiere': [], 'interpretar': _security},
    {'id': 'sky-music', 'nombre': 'Música', 'descripcion': 'Letras originales, estructura, acordes y estilo listos para tu plataforma de música.',
     'ejemplos': ['escribe una canción sobre Managua de noche estilo bachata'], 'requiere': [], 'interpretar': _music},
    {'id': 'sky-creative', 'nombre': 'Creación multimedia', 'descripcion': 'Imágenes (OpenAI o Adobe Firefly) y presentaciones (Gamma).',
     'ejemplos': ['genera una imagen de un colibrí futurista', 'crea una presentación en Gamma sobre energía solar'],
     'requiere': ['openai_imagenes|firefly|gamma'], 'interpretar': _creative},
]
# Siempre activas: no se pueden apagar por voz (son las que vigilan y protegen a SKY).
PROTEGIDAS = {'sky-security', 'sky-self-monitor'}


def _ruta() -> Path:
    return Path.home() / '.neuralt' / 'sky_habilidades.json'


def _estado() -> dict:
    try:
        d = json.loads(_ruta().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def activa(hid: str) -> bool:
    return hid in PROTEGIDAS or hid not in set(_estado().get('desactivadas', []))


def cambiar(hid: str, activar: bool) -> bool:
    if hid not in {h['id'] for h in NATIVAS} or (hid in PROTEGIDAS and not activar):
        return False
    d = _estado()
    desact = set(d.get('desactivadas', []))
    (desact.discard if activar else desact.add)(hid)
    d['desactivadas'] = sorted(desact)
    _ruta().parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _ruta().write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    return True


def catalogo() -> dict:
    from . import sky_integraciones, sky_skill_builder, sky_skills
    integ = {i['id']: i['lista'] for i in sky_integraciones.listar()}
    nativas = []
    for h in NATIVAS:
        lista = all(any(integ.get(x) for x in req.split('|')) for req in h['requiere'])
        nativas.append({k: v for k, v in h.items() if k != 'interpretar'} | {'activa': activa(h['id']), 'protegida': h['id'] in PROTEGIDAS,
                                                                              'integraciones_listas': lista})
    return {'nativas': nativas,
            'builder': [{k: v for k, v in b.items() if k != 'codigo'} for b in sky_skill_builder.listar()],
            'skills': [{'id': s['id'], 'nombre': s['nombre'], 'integrada': s.get('integrada')} for s in sky_skills.listar()],
            'integraciones': sky_integraciones.listar(),
            'necesidades': sky_skill_builder.necesidades(10)}


def describir() -> str:
    c = catalogo()
    nat = '; '.join(f"{h['nombre']}{'' if h['activa'] else ' (desactivada)'}" for h in c['nativas'])
    inst = [b['nombre'] for b in c['builder'] if b['estado'] == 'instalada']
    prop = [b['nombre'] for b in c['builder'] if b['estado'] != 'instalada']
    return (f"Habilidades de SKY: {nat}. Creadas con el Skill Builder: {', '.join(inst) or 'ninguna instalada'}"
            + (f"; esperando tu aprobación: {', '.join(prop)}" if prop else '') +
            f". Además tengo {len(c['skills'])} skills de pasos. Decí «diseña una habilidad para …» para crear una nueva.")


# ------------------------------------------------------------------ sky-security: auditoría

def auditoria() -> dict:
    from . import sky_capacidades as caps, sky_metricas, sky_skill_builder, sky_whatsapp
    hallazgos = []

    def h(nivel, texto, accion=''):
        hallazgos.append({'nivel': nivel, 'texto': texto, 'accion': accion})

    politica = caps.cargar_politica()
    h('info', f"Perfil de permisos «{politica.get('perfil', '?')}»: {len(politica.get('enabled', []))} capacidades activas, "
              f"{len(politica.get('auto_confirm', []))} sin pedir confirmación; el nivel 3 siempre se confirma.")
    altas = [c for c in politica.get('enabled', []) if caps.CAPACIDADES.get(c) and caps.CAPACIDADES[c].riesgo == 'alto']
    if altas:
        h('media', 'Capacidades de alto riesgo activas: ' + ', '.join(altas) + ' (siempre piden confirmación).',
          'Desactivalas si no las usás: python agente_dispositivo.py --desactivar <capacidad>')
    auto_altas = [c for c in politica.get('auto_confirm', []) if caps.CAPACIDADES.get(c) and caps.CAPACIDADES[c].riesgo != 'bajo']
    if auto_altas:
        h('alta', 'Hay capacidades que no son de bajo riesgo marcadas como automáticas: ' + ', '.join(auto_altas) + '.',
          'Quitales la ejecución automática en tu política del agente.')
    if caps.parada_activa():
        h('info', 'La parada de emergencia está activa.', 'Levantala desde el HUD cuando quieras.')
    if os.getenv('SKY_DEPLOYMENT_MODE', 'local') != 'local':
        h('media', f"SKY corre en modo {os.getenv('SKY_DEPLOYMENT_MODE')}: revisá HTTPS, 2FA y hosts de confianza.")
    env = Path(__file__).resolve().parents[1] / '.env'
    if env.exists() and os.name != 'nt' and env.stat().st_mode & (stat.S_IRGRP | stat.S_IROTH):
        h('alta', 'El archivo .env (con tus claves) es legible por otros usuarios del equipo.', 'chmod 600 .env')
    r = sky_metricas.resumen('semana')
    s = r['seguridad']
    if s['accesos_fallidos']:
        h('media' if s['accesos_fallidos'] < 20 else 'alta', f"{s['accesos_fallidos']} intentos de acceso sin llave a la API esta semana.",
          'Si no fuiste vos, rotá la llave del dueño (local_data/sky_api_token.txt) y revisá quién llega a tu red.')
    if r['servicio'].get('whatsapp_rechazados'):
        h('info', f"{r['servicio']['whatsapp_rechazados']} mensajes de WhatsApp rechazados (otro número o firma inválida).")
    wa = sky_whatsapp.estado()
    if wa['configurado'] and not os.getenv('SKY_WA_TOKEN_FILE'):
        h('baja', 'El token de WhatsApp está escrito en .env.', 'Guardalo en un archivo aparte y usá SKY_WA_TOKEN_FILE.')
    for b in sky_skill_builder.listar():
        if b['estado'] == 'instalada':
            h('info', f"Habilidad instalada «{b['nombre']}» v{b['version_instalada']} con permisos: {', '.join(b['permisos_aprobados']) or 'ninguno'}.")
    if os.getenv('SKY_LOCAL_ONLY', '0') != '1' and os.getenv('SKY_CEREBRO', 'auto') not in ('auto', 'reglas', 'ollama'):
        h('info', f"El cerebro con herramientas usa la nube ({os.getenv('SKY_CEREBRO')}): tus pedidos, tu perfil y tus datos recordados viajan a ese proveedor.")
    orden = {'alta': 0, 'media': 1, 'baja': 2, 'info': 3}
    hallazgos.sort(key=lambda x: orden[x['nivel']])
    graves = [x for x in hallazgos if x['nivel'] in ('alta', 'media')]
    texto = ('Auditoría de seguridad: ' + ('sin hallazgos importantes. ' if not graves else f'{len(graves)} puntos a revisar. ') +
             ' '.join(f"[{x['nivel']}] {x['texto']}" + (f" → {x['accion']}" if x['accion'] else '') for x in hallazgos[:8]))
    try:
        sky_metricas.registrar('servicio', 'auditoria', not graves, detalle=f'{len(graves)} hallazgos')
    except Exception:
        pass
    return {'hallazgos': hallazgos, 'texto': texto}


# ------------------------------------------------------------------ sky-self-monitor: recomendaciones

def recomendaciones() -> str:
    from . import sky_metricas, sky_skill_builder, sky_integraciones
    r = sky_metricas.resumen('semana')
    ideas = []
    for p in r['problemas'][:3]:
        ideas.append(f"{p['titulo']}: {p['sugerencia']}")
    incumplidos = [o for o in r.get('slo', []) if o['cumple'] is False]
    for o in incumplidos[:2]:
        ideas.append(f"Objetivo «{o['nombre']}» sin cumplir ({o['actual']:g} {o['unidad']} vs {o['objetivo']:g}).")
    cer = r['asistente']['por_origen'].get('cerebro', {})
    apr = r['asistente']['por_origen'].get('aprendido', {})
    if cer.get('n', 0) >= 5 and not apr.get('n'):
        ideas.append('Muchas órdenes pasan por el cerebro y ninguna por atajos: confirmá las acciones para que las aprenda.')
    nec = sky_skill_builder.necesidades(3)
    if nec:
        ideas.append('Me pediste cosas que no sé hacer: ' + ', '.join(f"«{n['frase']}»" for n in nec) +
                     '. Puedo diseñar una habilidad para cada una (decí «diseña una habilidad para …»).')
    if not any(i['lista'] for i in sky_integraciones.listar() if i['id'] in ('ollama', 'openai', 'anthropic', 'gemini')):
        ideas.append('No tengo ningún cerebro de IA disponible: iniciá Ollama o configurá una clave.')
    if not ideas:
        return 'Revisé mis KPIs de la semana y no veo mejoras urgentes. Seguí usándome: aprendo de cada orden que confirmás.'
    return 'Mejoras que te recomiendo, según mis mediciones: ' + ' '.join(f'{i + 1}) {x}' for i, x in enumerate(ideas))


# ------------------------------------------------------------------ entrada única

def interpretar(texto: str) -> dict | None:
    t = _norm(texto)
    if re.fullmatch(r'(?:que|cuales) habilidades (?:tienes|tenes|hay|sabes)|(?:muestra(?:me)?|mostra(?:me)?|abre|ver) (?:tus |las |mis )?habilidades', t):
        return {'tipo': 'respuesta', 'proveedor': 'sky-habilidades', 'mensaje': describir(), 'modulo': 'habilidades'}
    m = re.fullmatch(r'(activa|desactiva|deshabilita|apaga|enciende) (?:la )?habilidad (?:de )?(.{2,40})', t)
    if m:
        q = m.group(2)
        h = next((x for x in NATIVAS if q in (x['id'], x['id'].replace('sky-', ''), _norm(x['nombre']))
                  or q in _norm(x['nombre']) or q in x['id']), None)
        if h:
            activar = m.group(1) in ('activa', 'enciende')
            if not cambiar(h['id'], activar):
                return {'tipo': 'respuesta', 'proveedor': 'sky-habilidades',
                        'mensaje': f"«{h['nombre']}» protege a SKY y no se puede desactivar."}
            return {'tipo': 'respuesta', 'proveedor': 'sky-habilidades', 'modulo': 'habilidades',
                    'mensaje': f"{'Activé' if activar else 'Desactivé'} la habilidad «{h['nombre']}»."}
    from . import sky_integraciones, sky_skill_builder
    r = sky_integraciones.interpretar(t) or sky_skill_builder.interpretar(texto)
    if r:
        return r
    for h in NATIVAS:
        if activa(h['id']):
            r = h['interpretar'](texto)
            if r:
                r.setdefault('habilidad', h['id'])
                return r
    return sky_skill_builder.ejecutar_si_coincide(texto)
