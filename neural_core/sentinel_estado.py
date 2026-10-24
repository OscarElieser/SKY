"""SKY SENTINEL — Security Center: estado de seguridad con datos reales y órdenes por voz.

    "mostrame tu estado de seguridad"         "qué dispositivos están conectados"
    "revisá tus accesos recientes"            "desactivá las automatizaciones"
    "bloqueá el acceso desde otros dispositivos"   "permití el acceso desde otros dispositivos" (pide PIN en el HUD)
    "bloquea SKY" / "bloquéate"  (la interfaz vuelve a pedir el PIN)
Ninguna de estas órdenes concede permisos: sólo consultan o restringen. Lo que afloja la seguridad se hace en el
Security Center con el PIN.
"""
from __future__ import annotations

import os
import re
import time
import unicodedata
from datetime import datetime


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'^(?:oye |hey |ok )?sky[\s,]+', '', s.strip())
    return ' '.join(re.sub(r'[^\w\s]', ' ', s).split())


def accesos_recientes(limite: int = 15) -> list[dict]:
    from .sky_metricas import _filas
    ahora = time.time()
    filas = _filas(ahora - 7 * 86400, ahora + 1)
    eventos = [f for f in filas if (f['tipo'] == 'api' and (f['codigo'] or 0) in (401, 403, 429)) or
               (f['tipo'] == 'servicio' and (f['nombre'].startswith('sentinel_') or f['nombre'] in
                                              ('whatsapp_rechazado', 'whatsapp_firma', 'parada', 'reanudar', 'habilidad_instalada')))]
    return [{'hora': datetime.fromtimestamp(f['ts']).strftime('%Y-%m-%d %H:%M'), 'que': f['nombre'],
             'codigo': f['codigo'], 'detalle': f['detalle'] or ''} for f in reversed(eventos[-limite:])]


def dispositivos() -> list[dict]:
    from . import dispositivos as disp
    salida = [{'nombre': 'local', 'url': '127.0.0.1', 'tipo': 'este equipo'}]
    try:
        salida += [{'nombre': d['name'], 'url': d['url'], 'tipo': 'remoto (Tailscale)'} for d in disp.paired_devices()]
    except Exception:
        pass
    return salida


def estado() -> dict:
    from . import sentinel_identidad as ident, sky_capacidades as caps, sky_metricas, sky_skill_builder, sky_skills
    from .sky_habilidades import auditoria
    try:
        from metaverse import owner_mfa
        mfa = owner_mfa.required()
    except Exception:
        mfa = False
    r = sky_metricas.resumen('semana')
    a = auditoria()
    tareas = [t for t in sky_skills.programadas() if t.get('activa', True)]
    datos = {
        'pin': ident.pin_configurado(), 'pin_bloqueado_s': ident.bloqueado_por(), 'mfa': mfa,
        'solo_local': ident.solo_local(), 'parada': caps.parada_activa(),
        'modo': os.getenv('SKY_DEPLOYMENT_MODE', 'local'), 'local_only_ia': os.getenv('SKY_LOCAL_ONLY', '0') == '1',
        'comunidad_publica': os.getenv('SKY_COMUNIDAD_PUBLICA', '0') == '1',
        'dispositivos': dispositivos(), 'automatizaciones_activas': len(tareas),
        'habilidades_instaladas': [{'nombre': b['nombre'], 'permisos': b['permisos_aprobados']}
                                   for b in sky_skill_builder.listar() if b['estado'] == 'instalada'],
        'kpis': {'accesos_fallidos_7d': r['seguridad']['accesos_fallidos'], 'prohibidos_7d': r['seguridad']['prohibidos'],
                 'acciones_rechazadas_7d': r['seguridad']['rechazadas'], 'whatsapp_rechazados_7d': r['servicio'].get('whatsapp_rechazados', 0),
                 'pin_fallidos_7d': sum(1 for e in accesos_recientes(500) if e['que'] == 'sentinel_pin_fallido')},
        'accesos_recientes': accesos_recientes(),
        'hallazgos': a['hallazgos'],
    }
    recomendaciones = []
    if not datos['pin']:
        recomendaciones.append('Configurá un PIN: hoy cualquiera frente a tu PC desbloqueada puede usar SKY.')
    if not datos['mfa'] and datos['modo'] != 'local':
        recomendaciones.append('Activá el segundo factor (2FA) del creador para el acceso remoto.')
    if datos['comunidad_publica']:
        recomendaciones.append('La comunidad está abierta a otras personas (SKY_COMUNIDAD_PUBLICA=1).')
    datos['recomendaciones'] = recomendaciones
    datos['texto'] = describir(datos)
    return datos


