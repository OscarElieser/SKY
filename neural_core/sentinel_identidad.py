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

import contextlib
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

from .sky_archivo_seguro import bloqueo, escribir_json, leer_json

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
    """v12.6: escritura atómica (temporal + os.replace); se llama bajo _candado()."""
    p = ruta()
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    escribir_json(p, d, privado=True)


@contextlib.contextmanager
def _candado():
    """v12.6: la API, la voz y el agente son procesos distintos; el candado de hilos no alcanzaba para
    leer-modificar-escribir sentinel.json (dos PIN fallidos simultáneos podían contarse como uno)."""
    with _LOCK, bloqueo(ruta()):
        yield


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
    with _candado():
        d = _datos()
    if d.get('pin') and not verificar_pin(actual or ''):
        raise PermissionError('El PIN actual no es correcto.')
    sal = secrets.token_bytes(16)
    with _candado():
        d = _datos()
        d['pin'] = {'sal': sal.hex(), 'hash': _derivar(nuevo, sal).hex(), 'creado': int(time.time())}
        d['fallos'], d['bloqueado_hasta'] = [], 0
        _guardar(d)
    # Quien acaba de crear o cambiar el PIN está presente: la sesión queda abierta.
    _escribir_sesion(False, 'pin configurado', 'configuracion')
    _auditar('pin_cambiado')


def quitar_pin(actual: str) -> None:
    if not verificar_pin(actual):
        raise PermissionError('El PIN actual no es correcto.')
    with _candado():
        d = _datos()
        d.pop('pin', None)
        _guardar(d)
    _auditar('pin_quitado')


def bloqueado_por(ahora: float | None = None) -> int:
    """Segundos que faltan del bloqueo por intentos fallidos (0 = libre)."""
    return max(0, int(_datos().get('bloqueado_hasta', 0) - (ahora or time.time())))


def verificar_pin(pin: str, ahora: float | None = None) -> bool:
    ahora = ahora or time.time()
    with _candado():
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


# ------------------------------------------------------------------ sesión del dueño (v12.6)
#
# Antes, el PIN sólo bloqueaba la interfaz del navegador: la voz manos libres, WhatsApp, el panel Streamlit y el
# agente del equipo seguían obedeciendo. Ahora hay UNA sesión compartida por todos los procesos de SKY:
#   * Con PIN configurado, SKY arranca BLOQUEADA y pregunta «¿Cuál es tu PIN?».
#   * Bloqueada: la API responde 423 (salvo salud, desbloqueo y parada de emergencia), la voz sólo acepta el PIN y la
#     parada, WhatsApp no ejecuta nada y el agente rechaza acciones (salvo avisos programados de nivel 1).
#   * Se desbloquea con el PIN (hablado o escrito) y se vuelve a bloquear por voz, texto o al caducar.
#   * Si el archivo de sesión no se puede leer, se considera BLOQUEADA (falla cerrado).
#   * Desbloquear no cambia permisos: la política por dispositivo y herramienta sigue igual.
# Conocer el PIN no identifica a quien habla: alguien que lo escuche o lo grabe puede repetirlo.

DIGITOS_HABLADOS = {'cero': '0', 'uno': '1', 'un': '1', 'una': '1', 'dos': '2', 'tres': '3', 'cuatro': '4',
                    'cinco': '5', 'seis': '6', 'siete': '7', 'ocho': '8', 'nueve': '9'}
_RELLENO = frozenset({'mi', 'pin', 'es', 'el', 'la', 'clave', 'codigo', 'numero', 'sky', 'esquai', 'escai', 'oye',
                      'hey', 'ok', 'y', 'de', 'seguridad', 'desbloquea', 'desbloquear', 'desbloqueate'})


def ruta_sesion() -> Path:
    return ruta().with_name('sentinel_sesion.json')


def max_horas_sesion() -> float:
    try:
        return max(0.0, float(os.getenv('SKY_SESION_MAX_HORAS', '12')))
    except ValueError:
        return 12.0


def _escribir_sesion(bloqueada: bool, motivo: str, canal: str) -> None:
    escribir_json(ruta_sesion(), {'bloqueada': bool(bloqueada), 'desde': time.time(), 'motivo': str(motivo)[:80],
                                  'canal': str(canal)[:20]}, privado=True)


