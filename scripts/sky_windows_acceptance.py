"""SKY Windows acceptance — non-invasive local checklist and truthful readiness.

Run in the owner's Windows installation. Never sends tokens, starts a service,
records audio, invokes applications, changes system settings or approves actions.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
from neural_core import sky_verification_lab as lab


def build_report(probe_ollama: bool = False) -> dict:
    runtime = lab.runtime_readiness(probe_ollama)
    from neural_core.sky_train_model import preflight
    from neural_core.sky_runtime_inventory import report as integration_report
    from neural_core.sky_comfyui_local import capabilities as creative_capabilities
    from neural_core.sky_diffusers_local import capabilities as diffusion_capabilities
    root=Path(__file__).resolve().parents[1]
    base=os.getenv("SKY_TRAINING_BASE_MODEL_DIR","") or None
    output=os.getenv("SKY_TRAINING_OUTPUT_DIR","") or None
    lora=preflight(dataset=root/"data/training/sky_seed_v1.jsonl",
                   base_model=base,output=output)
    integrations=integration_report()
    media={"comfyui":creative_capabilities(),
           "diffusers":diffusion_capabilities(),
           "real_image_file_generated":False,
           "real_video_file_rendered":False,
           "real_music_file_verified":False,
           "real_document_file_verified":False}
    four_pillars={
        "voice_windows":{"status":"pending_human_hardware_test",
                         "microphone_verified":False,
                         "native_app_open_verified":False},
        "real_artifacts":{"status":"pending_real_render_and_open_test",
                          "providers":media},
        "integrations":{"status":"code_and_dependency_inventory_only",
                        "inventory":integrations,
                        "external_actions_verified":False},
        "own_lora":{"status":"preflight_only_not_trained",
                    "preflight":lora,"trained_checkpoint_verified":False}
    }
    return {
        "test_location": platform.system(),
        "windows_test_environment": platform.system() == "Windows",
        "component_probe": runtime,
        "four_pillars": four_pillars,
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
