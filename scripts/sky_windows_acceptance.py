"""SKY Windows acceptance — non-invasive local checklist and truthful readiness.

Run in the owner's Windows installation. Never sends tokens, starts a service,
records audio, invokes applications, changes system settings or approves actions.
"""
from __future__ import annotations

import argparse
import json
import platform
from neural_core import sky_verification_lab as lab


def build_report(probe_ollama: bool = False) -> dict:
    runtime = lab.runtime_readiness(probe_ollama)
    return {
        "test_location": platform.system(),
        "windows_test_environment": platform.system() == "Windows",
        "component_probe": runtime,
        "live_microphone_stt_verified": False,
        "live_piper_tts_verified": False,
        "windows_agent_action_verified": False,
        "action_approval_chain_verified": False,
        "human_steps": [
            "Iniciar SKY_INICIAR.bat opción 0 y luego opción 7 para diagnóstico.",
            "Probar una orden hablada, comprobar transcripción y responder sin fallos.",
            "Probar salida de voz Piper en altavoces y función de interrupción.",
            "Probar una aplicación permitida con agente Windows y comprobar la ventana real.",
            "Intentar una acción de mayor riesgo y confirmar que exige aprobación explícita.",
            "Consultar KPIs reales y guardar identificadores de recibo sin datos privados.",
        ],
        "overall_real_device_validation": "pending_manual_execution",
        "note": "Este script solo obtiene señales locales; no puede certificarse voz o acciones sin pruebas humanas.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico no invasivo de SKY en Windows")
    parser.add_argument("--probe-ollama", action="store_true",
                        help="Consultar únicamente Ollama en http://127.0.0.1:11434")
    args = parser.parse_args(argv)
    print(json.dumps(build_report(args.probe_ollama), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
