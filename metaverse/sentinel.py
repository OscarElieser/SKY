"""SKY SENTINEL · sentinel_api_guard — la API de SKY es privada por defecto (cerrada si falla).

Antes de v12.5, cada ruta tenía que acordarse de pedir la llave del dueño, y la auditoría encontró 30 rutas
/api/* que no la pedían (entre ellas un REPL de Python y la lectura/borrado de memorias). Desde ahora:

  * TODA ruta /api/* y /v1/* exige la llave del dueño (X-SKY-KEY) y, si el 2FA del creador está activo,
    la sesión de segundo factor (X-SKY-SESSION). Una ruta nueva queda protegida aunque nadie se acuerde.
  * Excepciones explícitas y mínimas (PUBLICAS): salud, arranque local del HUD, textos de idioma y el estado
    del 2FA (que es necesario para iniciar sesión).
  * La comunidad multiusuario sólo se abre a otras personas si el dueño lo decide: SKY_COMUNIDAD_PUBLICA=1.
  * Los sensores pueden enviar telemetría con su propio token (SKY_TELEMETRIA_TOKEN), nunca con la llave del dueño.
  * Si la verificación falla por cualquier error interno, se niega el acceso (falla cerrado).
  * Cada rechazo queda en los KPIs (accesos fallidos) sin guardar la llave probada; tras 30 rechazos en 5 minutos
    desde una misma dirección se responde 429 a los intentos inválidos (la llave correcta siempre entra:
    adivinarla es inviable y así no se bloquea al dueño por una sospecha).

Este control no depende del modelo de IA: es código que corre antes de cualquier ruta.
"""
from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

PUBLICAS = frozenset({
    ('GET', '/api/health'), ('GET', '/api/client/bootstrap'),
    ('GET', '/api/i18n/languages'), ('GET', '/api/i18n/phrases'), ('GET', '/api/i18n/ui'),
    ('GET', '/api/security/owner-mfa/status'), ('POST', '/api/sentinel/desbloquear'),
})
LOCALES = frozenset({'127.0.0.1', '::1', 'localhost', 'testclient'})
# Rutas que piden sólo la llave (son las que crean la sesión de 2FA).
SOLO_LLAVE = frozenset({('POST', '/api/security/owner-mfa/session')})
VENTANA = 300
MAX_FALLOS = 30
_FALLOS: dict[str, deque] = defaultdict(deque)


def comunidad_publica() -> bool:
    return os.getenv('SKY_COMUNIDAD_PUBLICA', '0').strip() == '1'


def _sensor_ok(request: Request) -> bool:
    esperado = os.getenv('SKY_TELEMETRIA_TOKEN', '').strip()
    dado = request.headers.get('X-SKY-SENSOR-TOKEN', '')
    return len(esperado) >= 24 and secrets.compare_digest(dado.encode(), esperado.encode())


def es_publica(metodo: str, ruta: str) -> bool:
    return (metodo, ruta) in PUBLICAS or (comunidad_publica() and ruta.startswith('/api/community/'))


def _registrar_rechazo(request: Request, ruta: str, codigo: int, motivo: str) -> None:
    try:
        from neural_core import sky_metricas
        sky_metricas.registrar('api', f'{request.method} {sky_metricas.ruta_plantilla(ruta)}', True, 0, codigo=codigo,
                               origen='sentinel', detalle=motivo)
    except Exception:
        pass


def _demasiados(ip: str, ahora: float) -> bool:
    q = _FALLOS[ip]
    while q and ahora - q[0] > VENTANA:
        q.popleft()
    return len(q) >= MAX_FALLOS


def verificar(request: Request) -> tuple[bool, int, str]:
    """(permitido, código, motivo). Falla cerrado ante cualquier error."""
    metodo, ruta = request.method.upper(), request.url.path
    if metodo == 'OPTIONS' or not ruta.startswith(('/api/', '/v1/')):
        return True, 200, ''
    try:
        from neural_core.sentinel_identidad import solo_local
        if solo_local() and (request.client.host if request.client else '') not in LOCALES:
            return False, 403, 'modo «sólo este equipo»: conexión remota rechazada'
    except Exception:
        return False, 503, 'verificación de seguridad no disponible'
    if es_publica(metodo, ruta):
        return True, 200, ''
    if ruta == '/api/telemetria/push' and _sensor_ok(request):
        return True, 200, ''
    try:
        from .api import api_token
        llave = request.headers.get('X-SKY-KEY', '')
        if not llave or not secrets.compare_digest(llave.encode(), api_token().encode()):
            return False, 401, 'llave inválida o ausente'
        if (metodo, ruta) in SOLO_LLAVE:
            return True, 200, ''
        from . import owner_mfa
        if owner_mfa.required() and not owner_mfa.valid(request.headers.get('X-SKY-SESSION')):
            return False, 401, 'falta la sesión de segundo factor'
        return True, 200, ''
    except Exception:
        return False, 503, 'verificación de seguridad no disponible'


def install(app) -> None:
    @app.middleware('http')
    async def sentinel_api_guard(request: Request, call_next):
        ok, codigo, motivo = verificar(request)
        if ok:
            return await call_next(request)
        ip = request.client.host if request.client else 'desconocido'
        ahora = time.monotonic()
        if codigo == 401:
            if _demasiados(ip, ahora):
                _registrar_rechazo(request, request.url.path, 429, 'demasiados intentos')
                return JSONResponse({'detail': 'Demasiados intentos fallidos. Esperá unos minutos.'}, status_code=429,
                                    headers={'Retry-After': '300'})
            _FALLOS[ip].append(ahora)
        _registrar_rechazo(request, request.url.path, codigo, motivo)
        textos = {401: 'Credenciales inválidas', 403: 'SKY sólo acepta conexiones de este equipo.', 503: 'Seguridad no disponible'}
        return JSONResponse({'detail': textos.get(codigo, 'Acceso denegado')},
                            status_code=codigo, headers={'WWW-Authenticate': 'APIKey'} if codigo == 401 else {})


def exigir_pin(request: Request, que: str) -> None:
    """Operaciones críticas: si el dueño configuró un PIN, se exige en ESTA solicitud (X-SKY-PIN).
    Lo comprueba el servidor, no el modelo de IA ni la interfaz."""
    from fastapi import HTTPException
    from neural_core import sentinel_identidad as ident
    if not ident.pin_configurado():
        return
    espera = ident.bloqueado_por()
    if espera:
        raise HTTPException(429, f'Demasiados PIN incorrectos. Esperá {espera // 60 + 1} minutos.')
    if not ident.verificar_pin(request.headers.get('X-SKY-PIN', '')):
        try:
            from neural_core import sky_metricas
            sky_metricas.registrar('servicio', 'sentinel_bloqueo_pin', False, detalle=que[:80])
        except Exception:
            pass
        raise HTTPException(403, f'Se requiere tu PIN para {que}.')