def estado_sesion(ahora: float | None = None) -> dict:
    """Estado real de la sesión. Sin PIN configurado no hay bloqueo (y se informa como riesgo)."""
    ahora = ahora or time.time()
    if not pin_configurado():
        return {'pin': False, 'bloqueada': False, 'motivo': 'sin PIN configurado'}
    d = leer_json(ruta_sesion(), None)
    if not isinstance(d, dict):
        return {'pin': True, 'bloqueada': True, 'motivo': 'SKY se inició bloqueada', 'pin_bloqueado_s': bloqueado_por(ahora)}
    bloqueada = d.get('bloqueada') is not False
    motivo = str(d.get('motivo', ''))
    limite = max_horas_sesion()
    if not bloqueada and limite and ahora - float(d.get('desde') or 0) > limite * 3600:
        bloqueada, motivo = True, f'la sesión caducó ({limite:g} h)'
    return {'pin': True, 'bloqueada': bloqueada, 'motivo': motivo, 'canal': d.get('canal', ''),
            'desde': d.get('desde'), 'pin_bloqueado_s': bloqueado_por(ahora)}


def sesion_bloqueada() -> bool:
    try:
        return bool(estado_sesion()['bloqueada'])
    except Exception:
        return True   # falla cerrado


def bloquear_sesion(motivo: str = 'pedido del dueño', canal: str = '') -> bool:
    """Bloquea SKY en todos sus procesos. Devuelve False si no hay PIN (no se podría desbloquear después)."""
    if not pin_configurado():
        return False
    _escribir_sesion(True, motivo, canal)
    _auditar('sesion_bloqueada', f'{canal}: {motivo}')
    return True


def espera_entre_intentos(ahora: float | None = None) -> int:
    """Espera progresiva entre PIN incorrectos (2 fallos → 4 s, 3 → 8 s, 4 → 16 s; al 5.º, bloqueo de 15 min)."""
    ahora = ahora or time.time()
    fallos = [t for t in _datos().get('fallos', []) if ahora - t < BLOQUEO_S]
    if len(fallos) < 2:
        return 0
    return max(0, int(fallos[-1] + min(30, 2 ** len(fallos)) - ahora + 0.999))


def intentos_restantes() -> int:
    ahora = time.time()
    return max(0, MAX_FALLOS - len([t for t in _datos().get('fallos', []) if ahora - t < BLOQUEO_S]))


def desbloquear_sesion(pin: str, canal: str = '') -> dict:
    """Única puerta para abrir la sesión (HUD, voz, Streamlit, consola). Respeta el bloqueo y la espera progresiva."""
    if not pin_configurado():
        return {'ok': True, 'mensaje': 'No hay PIN configurado: SKY no está protegida.'}
    espera = bloqueado_por()
    if espera:
        return {'ok': False, 'espera_s': espera,
                'mensaje': f'Demasiados PIN incorrectos. Esperá {espera // 60 + 1} minutos.'}
    pausa = espera_entre_intentos()
    if pausa:
        return {'ok': False, 'espera_s': pausa, 'mensaje': f'Esperá {pausa} segundos antes de volver a intentar.'}
    if verificar_pin(pin):
        _escribir_sesion(False, 'PIN correcto', canal)
        _auditar('sesion_desbloqueada', canal)
        return {'ok': True, 'mensaje': 'PIN correcto. SKY desbloqueada.'}
    espera = bloqueado_por()
    if espera:
        return {'ok': False, 'espera_s': espera,
                'mensaje': f'PIN incorrecto. Bloqueé los intentos {espera // 60 + 1} minutos.'}
    return {'ok': False, 'restantes': intentos_restantes(), 'mensaje': 'PIN incorrecto.'}


def pin_desde_voz(texto: str) -> str | None:
    """Convierte «cuatro siete dos …» (o «4 7 2 …») en dígitos. Sólo dígitos dichos de a uno: «veinte» no vale.
    No guarda ni devuelve el texto original."""
    import unicodedata
    plano = unicodedata.normalize('NFD', str(texto or '').lower())
    plano = ''.join(c for c in plano if unicodedata.category(c) != 'Mn')
    digitos = []
    for palabra in re.findall(r'[a-z]+|\d+', plano):
        if palabra.isdigit():
            digitos.append(palabra)
        elif palabra in DIGITOS_HABLADOS:
            digitos.append(DIGITOS_HABLADOS[palabra])
        elif palabra not in _RELLENO:
            return None
    pin = ''.join(digitos)
    return pin if re.fullmatch(r'\d{6,12}', pin) else None


def restablecer_local() -> None:
    """Recuperación local (consola de este equipo): quita el PIN, los intentos fallidos y el bloqueo de sesión.
    Quien tenga tu sesión de Windows abierta puede hacerlo: protegé tu cuenta de Windows con contraseña."""
    with _candado():
        d = _datos()
        d.pop('pin', None)
        d['fallos'], d['bloqueado_hasta'] = [], 0
        _guardar(d)
    try:
        ruta_sesion().unlink()
    except OSError:
        pass
    _auditar('pin_restablecido_local')


# ------------------------------------------------------------------ «sólo este equipo»

def solo_local() -> bool:
    return bool(_datos().get('solo_local')) or os.getenv('SKY_SOLO_LOCAL', '0').strip() == '1'


def cambiar_solo_local(activo: bool) -> None:
    with _candado():
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
