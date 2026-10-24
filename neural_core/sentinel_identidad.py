"""SKY SENTINEL · sentinel_identity — PIN del dueño, bloqueo de la interfaz y estado de seguridad local.

Por qué: en tu PC, la interfaz recibía la llave del dueño automáticamente (127.0.0.1). Cualquiera sentado frente a tu
equipo desbloqueado podía usar SKY. Con un PIN configurado:
  * La interfaz arranca BLOQUEADA y pide el PIN para recibir la llave (nada se revela sin él).
  * Lo crítico (enviar correos, aprobar habilidades, exportar tu memoria, levantar la parada de emergencia, acciones
    de nivel 3, cerraduras) exige el PIN en ese momento, además del clic. Una voz grabada no alcanza.
  * 5 PIN incorrectos bloquean los intentos 15 minutos (también entre reinicios).
El PIN se guarda derivado con scrypt (sal aleatoria), nunca en texto. Datos: ~/.neuralt/sentinel.json (0600).

También guarda el interruptor «sólo este equipo»: si está activo, la API rechaza toda conexión que no venga del
propio equipo (por ejemplo, el celular por Tailscale), sin importar la llave.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

_LOCK = threading.Lock()
MAX_FALLOS = 5
BLOQUEO_S = 15 * 60
_SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)


def ruta() -> Path:
    return Path.home() / '.neuralt' / 'sentinel.json'


def _datos() -> dict:
    try:
        d = json.loads(ruta().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _guardar(d: dict) -> None:
    p = ruta()
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(d), encoding='utf-8')
    tmp.replace(p)
    try:
        p.chmod(0o600)
    except OSError:
        pass


def _auditar(evento: str, detalle: str = '') -> None:
    try:
        from .sky_metricas import registrar
        registrar('servicio', 'sentinel_' + evento, evento not in ('pin_fallido', 'pin_bloqueado'), detalle=detalle[:120])
    except Exception:
        pass


def pin_configurado() -> bool:
    return bool(_datos().get('pin'))


def _derivar(pin: str, sal: bytes) -> bytes:
    return hashlib.scrypt(pin.encode('utf-8'), salt=sal, **_SCRYPT)


def validar_formato(pin: str) -> None:
    if not re.fullmatch(r'\d{6,12}', str(pin or '')):
        raise ValueError('El PIN debe tener entre 6 y 12 dígitos.')
    if len(set(pin)) == 1 or pin in '01234567890123' or pin in '98765432109876':
        raise ValueError('Elegí un PIN que no sea repetido ni consecutivo.')


def establecer_pin(nuevo: str, actual: str | None = None) -> None:
    """Crea o cambia el PIN. Cambiarlo exige el PIN actual (autenticación reforzada)."""
    validar_formato(nuevo)
    with _LOCK:
        d = _datos()
    if d.get('pin') and not verificar_pin(actual or ''):
        raise PermissionError('El PIN actual no es correcto.')
    sal = secrets.token_bytes(16)
    with _LOCK:
        d = _datos()
        d['pin'] = {'sal': sal.hex(), 'hash': _derivar(nuevo, sal).hex(), 'creado': int(time.time())}
        d['fallos'], d['bloqueado_hasta'] = [], 0
        _guardar(d)
    _auditar('pin_cambiado')


def quitar_pin(actual: str) -> None:
    if not verificar_pin(actual):
        raise PermissionError('El PIN actual no es correcto.')
    with _LOCK:
        d = _datos()
        d.pop('pin', None)
        _guardar(d)
    _auditar('pin_quitado')


def bloqueado_por(ahora: float | None = None) -> int:
    """Segundos que faltan del bloqueo por intentos fallidos (0 = libre)."""
    return max(0, int(_datos().get('bloqueado_hasta', 0) - (ahora or time.time())))


def verificar_pin(pin: str, ahora: float | None = None) -> bool:
    ahora = ahora or time.time()
    with _LOCK:
        d = _datos()
        info = d.get('pin')
        if not info:
            return False
        if d.get('bloqueado_hasta', 0) > ahora:
            _auditar('pin_bloqueado')
            return False
        ok = bool(re.fullmatch(r'\d{6,12}', str(pin or ''))) and hmac.compare_digest(
            _derivar(str(pin), bytes.fromhex(info['sal'])).hex(), info['hash'])
        if ok:
            d['fallos'] = []
        else:
            fallos = [t for t in d.get('fallos', []) if ahora - t < BLOQUEO_S] + [ahora]
            d['fallos'] = fallos
            if len(fallos) >= MAX_FALLOS:
                d['bloqueado_hasta'], d['fallos'] = ahora + BLOQUEO_S, []
        _guardar(d)
    _auditar('pin_ok' if ok else 'pin_fallido')
    return ok


# ------------------------------------------------------------------ «sólo este equipo»

def solo_local() -> bool:
    return bool(_datos().get('solo_local')) or os.getenv('SKY_SOLO_LOCAL', '0').strip() == '1'


def cambiar_solo_local(activo: bool) -> None:
    with _LOCK:
        d = _datos()
        d['solo_local'] = bool(activo)
        _guardar(d)
    _auditar('solo_local_' + ('activado' if activo else 'desactivado'))


# ------------------------------------------------------------------ automatizaciones

def pausar_automatizaciones() -> int:
    """Pausa todas las tareas programadas (se reactivan una por una)."""
    from . import sky_rutinas
    n = 0
    for r in sky_rutinas.agenda()['rutinas']:
        if r.get('hora') and r.get('activa', True):
            sky_rutinas.activar_rutina(r['id'], False)
            n += 1
    _auditar('automatizaciones_pausadas', str(n))
    return n
