"""Diagnósticos seguros para las API de SKY: nunca imprimen claves, cuerpos
de solicitudes ni mensajes arbitrarios del proveedor.

Uso local (sin coste): python -m neural_core.sky_ai_diagnostics
Prueba real (puede consumir cuota): python -m neural_core.sky_ai_diagnostics --live
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error

# Sólo códigos públicos conocidos. No imprimir el mensaje bruto de la API.
_ESTADOS = frozenset({
    'INVALID_ARGUMENT', 'NOT_FOUND', 'RESOURCE_EXHAUSTED', 'PERMISSION_DENIED',
    'UNAUTHENTICATED', 'FAILED_PRECONDITION', 'INTERNAL', 'UNAVAILABLE',
    'DEADLINE_EXCEEDED', 'ABORTED', 'UNKNOWN',
    'invalid_api_key', 'insufficient_quota', 'rate_limit_exceeded',
    'model_not_found', 'invalid_request_error', 'invalid_request',
    'context_length_exceeded', 'unsupported_parameter',
    'billing_hard_limit_reached', 'model_not_supported',
    'credit_balance_exhausted', 'organization_spend_limit_exceeded',
    'project_spend_limit_exceeded', 'organization_usage_limit_exceeded',
    'slow_down', 'too_many_requests', 'quota_exceeded',
})

_ORIENTACION = {
    400: 'solicitud o parametros incompatibles con el modelo; revisa tambien el esquema de herramientas',
    401: 'autenticacion rechazada; revisa la clave API en tu equipo',
    402: 'se requiere credito o facturacion',
    403: 'acceso denegado; comprueba permisos, facturacion y modelo',
    404: 'modelo o ruta no disponible; revisa la variable de modelo',
    408: 'tiempo de espera agotado',
    422: 'solicitud no procesable; revisa los parametros',
    429: 'limite de peticiones o cuota; revisa el plan de la API',
    500: 'error interno del proveedor',
    502: 'servicio externo temporalmente no disponible',
    503: 'servicio externo temporalmente no disponible',
    504: 'servicio externo no respondio a tiempo',
}


def error_seguro(proveedor: str, exc: BaseException) -> str:
    """Descripción sin URL, cuerpo, API key, prompt ni mensajes sin filtrar."""
    nombre = str(proveedor).upper()
    if isinstance(exc, urllib.error.HTTPError):
        try:
            codigo = int(exc.code)
        except (TypeError, ValueError):
            codigo = 0
        estado = ''
        try:
            cuerpo = json.loads(exc.read(8192))
            datos = cuerpo.get('error', {}) if isinstance(cuerpo, dict) else {}
            if isinstance(datos, dict):
                # OpenAI incluye el motivo útil en error.code. Google lo
                # suele presentar en error.status. Ambos deben ser enumerados.
                for candidato in (datos.get('code'), datos.get('status')):
                    if isinstance(candidato, str) and candidato in _ESTADOS:
                        estado = candidato
                        break
        except (ValueError, TypeError, OSError, UnicodeError):
            pass
        razon = _ORIENTACION.get(codigo, 'consulta rechazada por el proveedor')
        if codigo == 429 and estado in (
            'credit_balance_exhausted', 'insufficient_quota',
            'organization_spend_limit_exceeded', 'project_spend_limit_exceeded',
            'organization_usage_limit_exceeded', 'billing_hard_limit_reached',
        ):
            razon = 'cuota o saldo agotado: revisa facturacion y limites; reintentar no repone el credito'
        return f'{nombre} HTTP {codigo}' + (f' ({estado})' if estado else '') + f': {razon}'
    if isinstance(exc, (TimeoutError,)):
        return f'{nombre}: tiempo de espera agotado'
    if isinstance(exc, urllib.error.URLError):
        return f'{nombre}: error de red, DNS, TLS o conexion'
    if isinstance(exc, (ValueError, KeyError, TypeError, json.JSONDecodeError)):
        return f'{nombre}: formato de respuesta inesperado'
    # No interpolar str(exc): algunos SDK incluyen secretos o contexto privado.
    return f'{nombre}: error interno de integracion ({type(exc).__name__})'


def main() -> int:
    parser = argparse.ArgumentParser(description='Diagnosticar API de SKY sin revelar credenciales')
    parser.add_argument('--live', action='store_true',
                        help='Realizar solicitudes reales (consumen cuota de los proveedores)')
    parser.add_argument('--providers', nargs='+', default=['gemini', 'openai'],
                        help='Proveedores a diagnosticar, por defecto gemini y openai')
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv('.env', override=True)
    from .providers import PROVIDERS, local_only, provider_ready
    from .sky_cerebro import _llamada_nube, _modelo_nube
    from .sky_ai_auction import CLOUD

    if any(p not in CLOUD for p in args.providers):
        parser.error('Proveedor desconocido; permitidos: ' + ', '.join(CLOUD))
    print('Modo SKY:', os.getenv('SKY_CEREBRO', 'auto'))
    print('Exclusivamente local:', local_only())
    print('Se realizaran consultas API:', args.live)
    if args.live and local_only():
        print('BLOQUEADO: SKY_LOCAL_ONLY impide realizar pruebas en la nube.')
        return 2

    errores = 0
    for proveedor in dict.fromkeys(args.providers):
        config = PROVIDERS[proveedor]
        estado = 'clave presente' if provider_ready(proveedor) else 'sin clave'
        mod = _modelo_nube(proveedor)
        print(f'[{proveedor}] {estado}; modelo: {mod}')
        if not args.live:
            continue
        if not provider_ready(proveedor):
            errores += 1
            continue
        inicio = time.perf_counter()
        try:
            nombre, argumentos, respuesta, tokens = _llamada_nube(proveedor, [
                {'role': 'system', 'content': 'Responde muy breve. No uses herramientas.'},
                {'role': 'user', 'content': 'Di solamente la palabra OK.'},
            ])
            if nombre or not respuesta.strip():
                print(f'[{proveedor}] RESPUESTA INESPERADA (sin texto de salida).')
                errores += 1
            else:
                print(f'[{proveedor}] OK; latencia_ms={round((time.perf_counter()-inicio)*1000)}')
        except Exception as exc:
            print('[' + proveedor + '] ' + error_seguro(proveedor, exc))
            errores += 1
    return 1 if errores else 0


if __name__ == '__main__':
    raise SystemExit(main())
