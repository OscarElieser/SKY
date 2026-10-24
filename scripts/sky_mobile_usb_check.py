"""Read-only Windows USB phone diagnostic for SKY Mobile Unlock.

Run from SKY repository root, with a phone personally owned or authorized:
    python scripts/sky_mobile_usb_check.py --i-own-or-have-permission

Never performs SIM unlock, flashes firmware, changes IMEI or reads private
phone data; all output is safe and excludes serial numbers.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))


def main() -> int:
    parser=argparse.ArgumentParser(description="SKY Mobile — diagnóstico USB de solo lectura")
    parser.add_argument("--i-own-or-have-permission",action="store_true",
                        help="Confirmo propiedad o permiso explícito del propietario")
    args=parser.parse_args()
    if not args.i_own_or_have_permission:
        parser.error("No es posible inspeccionar un equipo sin permiso del titular.")
    from neural_core.sky_mobile_unlock import diagnose_usb
    try:
        result=diagnose_usb(owner_attested=True)
    except (PermissionError,RuntimeError) as exc:
        print("SKY:",str(exc))
        return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result.get("ok"):
        print("\nSKY: el estado de bloqueo de operador NO se deduce de ADB. "
              "Confirmá con el operador original.")
        return 0
    return 1


if __name__=="__main__":
    raise SystemExit(main())
