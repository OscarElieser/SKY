"""SKY v12.2 — KPIs reales: mediciones de la API, del asistente y de cada acción, con detección de problemas.

Qué se registra (base local ~/.neuralt/sky_metricas.sqlite3, o SKY_METRICAS_DB):
  api     cada petición /api/*: ruta (plantilla, sin IDs), código HTTP y milisegundos
  turno   cada mensaje al asistente: cómo se resolvió (reglas, atajo aprendido, cerebro, IA) y cuánto tardó
  accion  cada acción en un equipo (vía dispositivos.call_device): completada o fallida, con el motivo
  casa    cada orden a Home Assistant
  agente  disponibilidad del agente del equipo (consultas de estado)
  voz     lo que mide el HUD: tiempo hasta la primera palabra hablada, interrupciones, errores de micrófono
  tarea   propuestas que esperan confirmación y las que el dueño canceló
  servicio arranques de la API (reinicios)
  modelo  llamadas al cerebro local: milisegundos y tokens (Ollama informa eval_count)

No guarda textos de mensajes, parámetros, tokens, IPs ni contenido de archivos: sólo nombres de rutas
y acciones, resultados, tiempos y el motivo corto de los fallos.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

_LOCK = threading.Lock()
RETENCION_DIAS = 30
TIPOS = ('api', 'turno', 'accion', 'casa', 'agente', 'interfaz', 'voz', 'tarea', 'servicio', 'modelo')
_insertados = 0

NOMBRES_ACCION = {
    'launch_app': 'abrir app', 'open_url': 'abrir web', 'media_control': 'control multimedia', 'media_key': 'tecla multimedia',
    'volume': 'volumen', 'play_media': 'reproducir', 'notify': 'aviso', 'task_action': 'tarea', 'open_file': 'abrir archivo',
    'open_path': 'abrir carpeta', 'list_path': 'listar carpeta', 'window_action': 'ventanas', 'organize_windows': 'organizar ventanas',
    'note_create': 'crear nota', 'note_append': 'agregar a nota', 'note_trash': 'borrar nota', 'type_text': 'escribir texto',
    'screenshot': 'captura', 'clipboard_get': 'leer portapapeles', 'clipboard_set': 'copiar al portapapeles', 'lock_screen': 'bloquear',
}


def _ruta_db() -> Path:
    return Path(os.getenv('SKY_METRICAS_DB') or Path.home() / '.neuralt' / 'sky_metricas.sqlite3')


def _conn() -> sqlite3.Connection:
    p = _ruta_db()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p, timeout=10)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('''CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY, ts REAL NOT NULL, tipo TEXT NOT NULL, nombre TEXT NOT NULL,
        ok INTEGER NOT NULL, ms INTEGER, codigo INTEGER, origen TEXT, detalle TEXT, tokens INTEGER)''')
    try:
        c.execute('ALTER TABLE eventos ADD COLUMN tokens INTEGER')
    except sqlite3.OperationalError:
        pass
    c.execute('CREATE INDEX IF NOT EXISTS eventos_ts ON eventos(ts, tipo)')
    return c


def activo() -> bool:
    return os.getenv('SKY_METRICAS', '1').strip() != '0'


def registrar(tipo: str, nombre: str, ok: bool, ms: float | None = None, codigo: int | None = None,
              origen: str = '', detalle: str = '', ts: float | None = None, tokens: int | None = None) -> None:
    """Registra un evento. Nunca lanza: medir no puede romper a SKY."""
    global _insertados
    if not activo() or tipo not in TIPOS:
        return
    try:
        with _LOCK, _conn() as c:
            c.execute('INSERT INTO eventos(ts,tipo,nombre,ok,ms,codigo,origen,detalle,tokens) VALUES(?,?,?,?,?,?,?,?,?)',
                      (ts or time.time(), tipo, str(nombre)[:80], 1 if ok else 0,
                       None if ms is None else max(0, min(3_600_000, int(ms))), codigo, str(origen or '')[:20],
                       ' '.join(str(detalle or '').split())[:200], None if tokens is None else max(0, int(tokens))))
            _insertados += 1
            if _insertados % 500 == 1:
                c.execute('DELETE FROM eventos WHERE ts < ?', (time.time() - RETENCION_DIAS * 86400,))
    except (OSError, sqlite3.Error):
        pass


_MUESTRAS: dict[str, float] = {}


def toca_muestra(clave: str, cada_segundos: float) -> bool:
    ahora = time.monotonic()
    if ahora - _MUESTRAS.get(clave, -1e9) >= cada_segundos:
        _MUESTRAS[clave] = ahora
        return True
    return False


_SEGMENTO_ID = re.compile(r'/(?:[0-9a-f]{8,}|\d+|[0-9a-f-]{32,36})(?=/|$)', re.I)


def ruta_plantilla(path: str) -> str:
    return _SEGMENTO_ID.sub('/{id}', path)[:80]


def resultado_ok(res) -> tuple[bool, str]:
    """Interpreta la respuesta del agente: ok=False o estados FAILED/ERROR cuentan como fallo."""
    if not isinstance(res, dict):
        return True, ''
    estado = str(res.get('status', '')).upper()
    if res.get('ok') is False or estado in ('FAILED', 'ERROR', 'DENIED'):
        return False, str(res.get('error') or res.get('message') or estado or 'falló')
    if estado in ('SENT', 'RUNNING', 'PENDING', 'DISPATCHED', 'UI'):
        # The action may have been issued, but is NOT yet verified. It must
        # not become an automatically learned success or a success KPI.
        return False, 'Acción enviada o iniciada, aún no verificada.'
    return True, ''


# ------------------------------------------------------------------ consultas

def _desde(periodo: str, ahora: datetime) -> float:
    if periodo == 'semana':
        return (ahora - timedelta(days=7)).timestamp()
    return ahora.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def _filas(desde: float, hasta: float, tipo: str | None = None) -> list[sqlite3.Row]:
    try:
        with _conn() as c:
            c.row_factory = sqlite3.Row
            if tipo:
                return c.execute('SELECT * FROM eventos WHERE ts>=? AND ts<? AND tipo=? ORDER BY ts', (desde, hasta, tipo)).fetchall()
            return c.execute('SELECT * FROM eventos WHERE ts>=? AND ts<? ORDER BY ts', (desde, hasta)).fetchall()
    except (OSError, sqlite3.Error):
        return []


def percentil(valores: list[int], p: float) -> int | None:
    v = sorted(x for x in valores if x is not None)
    if not v:
        return None
    k = max(0, min(len(v) - 1, int(round(p / 100 * (len(v) - 1)))))
    return int(v[k])


def _estad(ms: list[int]) -> dict:
    ms = [m for m in ms if m is not None]
    return {'n': len(ms), 'p50_ms': percentil(ms, 50), 'p95_ms': percentil(ms, 95), 'p99_ms': percentil(ms, 99),
            'promedio_ms': int(sum(ms) / len(ms)) if ms else None}


# Objetivos de servicio (SLO) configurables en .env
def objetivos() -> dict:
    def num(nombre, defecto):
        try:
            return float(os.getenv(nombre, defecto))
        except ValueError:
            return float(defecto)
    return {'api_p95_ms': num('SKY_SLO_API_P95_MS', 800), 'exito_tareas_pct': num('SKY_SLO_EXITO_TAREAS', 95),
            'disponibilidad_api_pct': num('SKY_SLO_DISPONIBILIDAD', 99.5), 'cerebro_p50_ms': num('SKY_SLO_CEREBRO_P50_MS', 4000),
            'primera_voz_p50_ms': num('SKY_SLO_PRIMERA_VOZ_MS', 1500)}


def evaluar_slo(r: dict) -> list[dict]:
    o, salida = objetivos(), []
    def agregar(nombre, objetivo, actual, cumple, unidad):
        salida.append({'nombre': nombre, 'objetivo': objetivo, 'actual': actual, 'unidad': unidad,
                       'cumple': None if actual is None else bool(cumple)})
    p95 = r['api']['p95_ms']
    agregar('Latencia p95 de la API', o['api_p95_ms'], p95, p95 is not None and p95 <= o['api_p95_ms'], 'ms')
    disp = r['api']['disponibilidad']
    agregar('Disponibilidad de la API', o['disponibilidad_api_pct'], disp, disp is not None and disp >= o['disponibilidad_api_pct'], '%')
    ex = r['acciones']['tasa_exito']
    agregar('Éxito de tareas', o['exito_tareas_pct'], ex, ex is not None and ex >= o['exito_tareas_pct'], '%')
    cer = (r['asistente']['por_origen'].get('cerebro') or {}).get('p50_ms')
    agregar('Cerebro local (mediana)', o['cerebro_p50_ms'], cer, cer is not None and cer <= o['cerebro_p50_ms'], 'ms')
    pv = r['voz']['primera_voz']['p50_ms']
    agregar('Primera palabra hablada (mediana)', o['primera_voz_p50_ms'], pv, pv is not None and pv <= o['primera_voz_p50_ms'], 'ms')
    return salida


def detectar(ahora: datetime | None = None, filas: list | None = None, base: list | None = None) -> list[dict]:
    """Problemas de rendimiento de HOY comparados con los 7 días anteriores."""
    ahora = ahora or datetime.now()
    inicio = _desde('hoy', ahora)
    hoy = filas if filas is not None else _filas(inicio, ahora.timestamp() + 1)
    previo = base if base is not None else _filas(inicio - 7 * 86400, inicio)
    problemas = []

    def agregar(pid, severidad, titulo, detalle, sugerencia):
        problemas.append({'id': pid, 'severidad': severidad, 'titulo': titulo, 'detalle': detalle, 'sugerencia': sugerencia})

    # 1) Rutas de la API lentas o más lentas que lo normal
    por_ruta, base_ruta = {}, {}
    for f in hoy:
        if f['tipo'] == 'api' and f['ms'] is not None:
            por_ruta.setdefault(f['nombre'], []).append(f['ms'])
    for f in previo:
        if f['tipo'] == 'api' and f['ms'] is not None:
            base_ruta.setdefault(f['nombre'], []).append(f['ms'])
    for ruta, ms in por_ruta.items():
        if len(ms) < 5 or '/stream' in ruta or '/stt/' in ruta or '/tts' in ruta:
            continue   # streaming/voz duran lo que dura la respuesta: no son lentitud
        p95 = percentil(ms, 95)
        b = base_ruta.get(ruta, [])
        bp95 = percentil(b, 95) if len(b) >= 10 else None
        if bp95 and p95 > max(300, 2 * bp95):
            agregar('lenta:' + ruta, 'media', f'{ruta} está más lenta que lo normal',
                    f'p95 de hoy {p95} ms frente a {bp95} ms de los últimos 7 días ({len(ms)} peticiones).',
                    'Revisá si hay otra app consumiendo CPU o disco; reiniciá SKY si persiste.')
        elif p95 > 3000:
            agregar('lenta:' + ruta, 'media', f'{ruta} responde lento',
                    f'p95 de {p95} ms en {len(ms)} peticiones.', 'Revisá el diagnóstico (DIAG) y el uso de CPU del equipo.')

    # 2) Errores del servidor
    api = [f for f in hoy if f['tipo'] == 'api']
    errores = [f for f in api if (f['codigo'] or 0) >= 500]
    if len(api) >= 10 and len(errores) / len(api) >= 0.10:
        rutas = sorted({f['nombre'] for f in errores})[:3]
        agregar('errores_api', 'alta', 'Muchos errores internos en la API',
                f'{len(errores)} de {len(api)} peticiones fallaron con 5xx ({", ".join(rutas)}).',
                'Mirá la consola de SKY; ejecutá python sky_diagnostico.py.')

    # 3) Acciones fallidas
    acciones = [f for f in hoy if f['tipo'] in ('accion', 'casa')]
    fallidas = [f for f in acciones if not f['ok']]
    if len(acciones) >= 4 and len(fallidas) / len(acciones) >= 0.25:
        agregar('acciones_fallidas', 'alta', 'Están fallando muchas acciones',
                f'{len(fallidas)} de {len(acciones)} acciones fallaron hoy. Último motivo: {fallidas[-1]["detalle"] or "sin detalle"}.',
                'Revisá que el agente del equipo esté activo y los permisos en el panel Permisos.')
    racha = {}
    for f in acciones:
        racha[f['nombre']] = 0 if f['ok'] else racha.get(f['nombre'], 0) + 1
    for nombre, n in racha.items():
        if n >= 3:
            agregar('repite:' + nombre, 'media', f'«{NOMBRES_ACCION.get(nombre, nombre)}» falló {n} veces seguidas',
                    'Último motivo: ' + (next((f['detalle'] for f in reversed(acciones) if f['nombre'] == nombre), '') or 'sin detalle'),
                    'Probala desde el panel; si dice "desactivada", activá la capacidad.')

    # 4) Agente del equipo sin respuesta
    agente = [f for f in hoy if f['tipo'] == 'agente']
    if agente and agente[-1]['ok'] == 0 and sum(1 for f in agente[-3:] if not f['ok']) >= 2:
        agregar('agente_caido', 'alta', 'El agente del equipo no responde',
                agente[-1]['detalle'] or 'Sin conexión con el agente.', 'Inicialo: python agente_dispositivo.py (opción 0 del menú).')

    # 4b) Servicios que se reinician solos
    reinicios = [f for f in hoy if f['tipo'] == 'servicio' and f['nombre'] == 'reinicio']
    if len(reinicios) >= 3:
        agregar('reinicios', 'alta', 'Un servicio de SKY se está reiniciando seguido',
                f'{len(reinicios)} reinicios hoy. Último: {reinicios[-1]["detalle"]}.',
                'Ejecutá python sky_diagnostico.py y mirá la consola del servicio.')

    # 4c) WhatsApp cerca del límite gratis del mes
    if any(f['tipo'] == 'servicio' and f['nombre'] == 'whatsapp_enviado' for f in hoy):
        mes = whatsapp_del_mes(ahora)
        if mes >= LIMITE_GRATIS_WHATSAPP * 0.9:
            agregar('whatsapp_cupo', 'media', 'Cerca del límite de mensajes gratis de WhatsApp',
                    f'{mes} respuestas enviadas este mes; Meta cobra desde la número {LIMITE_GRATIS_WHATSAPP + 1}.',
                    'Usá el HUD para consultas largas o configurá un presupuesto en Meta.')

    # 4d) Presupuesto de IA en la nube (si definiste precio y presupuesto)
    presupuesto = os.getenv('SKY_PRESUPUESTO_USD_MES', '').strip()
    if re.fullmatch(r'\d+(?:\.\d+)?', presupuesto) and float(presupuesto) > 0 and any(f['tipo'] == 'modelo' for f in hoy):
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
        costo = resumen_modelo(_filas(inicio_mes, ahora.timestamp() + 1, 'modelo'))['costo_estimado_usd']
        if costo is not None and costo >= 0.8 * float(presupuesto):
            agregar('presupuesto_ia', 'alta' if costo >= float(presupuesto) else 'media', 'Consumo de IA cerca del presupuesto',
                    f'Llevás USD {costo:.2f} este mes de un presupuesto de USD {float(presupuesto):.2f}.',
                    'Usá Ollama local (SKY_CEREBRO=auto) o subí el presupuesto en .env.')

    # 5) Cerebro lento o fallando
    turnos = [f for f in hoy if f['tipo'] == 'turno']
    cerebro = [f['ms'] for f in turnos if f['origen'] == 'cerebro' and f['ms'] is not None]
    if len(cerebro) >= 3 and percentil(cerebro, 50) > 6000:
        agregar('cerebro_lento', 'media', 'El cerebro local tarda en decidir',
                f'Mediana de {percentil(cerebro, 50) / 1000:.1f} s en {len(cerebro)} órdenes.',
                'Usá un modelo más chico (OLLAMA_MODEL=qwen2.5:3b) o una tarjeta gráfica; las órdenes repetidas ya se aprenden.')
    turnos_err = [f for f in turnos if not f['ok']]
    if len(turnos) >= 5 and len(turnos_err) / len(turnos) >= 0.3:
        agregar('turnos_error', 'alta', 'Muchas respuestas con error',
                f'{len(turnos_err)} de {len(turnos)} mensajes terminaron en error. Último: {turnos_err[-1]["detalle"] or "sin detalle"}.',
                'Revisá el motor de IA (Ollama encendido o una clave configurada).')
    return problemas


def resumen(periodo: str = 'hoy', ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now()
    periodo = 'semana' if periodo == 'semana' else 'hoy'
    desde = _desde(periodo, ahora)
    filas = _filas(desde, ahora.timestamp() + 1)

    acciones = [f for f in filas if f['tipo'] in ('accion', 'casa')]
    ok = [f for f in acciones if f['ok']]
    fallidas = [f for f in acciones if not f['ok']]
    por_accion = {}
    for f in acciones:
        d = por_accion.setdefault(f['nombre'], {'accion': f['nombre'], 'nombre': NOMBRES_ACCION.get(f['nombre'], f['nombre']),
                                                'completadas': 0, 'fallidas': 0, 'ms': []})
        d['completadas' if f['ok'] else 'fallidas'] += 1
        if f['ms'] is not None:
            d['ms'].append(f['ms'])
    tabla = sorted(({**{k: v for k, v in d.items() if k != 'ms'}, 'p50_ms': percentil(d['ms'], 50)} for d in por_accion.values()),
                   key=lambda d: -(d['completadas'] + d['fallidas']))

    turnos = [f for f in filas if f['tipo'] == 'turno']
    origenes = {}
    for f in turnos:
        origenes.setdefault(f['origen'] or 'reglas', []).append(f['ms'])
    api = [f for f in filas if f['tipo'] == 'api']
    rutas = {}
    for f in api:
        rutas.setdefault(f['nombre'], []).append(f['ms'])
    lentas = sorted(({'ruta': r, **_estad(ms)} for r, ms in rutas.items() if len(ms) >= 3),
                    key=lambda x: -(x['p95_ms'] or 0))[:5]

    horas = {}
    for f in acciones:
        h = datetime.fromtimestamp(f['ts']).strftime('%Y-%m-%d %H:00' if periodo == 'semana' else '%H:00')
        horas.setdefault(h, {'completadas': 0, 'fallidas': 0})['completadas' if f['ok'] else 'fallidas'] += 1

    agente = [f for f in filas if f['tipo'] == 'agente']
    base = _filas(_desde('hoy', ahora) - 7 * 86400, _desde('hoy', ahora))
    hoy_filas = filas if periodo == 'hoy' else [f for f in filas if f['ts'] >= _desde('hoy', ahora)]

    voz = [f for f in filas if f['tipo'] == 'voz']
    stt = [f for f in api if '/stt/' in f['nombre']]
    tts = [f for f in api if f['nombre'].endswith('/api/hud/tts')]
    tareas = [f for f in filas if f['tipo'] == 'tarea']
    modelo = [f for f in filas if f['tipo'] == 'modelo']
    rechazos_agente = [f for f in acciones if not f['ok'] and re.search(r'desactivad|no permitid|denied|403|confirmaci', f['detalle'] or '', re.I)]
    arranques = [f for f in filas if f['tipo'] == 'servicio' and f['nombre'] == 'inicio']
    errores_5xx = sum(1 for f in api if (f['codigo'] or 0) >= 500)
    r = {
        'periodo': periodo, 'desde': datetime.fromtimestamp(desde).isoformat(timespec='seconds'),
        'generado': ahora.isoformat(timespec='seconds'), 'eventos': len(filas),
        'acciones': {'total': len(acciones), 'completadas': len(ok), 'fallidas': len(fallidas),
                     'tasa_exito': round(len(ok) / len(acciones) * 100, 1) if acciones else None,
                     **_estad([f['ms'] for f in acciones]),
                     'por_accion': tabla[:12],
                     'ultimas_fallidas': [{'accion': f['nombre'], 'nombre': NOMBRES_ACCION.get(f['nombre'], f['nombre']),
                                           'motivo': f['detalle'], 'hora': datetime.fromtimestamp(f['ts']).strftime('%H:%M'),
                                           'tipo': f['tipo']} for f in reversed(fallidas[-10:])]},
        'automatizacion': {'propuestas': sum(1 for f in tareas if f['nombre'] == 'propuesta'),
                           'canceladas': sum(1 for f in tareas if f['nombre'] == 'cancelada'),
                           'confirmadas': sum(1 for f in tareas if f['nombre'] == 'confirmada'),
                           'interfaz': sum(1 for f in filas if f['tipo'] == 'interfaz')},
        'asistente': {'turnos': len(turnos), 'errores': sum(1 for f in turnos if not f['ok']),
                      'por_origen': {o: _estad(ms) for o, ms in origenes.items()}},
        'modelo': resumen_modelo(modelo),
        'api': {'peticiones': len(api), 'errores_5xx': errores_5xx,
                'rechazos_4xx': sum(1 for f in api if 400 <= (f['codigo'] or 0) < 500),
                'disponibilidad': round((len(api) - errores_5xx) / len(api) * 100, 2) if api else None,
                **_estad([f['ms'] for f in api]), 'rutas_lentas': lentas},
        'agente': {'consultas': len(agente), 'sin_respuesta': sum(1 for f in agente if not f['ok']),
                   'disponibilidad': round(sum(1 for f in agente if f['ok']) / len(agente) * 100, 1) if agente else None},
        'voz': {'primera_voz': _estad([f['ms'] for f in voz if f['nombre'] == 'primera_voz']),
                'reconocimiento': {**_estad([f['ms'] for f in stt]), 'errores': sum(1 for f in stt if not f['ok'] or (f['codigo'] or 0) >= 400)},
                'sintesis': {**_estad([f['ms'] for f in tts]), 'errores': sum(1 for f in tts if not f['ok'] or (f['codigo'] or 0) >= 400)},
                # v12.6: escucha manos libres, etapa por etapa (interpretación, agente, modelo, voz) y turno completo.
                'manos_libres': {**{etapa: _estad([f['ms'] for f in voz if f['nombre'] == 'ml_' + etapa])
                                    for etapa in ('interpretar', 'ejecutar', 'modelo', 'tts', 'turno')},
                                 'turnos': sum(1 for f in voz if f['nombre'] == 'ml_turno'),
                                 'errores': sum(1 for f in voz if f['nombre'].startswith('ml_') and not f['ok']),
                                 'acciones_verificadas': sum(1 for f in voz if f['nombre'] == 'ml_ejecutar' and f['detalle'] == 'verificada'),
                                 'acciones_sin_comprobar': sum(1 for f in voz if f['nombre'] == 'ml_ejecutar' and f['detalle'] == 'enviada')},
                'interrupciones': sum(1 for f in voz if f['nombre'] == 'interrupcion'),
                'errores_audio': sum(1 for f in voz if f['nombre'] in ('error_microfono', 'error_reproduccion'))},
        'seguridad': {'autorizadas': len(ok), 'rechazadas': len(rechazos_agente),
                      'accesos_fallidos': sum(1 for f in api if f['codigo'] == 401),
                      'prohibidos': sum(1 for f in api if f['codigo'] == 403),
                      'confirmaciones_pendientes': pendientes_confirmacion()},
        'servicio': {'arranques': len(arranques),
                     'reinicios': sum(1 for f in filas if f['tipo'] == 'servicio' and f['nombre'] == 'reinicio'),
                     'whatsapp_enviados': sum(1 for f in filas if f['tipo'] == 'servicio' and f['nombre'] == 'whatsapp_enviado'),
                     'whatsapp_plantillas': sum(1 for f in filas if f['tipo'] == 'servicio' and f['nombre'] == 'whatsapp_plantilla'),
                     'whatsapp_enviados_mes': whatsapp_del_mes(ahora),
                     'whatsapp_rechazados': sum(1 for f in filas if f['tipo'] == 'servicio' and f['nombre'] in ('whatsapp_rechazado', 'whatsapp_firma')),
                     'ultimo_arranque': datetime.fromtimestamp(arranques[-1]['ts']).isoformat(timespec='seconds') if arranques else None},
        'serie': [{'hora': h, **v} for h, v in sorted(horas.items())],
        'problemas': detectar(ahora, hoy_filas, base),
        'sistema': sistema(),
    }
    r['slo'] = evaluar_slo(r)
    return r


def resumen_modelo(filas: list) -> dict:
    """Llamadas al cerebro por proveedor: tokens reales informados por cada API. Costo sólo si definís el precio."""
    por = {}
    for f in filas:
        prov = f['nombre'].split(':', 1)[0]
        d = por.setdefault(prov, {'llamadas': 0, 'tokens': 0, 'errores': 0})
        d['llamadas'] += 1
        d['tokens'] += f['tokens'] or 0
        d['errores'] += 0 if f['ok'] else 1
    costo, sin_precio = 0.0, []
    for prov, d in por.items():
        if prov == 'ollama':
            d['costo_usd'] = 0.0
            continue
        try:
            precio = float(os.getenv(f'SKY_COSTO_{prov.upper()}_USD_1K', ''))
            d['costo_usd'] = round(d['tokens'] / 1000 * precio, 4)
            costo += d['costo_usd']
        except ValueError:
            d['costo_usd'] = None
            sin_precio.append(prov)
    presupuesto = os.getenv('SKY_PRESUPUESTO_USD_MES', '').strip()
    return {'llamadas': len(filas), 'errores': sum(1 for f in filas if not f['ok']),
            'tokens': sum(f['tokens'] or 0 for f in filas), **_estad([f['ms'] for f in filas]),
            'por_proveedor': por,
            'costo_estimado_usd': None if (sin_precio or not filas) else round(costo, 4),
            'presupuesto_usd_mes': float(presupuesto) if re.fullmatch(r'\d+(?:\.\d+)?', presupuesto) else None,
            'nota': ('Ollama local no tiene costo por token.' +
                     (f" Sin precio configurado para {', '.join(sin_precio)} (SKY_COSTO_<PROVEEDOR>_USD_1K)." if sin_precio else ''))}


LIMITE_GRATIS_WHATSAPP = 1000   # mensajes de servicio gratis por mes y número (Meta, desde el 1/10/2026)


def whatsapp_del_mes(ahora: datetime) -> int:
    inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
    return sum(1 for f in _filas(inicio, ahora.timestamp() + 1, 'servicio') if f['nombre'] == 'whatsapp_enviado')


def pendientes_confirmacion() -> int | None:
    try:
        from .voz_inbox import read_inbox
        return len(read_inbox())
    except Exception:
        return None


def sistema() -> dict:
    datos = {}
    try:
        import shutil
        u = shutil.disk_usage(Path.home())
        datos.update(disco_usado_pct=round(u.used / u.total * 100, 1), disco_libre_gb=round(u.free / 1_073_741_824, 1))
        datos['base_kpi_mb'] = round(_ruta_db().stat().st_size / 1_048_576, 2) if _ruta_db().exists() else 0
    except OSError:
        pass
    try:
        import psutil
        proc = psutil.Process()
        datos.update(cpu_equipo=psutil.cpu_percent(interval=None), memoria_equipo=psutil.virtual_memory().percent,
                     memoria_sky_mb=round(proc.memory_info().rss / 1_048_576, 1), cpu_sky=proc.cpu_percent(interval=None))
    except Exception:
        datos['nota'] = 'Instalá psutil para medir CPU y RAM.'
    return datos


def _seg(ms) -> str:
    if ms is None:
        return '—'
    return f'{ms} ms' if ms < 1000 else f'{ms / 1000:.1f} s'.replace('.', ',')


ORIGENES = {'reglas': 'con reglas al instante', 'aprendido': 'con atajos aprendidos', 'cerebro': 'con el cerebro local',
            'ia': 'con la IA conversacional'}


def diagnosticar(r: dict) -> str:
    """«¿Qué está fallando?» / «¿por qué estás lenta?»: sólo evidencia medida, sin inventar causas."""
    if not r['eventos']:
        return 'Todavía no tengo mediciones de hoy, así que no puedo diagnosticar nada con evidencia.'
    partes = []
    for p in r['problemas'][:4]:
        partes.append(f"{p['titulo']}: {p['detalle'].rstrip('. ')}. Sugerencia: {p['sugerencia']}")
    incumplidos = [o for o in r.get('slo', []) if o['cumple'] is False]
    for o in incumplidos[:3]:
        partes.append(f"No se cumple el objetivo «{o['nombre']}»: {o['actual']:g} {o['unidad']} frente a {o['objetivo']:g} {o['unidad']}.")
    sis = r.get('sistema') or {}
    if sis.get('cpu_equipo') is not None and sis['cpu_equipo'] >= 85:
        partes.append(f"El equipo está con la CPU al {sis['cpu_equipo']:.0f} %: eso me hace más lenta.")
    if sis.get('memoria_equipo') is not None and sis['memoria_equipo'] >= 90:
        partes.append(f"La memoria RAM está al {sis['memoria_equipo']:.0f} %.")
    if sis.get('disco_usado_pct') is not None and sis['disco_usado_pct'] >= 95:
        partes.append(f"El disco está casi lleno ({sis['disco_usado_pct']:.0f} %).")
    cer = (r['asistente']['por_origen'].get('cerebro') or {})
    if cer.get('n') and not any('cerebro' in p['id'] for p in r['problemas']):
        partes.append(f"Referencia: el cerebro local tardó una mediana de {_seg(cer['p50_ms'])} en {cer['n']} órdenes.")
    if not partes:
        return ('Revisé mis indicadores reales y no encuentro fallas: ' + describir(r))
    return 'Esto es lo que encontré en mis mediciones. ' + ' '.join(partes)


def describir(r: dict) -> str:
    """Texto natural (para voz o chat) con las estadísticas reales."""
    cuando = 'Hoy' if r['periodo'] == 'hoy' else 'En los últimos 7 días'
    a, t, api = r['acciones'], r['asistente'], r['api']
    if not r['eventos']:
        return f'{cuando} todavía no tengo mediciones registradas.'
    partes = []
    if a['total']:
        txt = f"{cuando} completé {a['completadas']} de {a['total']} tareas ({a['tasa_exito']:.0f} %)".replace('.0 %', ' %')
        if a['fallidas']:
            grupos = {}
            for f in a['ultimas_fallidas']:
                g = grupos.setdefault(f['nombre'], {'n': 0, 'hora': f['hora'], 'motivo': f['motivo']})
                g['n'] += 1
            motivos = '; '.join(f"{n}" + (f" ({g['n']} veces)" if g['n'] > 1 else f" a las {g['hora']}") +
                                (f" — {g['motivo'][:60].rstrip('. ')}" if g['motivo'] else '') for n, g in list(grupos.items())[:3])
            txt += f". Fallaron {a['fallidas']}: {motivos}"
        else:
            txt += ' y no falló ninguna'
        partes.append(txt + '.')
    else:
        partes.append(f'{cuando} no ejecuté tareas en tus equipos.')
    if t['turnos']:
        detalle = ', '.join(f"{v['n']} {ORIGENES.get(o, o)} (mediana {_seg(v['p50_ms'])})"
                            for o, v in sorted(t['por_origen'].items(), key=lambda x: -x[1]['n']))
        partes.append(f"Respondí {t['turnos']} mensajes: {detalle}." + (f" {t['errores']} terminaron en error." if t['errores'] else ''))
    if api['peticiones']:
        partes.append(f"La API atendió {api['peticiones']} peticiones con p95 de {_seg(api['p95_ms'])} y {api['errores_5xx']} errores internos.")
    if r['problemas']:
        partes.append('Detecté ' + ('un problema: ' if len(r['problemas']) == 1 else f"{len(r['problemas'])} problemas: ") +
                      '; '.join(p['titulo'] for p in r['problemas'][:3]) + '.')
    else:
        partes.append('No detecté problemas de rendimiento.')
    return ' '.join(partes)


_PATRON = re.compile(r'\b(?:tu|tus|su|sus)\s+(?:propio |propias )?(?:rendimiento|estadisticas?|kpis?|metricas?|indicadores|desempeno)\b|'
                     r'\b(?:rendimiento|estadisticas?|kpis?|metricas?|indicadores|desempeno) de sky\b|'
                     r'^(?:muestra(?:me)?|mostrame|abre|abri|ver|dame|panel de|el panel de)?\s*(?:el |los |las )?(?:panel de )?'
                     r'(?:kpis?|metricas|indicadores|rendimiento|estadisticas)(?: de hoy| del dia| de la semana| de los ultimos 7 dias)?$|'
                     r'\bcuantas (?:tareas|acciones|ordenes) (?:completaste|hiciste|realizaste|fallaron|ejecutaste)|'
                     r'\b(?:que|cuales) (?:tareas |acciones |ordenes )?(?:fallaron|salieron mal)\b|'
                     r'\bcomo (?:estas funcionando|vas funcionando|te fue hoy)|'
                     r'\bque (?:esta|estas|anda) fallando\b|\banaliza (?:tu|el) rendimiento\b|'
                     r'\bpor que (?:estas|andas|vas|respondes|estas respondiendo) (?:tan )?(?:lent[ao]|despacio)')
_DIAGNOSTICO = re.compile(r'fallando|analiza|por que|lent[ao]|despacio|diagnost')


def interpretar(texto_normalizado: str) -> dict | None:
    if not _PATRON.search(texto_normalizado):
        return None
    diag = bool(_DIAGNOSTICO.search(texto_normalizado))
    if re.search(r'\b(semana|7 dias|siete dias|ultimos dias)\b', texto_normalizado):
        return {'tipo': 'kpi', 'periodo': 'semana', 'diagnostico': diag}
    return {'tipo': 'kpi', 'periodo': 'hoy', 'diagnostico': diag}
