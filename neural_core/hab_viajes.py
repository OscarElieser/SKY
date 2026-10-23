"""sky-travel — planificar viajes: presupuesto por rubro y por día, clima previsto, cambio de moneda e itinerario.

    "planifica un viaje a Granada de 3 días con 200 dólares"
    "planifica un viaje a San Juan del Sur de 2 días con 4000 córdobas"
Fuentes públicas sin clave (si SKY_INTERNET no es 0): Open-Meteo (geocodificación y pronóstico) y open.er-api.com
(tipo de cambio). El itinerario lo redacta la IA configurada; sin IA, SKY arma una estructura base.
El plan se guarda en tu base de conocimiento para retomarlo después.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import date

REPARTO = [('Alojamiento', 0.40), ('Comida', 0.25), ('Transporte', 0.20), ('Actividades', 0.10), ('Imprevistos', 0.05)]
MONEDAS = {'dolares': 'USD', 'dolar': 'USD', 'usd': 'USD', 'cordobas': 'NIO', 'cordoba': 'NIO', 'nio': 'NIO', 'euros': 'EUR',
           'euro': 'EUR', 'eur': 'EUR', 'pesos': 'MXN', 'quetzales': 'GTQ', 'colones': 'CRC', 'lempiras': 'HNL'}
CLIMA = {0: 'despejado', 1: 'mayormente despejado', 2: 'parcialmente nublado', 3: 'nublado', 45: 'niebla', 48: 'niebla',
         51: 'llovizna', 53: 'llovizna', 55: 'llovizna', 61: 'lluvia ligera', 63: 'lluvia', 65: 'lluvia fuerte',
         80: 'chubascos', 81: 'chubascos', 82: 'chubascos fuertes', 95: 'tormenta', 96: 'tormenta', 99: 'tormenta'}


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '').lower())
    return ' '.join(re.sub(r'[^\w\s.,]', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).split())


def _get(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'SKY-IA/12.4 (asistente personal)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(500_000))


def internet() -> bool:
    return os.getenv('SKY_INTERNET', '1').strip() != '0'


def presupuesto(total: float, dias: int) -> list[dict]:
    dias = max(1, dias)
    return [{'rubro': r, 'total': round(total * p, 2), 'por_dia': round(total * p / dias, 2)} for r, p in REPARTO]


def clima(destino: str, dias: int) -> dict | None:
    if not internet():
        return None
    g = _get('https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode(
        {'name': destino, 'count': 1, 'language': 'es', 'format': 'json'}))
    lugar = (g.get('results') or [None])[0]
    if not lugar:
        return None
    f = _get('https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode({
        'latitude': lugar['latitude'], 'longitude': lugar['longitude'], 'timezone': 'auto',
        'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
        'forecast_days': max(1, min(dias, 14))}))
    d = f.get('daily') or {}
    pron = [{'fecha': fe, 'cielo': CLIMA.get(int(c or 0), 'variable'), 'max': mx, 'min': mn, 'lluvia': ll}
            for fe, c, mx, mn, ll in zip(d.get('time', []), d.get('weather_code', []), d.get('temperature_2m_max', []),
                                          d.get('temperature_2m_min', []), d.get('precipitation_probability_max', []))]
    return {'lugar': f"{lugar.get('name')}, {lugar.get('country', '')}".strip(', '), 'dias': pron}


def cambio(moneda: str, a: str = 'USD') -> float | None:
    if not internet() or moneda == a:
        return None
    d = _get(f'https://open.er-api.com/v6/latest/{moneda}')
    tasa = (d.get('rates') or {}).get(a)
    return float(tasa) if d.get('result') == 'success' and tasa else None


def itinerario(destino: str, dias: int, total: float, moneda: str) -> str:
    try:
        from .providers import reply
        return str(reply([{'role': 'system', 'content': 'Sos SKY, asistente de viajes. Itinerario breve, realista y en español, '
                                                         'un bloque por día con mañana/tarde/noche. Sin inventar precios exactos.'},
                          {'role': 'user', 'content': f'Viaje a {destino}, {dias} días, presupuesto total {total:g} {moneda}.'}],
                         'auto', max_output_tokens=900)).strip()
    except Exception:
        return '\n'.join(f'Día {i}: mañana — recorrido a pie por el centro; tarde — actividad principal; noche — cena local.'
                         for i in range(1, dias + 1))


def planificar(destino: str, dias: int, total: float, moneda: str = 'USD') -> dict:
    destino = ' '.join(str(destino).split())[:80]
    if not destino or dias < 1 or dias > 60 or total <= 0:
        raise ValueError('Decime destino, días (1–60) y presupuesto.')
    plan = {'destino': destino, 'dias': dias, 'total': total, 'moneda': moneda, 'presupuesto': presupuesto(total, dias)}
    try:
        plan['clima'] = clima(destino, dias)
    except Exception:
        plan['clima'] = None
    try:
        tasa = cambio(moneda, 'USD' if moneda != 'USD' else 'NIO')
        if tasa:
            otra = 'USD' if moneda != 'USD' else 'NIO'
            plan['equivalente'] = {'moneda': otra, 'total': round(total * tasa, 2), 'tasa': tasa}
    except Exception:
        pass
    plan['itinerario'] = itinerario(destino, dias, total, moneda)
    try:
        from .storage import iniciar, agregar_documento
        iniciar()
        agregar_documento(f'SKY · viaje a {destino} ({date.today().isoformat()})', texto_plan(plan))
    except Exception:
        pass
    try:
        from . import sky_metricas
        sky_metricas.registrar('accion', 'planificar_viaje', True)
    except Exception:
        pass
    return plan


def texto_plan(p: dict) -> str:
    lineas = [f"Viaje a {p['destino']} · {p['dias']} días · presupuesto {p['total']:g} {p['moneda']}"]
    if p.get('equivalente'):
        e = p['equivalente']
        lineas.append(f"≈ {e['total']:g} {e['moneda']} (tipo de cambio de open.er-api.com)")
    lineas.append('Presupuesto: ' + '; '.join(f"{x['rubro']} {x['total']:g} ({x['por_dia']:g}/día)" for x in p['presupuesto']))
    if p.get('clima'):
        lineas.append(f"Clima en {p['clima']['lugar']} (Open-Meteo): " + '; '.join(
            f"{d['fecha']} {d['cielo']} {d['min']:.0f}–{d['max']:.0f} °C, lluvia {d['lluvia'] or 0} %" for d in p['clima']['dias']))
    lineas.append('Itinerario:\n' + p['itinerario'])
    return '\n'.join(lineas)


def interpretar(texto: str) -> dict | None:
    t = _norm(texto)
    m = re.search(r'\b(?:planifica|planea|organiza|arma|prepara)(?:me)? (?:un |mi )?viaje (?:a|para) (.+?)'
                  r'(?: (?:de|por|durante) (\d{1,2}) dias?)?(?: (?:con|y|presupuesto de|por) (?:un presupuesto de )?([\d.,]+) ?([a-z]+)?)?$', t)
    if not m:
        return None
    destino, dias = m.group(1), int(m.group(2) or 3)
    try:
        total = float((m.group(3) or '0').replace(',', '')) if m.group(3) else 0
    except ValueError:
        total = 0
    moneda = MONEDAS.get((m.group(4) or 'dolares').strip(), 'USD')
    from .sky_aprendizaje import _recuperar
    destino = _recuperar(texto, destino)
    if not total:
        return {'tipo': 'respuesta', 'proveedor': 'sky-travel',
                'mensaje': f'¿Con qué presupuesto viajás a {destino}? Decime por ejemplo «planifica un viaje a {destino} de {dias} días con 300 dólares».'}
    try:
        plan = planificar(destino, dias, total, moneda)
    except ValueError as exc:
        return {'tipo': 'respuesta', 'mensaje': str(exc), 'proveedor': 'sky-travel'}
    return {'tipo': 'respuesta', 'proveedor': 'sky-travel', 'mensaje': texto_plan(plan), 'viaje': plan}
