"""SKY · configuración local del PIN del dueño (v12.6).

    python sky_pin.py configurar     # crear el PIN (o cambiarlo: pide el actual)
    python sky_pin.py estado         # ¿hay PIN? ¿la sesión está bloqueada?
    python sky_pin.py bloquear       # bloquear SKY ahora (voz, HUD, WhatsApp y agente)
    python sky_pin.py desbloquear    # abrir la sesión escribiendo el PIN
    python sky_pin.py restablecer    # recuperación local si olvidaste el PIN

Seguridad:
  * El PIN se escribe sin eco (getpass); nunca se acepta como argumento (quedaría en el historial de la consola).
  * Se guarda sólo un verificador scrypt con sal aleatoria en ~/.neuralt/sentinel.json; ni el PIN ni su audio se
    registran en archivos, KPIs o documentación.
  * «restablecer» funciona en la consola de este equipo: quien tenga tu sesión de Windows abierta puede usarlo.
    Protegé tu cuenta de Windows con contraseña o Windows Hello.
  * Conocer el PIN no identifica a la persona: si alguien lo escucha cuando lo decís, puede repetirlo. Cambialo si
    sospechás que lo oyeron.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from neural_core import sentinel_identidad as ident  # noqa: E402


def _leer(mensaje: str) -> str:
    return getpass.getpass(mensaje).strip()


def configurar() -> int:
    actual = None
    if ident.pin_configurado():
        actual = _leer('PIN actual: ')
    nuevo = _leer('Nuevo PIN (6 a 12 dígitos): ')
    if _leer('Repetí el nuevo PIN: ') != nuevo:
        print('Los PIN no coinciden. No cambié nada.')
        return 1
    try:
        ident.establecer_pin(nuevo, actual)
    except ValueError as exc:
        print(f'PIN no válido: {exc}')
        return 1
    except PermissionError as exc:
        print(str(exc))
        return 1
    print('PIN guardado (sólo su verificador scrypt). La próxima vez que inicies SKY te va a preguntar «¿Cuál es tu PIN?».')
    print('Podés decirlo en voz alta dígito por dígito («cuatro, siete, dos…») o escribirlo en la interfaz.')
    return 0


def estado() -> int:
    e = ident.estado_sesion()
    if not e['pin']:
        print('Sin PIN: cualquiera frente a tu PC o cerca del micrófono puede usar SKY. Ejecutá: python sky_pin.py configurar')
        return 0
    print('PIN configurado. Sesión ' + ('BLOQUEADA' if e['bloqueada'] else 'abierta') + (f" ({e['motivo']})" if e.get('motivo') else '') + '.')
    if e.get('pin_bloqueado_s'):
        print(f"Intentos bloqueados por {e['pin_bloqueado_s'] // 60 + 1} minutos más.")
    return 0


def bloquear() -> int:
    if ident.bloquear_sesion('pedido desde la consola', 'consola'):
        print('SKY bloqueada. Decí o escribí tu PIN para volver.')
        return 0
    print('No hay PIN configurado: no se puede bloquear.')
    return 1


def desbloquear() -> int:
    r = ident.desbloquear_sesion(_leer('PIN: '), 'consola')
    print(r['mensaje'] + (f" Te quedan {r['restantes']} intentos." if 'restantes' in r else ''))
    return 0 if r['ok'] else 1


def restablecer() -> int:
    print('Esto quita el PIN, los intentos fallidos y el bloqueo de la sesión. Tu memoria, permisos e historial NO se tocan.')
    if input('Escribí RESTABLECER para continuar: ').strip() != 'RESTABLECER':
        print('Cancelado.')
        return 1
    ident.restablecer_local()
    print('Listo. SKY quedó sin PIN: configurá uno nuevo ahora con  python sky_pin.py configurar')
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('accion', choices=['configurar', 'estado', 'bloquear', 'desbloquear', 'restablecer'])
    a = p.parse_args(argv)
    return {'configurar': configurar, 'estado': estado, 'bloquear': bloquear,
            'desbloquear': desbloquear, 'restablecer': restablecer}[a.accion]()


if __name__ == '__main__':
    raise SystemExit(main())
