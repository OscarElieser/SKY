"""Prueba local de integración SKY API + agente en Windows.

Uso (PowerShell, desde la raíz del repositorio):
    .\\.venv\\Scripts\\python.exe scripts/sky_api_smoke_windows.py
    .\\.venv\\Scripts\\python.exe scripts/sky_api_smoke_windows.py --app calculator --execute

No muestra ni transmite tokens a terceros. Por defecto SOLO consulta el estado.
La prueba opcional abre una app de la lista permitida del agente; el dueño
debe autorizar esa capacidad con la política local antes de usarla.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _get(url: str, headers: dict[str, str] | None = None, timeout: int = 5) -> dict:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as reply:
            return json.loads(reply.read(262144))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Respuesta HTTP {exc.code} del servicio local") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Servicio local sin conexión") from exc
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Respuesta local no válida") from exc


def main() -> int:
    cli = argparse.ArgumentParser(description="Prueba segura de SKY API en Windows")
    cli.add_argument("--app", choices=("calculator", "text_editor", "file_manager",
                                        "browser", "word", "excel", "powerpoint"),
                     help="Aplicación real que se probará SOLO junto con --execute")
    cli.add_argument("--execute", action="store_true", help="Autoriza la apertura de la aplicación elegida")
    args = cli.parse_args()
    if args.execute != bool(args.app):
        cli.error("Indicá conjuntamente --app NOMBRE y --execute para probar una app.")
    if platform.system() != "Windows":
        print("Esta verificación está diseñada para ejecutarse en una computadora Windows.")
        return 2

    from neural_core import dispositivos
    from neural_core.sky_voice_actions import local_agent_credentials

    print("SKY API Windows Smoke — sin revelar claves o datos privados")
    print("1. Comprobando agente de escritorio...")
    try:
        agent_url, agent_token = local_agent_credentials()
        status = dispositivos.call_device(agent_url, agent_token, "status", timeout=5)
        if not status.get("ok") or status.get("agent") != "SKY Desktop Agent":
            raise RuntimeError("El puerto no corresponde al agente SKY esperado.")
        print("   Conectado:", status.get("agent"), "versión", status.get("version"))
        print("   Perfil:", status.get("profile"), "Capacidades:", len(status.get("capabilities", [])))
    except Exception as exc:
        print("   FALLÓ:", type(exc).__name__, str(exc))
        print("   Iniciá el agente con: python agente_dispositivo.py")
        return 1

    print("2. Comprobando servicio de API SKY en 127.0.0.1:8765...")
    try:
        from metaverse.api import api_token
        headers = {"X-SKY-KEY": api_token()}
        # Si se configuró MFA, SKY necesita X-SKY-SESSION. El usuario debe
        # probarlo en el HUD, nunca imprimir tokens ni solicitar códigos aquí.
        d = _get("http://127.0.0.1:8765/api/asistente/dispositivo", headers)
        if not d.get("ok"):
            raise RuntimeError("La API no confirmó un agente operativo.")
        print("   API y agente se comunican correctamente.")
    except Exception as exc:
        print("   Pendiente:", type(exc).__name__, str(exc))
        print("   Comprobá que la API esté iniciada y que la sesión MFA se haya autorizado en el HUD.")
        print("   Iniciá la API con: python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765")
        if args.execute:
            print("   No se ejecutará la acción opcional mientras la API no esté disponible.")
        return 1

    print("3. Consultando KPI de acciones...")
    try:
        info = _get("http://127.0.0.1:8765/api/hud/kpis/ejecuciones", headers)
        if info.get("available"):
            print("   Muestra de acciones:", info.get("total_actions"),
                  "| verificadas:", info.get("verified"), "| fallidas:", info.get("failed"))
        else:
            print("   KPI no disponible:", info.get("reason", "sin conexión"))
    except Exception as exc:
        print("   No hay KPIs accesibles:", type(exc).__name__, str(exc))

    if not args.execute:
        print("4. Ejecución de aplicaciones omitida (modo seguro de solo lectura).")
        return 0

    print("4. Abriendo app autorizada en este Windows:", args.app)
    try:
        result = dispositivos.call_device(agent_url, agent_token, "launch_app", {"app": args.app}, timeout=12)
        command_id = result.get("command_id")
        print("   Estado reportado:", result.get("status", "NO REPORTADO"))
        if command_id:
            receipt = dispositivos.verify_device_action(agent_url, agent_token, command_id)
            print("   Recibo de acción:", receipt.get("status"), "| verificada:", receipt.get("verified"))
            if receipt.get("verified"):
                print("   Verificá además visualmente que la aplicación correcta esté abierta.")
                return 0
            print("   No se ha confirmado la apertura real de la aplicación.")
            return 1
        print("   El agente no devolvió un identificador verificable.")
        return 1
    except Exception as exc:
        print("   FALLÓ:", type(exc).__name__, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
