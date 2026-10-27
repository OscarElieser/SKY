"""SKY runtime readiness audit for the owner's Windows installation.

Read-only by default: no microphones started, apps opened, files generated on
disk, calls placed, devices controlled, or AI providers invoked. This extends
the existing integral API probe instead of replacing SKY's own API.

Use: .venv/Scripts/python.exe scripts/sky_runtime_full_audit.py --save
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRIVILEGED_CAPABILITIES = (
    "launch_app", "apps_extra", "files", "windows", "type_text", "tasks"
)
EXPECTED_FILES = {
    "api": "metaverse/api.py",
    "agent": "agente_dispositivo.py",
    "voice": "sky_manos_libres.py",
    "voice_single_instance": "neural_core/sky_voice_single_instance.py",
    "hud": "metaverse/static/hud.js",
    "hud_voice_bridge": "neural_core/sky_hud_intents.py",
    "office": "neural_core/sky_office.py",
    "academic": "neural_core/sky_aula.py",
    "research": "neural_core/sky_scholarly.py",
    "programming": "neural_core/sky_developer_workbench.py",
    "media": "neural_core/sky_media_tools.py",
    "phone": "neural_core/sky_phone.py",
    "security": "neural_core/sky_capacidades.py",
    "workflow": "neural_core/sky_execution_cycle.py",
    "metaverse": "metaverse/engine.py",
    "memory": "neural_core/smart_memory.py",
}


def capabilities(policy: dict[str, Any]) -> dict[str, bool]:
    enabled = set(policy.get("enabled") or [])
    return {name: name in enabled for name in PRIVILEGED_CAPABILITIES}


def classify_endpoint(is_reachable: bool) -> str:
    # An HTTP 200 proves a responding route, not an executed real-life task.
    return "API_RESPONDE_SIN_CERTIFICACION" if is_reachable else "NO_VERIFICADO"


def running_voice_processes() -> dict:
    try:
        import psutil
    except ImportError:
        return {"available": False, "reason": "psutil_no_instalado"}
    found = []
    for proc in psutil.process_iter(attrs=["pid", "ppid", "name", "cmdline"]):
        try:
            info = proc.info
            if str(info.get("name") or "").lower() not in ("python.exe", "pythonw.exe", "python"):
                continue
            cmd = " ".join(str(x) for x in (info.get("cmdline") or []))
            if "sky_manos_libres.py" in cmd.lower():
                found.append({"pid": info["pid"], "parent_pid": info["ppid"]})
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            continue
    return {
        "available": True,
        "processes_matching_voice_command": found,
        "count": len(found),
        "note": "Una lista de PIDs no demuestra cuántos micrófonos están abiertos. Comprobar padre/hijo y candado Vosk.",
    }


def resource_snapshot() -> dict:
    disk = shutil.disk_usage(ROOT)
    result = {
        "disk_free_gb": round(disk.free / 1024**3, 1),
        "disk_free_pct": round(100 * disk.free / disk.total, 1),
    }
    try:
        import psutil
        result.update(
            ram_used_pct=round(psutil.virtual_memory().percent, 1),
            cpu_used_pct=round(psutil.cpu_percent(interval=0.1), 1),
        )
    except ImportError:
        result["ram_used_pct"] = None
        result["cpu_used_pct"] = None
    return result


def local_command_contract() -> dict:
    """Parse requests without asking Ollama or dispatching a Windows command."""
    result = {}
    try:
        from neural_core.sky_asistente_personal import interpretar, reglas
        from neural_core.sky_execution_cycle import is_sequence
        greeting = reglas("hola sky")
        chat = reglas("Abrir panel de conversación.")
        word = interpretar("abri word")
        result = {
            "greeting_fast_rule": isinstance(greeting, dict) and greeting.get("tipo") == "respuesta",
            "hud_chat_intent": (isinstance(chat, dict) and chat.get("tipo") == "accion"
                                and (chat.get("propuesta") or {}).get("params", {}).get("subaction") == "open_chat"),
            "word_launch_intent": isinstance(word, dict) and word.get("action") == "launch_app",
            "word_report_sequence_recognized": is_sequence("abri word y redacta un informe sobre educacion"),
            "real_windows_execution_tested": False,
        }
    except Exception as exc:
        result = {"error_type": type(exc).__name__, "real_windows_execution_tested": False}
    return result


def in_memory_word_document() -> dict:
    """Verify actual DOCX byte generation without creating a personal file."""
    try:
        from neural_core.sky_office import create_document
        item = create_document({
            "kind": "docx", "title": "Prueba de auditoria SKY",
            "content": "Esta prueba valida bytes DOCX de forma local y privada.",
        })
        return {
            "generated_in_memory": len(item.data) > 1500 and item.data.startswith(b"PK"),
            "bytes": len(item.data),
            "saved_in_documents": False,
            "opened_in_word": False,
        }
    except Exception as exc:
        return {"generated_in_memory": False, "error_type": type(exc).__name__,
                "saved_in_documents": False, "opened_in_word": False}


def system_services() -> dict:
    try:
        from iniciar_sky_autonomo import check_system_status
        status = check_system_status()
        agent = status.get("agent") or {}
        api = status.get("api") or {}
        voice = status.get("voice") or {}
        return {
            "api_online": api.get("status") == "online",
            "agent_online": agent.get("status") == "online",
            "device_capabilities_reported": sorted(set(agent.get("capabilities") or [])),
            "voice_mode": str(voice.get("mode") or "desconocido")[:50],
            "voice_session_active": bool(voice.get("active")),
            "voice_active_note": "Una sesión inactiva no implica micrófono apagado.",
        }
    except Exception as exc:
        return {"available": False, "error_type": type(exc).__name__}


def policy_report() -> dict:
    try:
        from neural_core.sky_capacidades import cargar_politica
        policy = cargar_politica()
        result = {
            "profile": str(policy.get("perfil") or "desconocido")[:40],
            "allowed": capabilities(policy),
        }
        result["word_report_permissions_complete"] = (
            result["allowed"]["apps_extra"] and result["allowed"]["files"]
            and result["allowed"]["type_text"]
        )
        result["authorization_note"] = (
            "Los permisos habilitados no eliminan confirmaciones individuales "
            "de escritura ni prueban que Word esté instalado."
        )
        return result
    except Exception as exc:
        return {"available": False, "error_type": type(exc).__name__}


def api_matrix() -> dict:
    try:
        from scripts.sky_integral_operational_check import run
        existing = run()
        # Keep SKY's established routes and confidence limits.
        result = {}
        for name, value in (existing.get("checks") or {}).items():
            result[name] = {
                "status": classify_endpoint(bool(value.get("reachable"))),
                "http_status": value.get("http_status"),
            }
            if name == "telefono":
                result[name]["provider_configured"] = value.get("provider_configured", False)
                result[name]["owner_verified"] = value.get("owner_verified", False)
        return result
    except Exception as exc:
        return {"error_type": type(exc).__name__}


def assess(report: dict) -> list[str]:
    warnings = []
    resources = report["resources"]
    if resources.get("ram_used_pct") is not None and resources["ram_used_pct"] >= 90:
        warnings.append("RAM >= 90 %: evitar más motores y procesos antes de estabilizar.")
    voice = report["voice_processes"]
    if voice.get("count", 0) > 2:
        warnings.append("Varias entradas Vosk: revisar ParentProcessId y posible duplicación.")
    policy = report["device_policy"]
    if policy.get("word_report_permissions_complete") is False:
        warnings.append("Permisos insuficientes para abrir y escribir un informe en Word.")
    if not report["services"].get("agent_online"):
        warnings.append("Agente de Windows sin conexión comprobada.")
    if not report["services"].get("api_online"):
        warnings.append("API principal no aparece en línea.")
    commands = report["command_parser"]
    if commands.get("word_report_sequence_recognized") is False:
        warnings.append("La orden compuesta 'abrí Word y redactá un informe' NO se reconoce como ciclo.")
    return warnings


def run() -> dict:
    report = {
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "scope": "READ_ONLY_REAL_WINDOWS_GATE",
        "module_presence": {key: (ROOT / rel).is_file()
                            for key, rel in EXPECTED_FILES.items()},
        "services": system_services(),
        "resources": resource_snapshot(),
        "voice_processes": running_voice_processes(),
        "device_policy": policy_report(),
        "command_parser": local_command_contract(),
        "office_docx": in_memory_word_document(),
        "api_capabilities": api_matrix(),
    }
    report["warnings"] = assess(report)
    report["ready_for_main"] = False
    report["certified"] = False
    report["required_physical_tests"] = [
        "Vosk reconoce voz real sin palabra clave y pausas",
        "HUD abre chat flotante visible y confirma apertura",
        "Word abre y se comprueba una ventana real",
        "Se guarda y abre un DOCX real con consentimiento",
        "Se verifica una acción autorizada, la denegación y la parada de emergencia",
        "Se prueban voz, docencia, investigación, música y continuidad tras reinicio",
    ]
    report["privacy_note"] = (
        "No se guardan tokens, PIN, comandos de voz, historiales privados, nombres "
        "de archivos personales, conversaciones ni números telefónicos."
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="SKY — auditoría operativa, sin cambios")
    parser.add_argument("--save", action="store_true", help="Guardar diagnóstico privado JSON")
    args = parser.parse_args()
    report = run()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.save:
        output = ROOT / "local_data" / "diagnosticos" / "sky_runtime_full_audit.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                          encoding="utf-8")
        print("\nInforme local:", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