def describir(d: dict) -> str:
    partes = [f"PIN {'configurado' if d['pin'] else 'NO configurado'}",
              f"2FA {'activo' if d['mfa'] else 'inactivo'}",
              'sólo este equipo' if d['solo_local'] else 'acepta otros equipos con la llave',
              'parada de emergencia ACTIVA' if d['parada'] else 'sin parada']
    k = d['kpis']
    txt = ('Estado de seguridad: ' + ', '.join(partes) + '. ' +
           f"En 7 días: {k['accesos_fallidos_7d']} accesos sin llave, {k['pin_fallidos_7d']} PIN incorrectos, "
           f"{k['acciones_rechazadas_7d']} acciones rechazadas por permisos. "
           f"{len(d['dispositivos'])} dispositivo(s), {d['automatizaciones_activas']} automatizaciones activas, "
           f"{len(d['habilidades_instaladas'])} habilidades del Builder instaladas.")
    if d['recomendaciones']:
        txt += ' Te recomiendo: ' + ' '.join(d['recomendaciones'])
    return txt


def _resp(msg: str, **extra) -> dict:
    return {'tipo': 'respuesta', 'mensaje': msg, 'proveedor': 'sky-sentinel', **extra}


def interpretar(texto: str) -> dict | None:
    t = _norm(texto)
    if re.fullmatch(r'(?:muestra(?:me)?|mostra(?:me)?|dame|cual es|como esta) (?:tu |el |mi )?estado de seguridad|'
                    r'(?:abre|abri|muestra(?:me)?|mostra(?:me)?) (?:el )?(?:centro de seguridad|security center|sentinel)', t):
        d = estado()
        return _resp(d['texto'], modulo='sentinel')
    if re.fullmatch(r'(?:que|cuales) dispositivos (?:estan )?(?:conectados|vinculados|autorizados)(?: hay)?', t):
        ds = dispositivos()
        return _resp('Dispositivos autorizados: ' + '; '.join(f"{x['nombre']} ({x['tipo']})" for x in ds) + '.', modulo='sentinel')
    if re.fullmatch(r'(?:revisa|revisar|muestra(?:me)?|mostra(?:me)?) (?:tus |los |mis )?accesos(?: recientes)?', t):
        acc = accesos_recientes(8)
        if not acc:
            return _resp('No hubo accesos rechazados ni eventos de seguridad en los últimos 7 días.', modulo='sentinel')
        return _resp('Eventos de seguridad recientes: ' + '; '.join(f"{a['hora']} {a['que']}" + (f" ({a['codigo']})" if a['codigo'] else '')
                                                                     for a in acc) + '.', modulo='sentinel')
    if re.fullmatch(r'(?:desactiva|pausa|deten|apaga) (?:todas )?(?:las )?(?:automatizaciones|tareas programadas)', t):
        from .sentinel_identidad import pausar_automatizaciones
        return _resp(f'Pausé {pausar_automatizaciones()} tareas programadas. Reactivalas en Automatización cuando quieras.')
    if re.fullmatch(r'bloquea (?:el )?acceso (?:desde|de) (?:otros|los demas) (?:dispositivos|equipos)|solo (?:este equipo|acceso local)', t):
        from .sentinel_identidad import cambiar_solo_local
        cambiar_solo_local(True)
        return _resp('Listo: SKY sólo acepta conexiones de este equipo. Para volver a permitir otros equipos usá el Security Center con tu PIN.')
    if re.fullmatch(r'(?:permite|permiti|permitir|habilita|habilitar|desbloquea) (?:el )?acceso (?:desde|de) (?:otros|los demas) (?:dispositivos|equipos)', t):
        return _resp('Por seguridad, eso se hace en el Security Center con tu PIN.', modulo='sentinel')
    if re.fullmatch(r'bloqueate|bloquea (?:a )?sky|bloquea la interfaz(?: de sky)?|bloquear sky', t):
        from .sentinel_identidad import pin_configurado
        if not pin_configurado():
            return _resp('Para bloquear SKY primero configurá un PIN en el Security Center.', modulo='sentinel')
        return _resp('SKY bloqueada. Ingresá tu PIN para volver.', bloquear_hud=True)
    return None
