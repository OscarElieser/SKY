#!/usr/bin/env python3
"""Operator-run acceptance test: real SKY API -> local Ollama, never third-party.

Run on the owner's dedicated inference server; safe to run without installed
Ollama (exits nonzero with a truthful reason). No remote data or secrets sent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Enable running this script from the repository root without pip-installing SKY.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neural_core import sky_inference_gateway as gateway


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--long-academic", action="store_true",
                        help="Enviar consulta académica >4K completa al modelo local")
    args = parser.parse_args()
    academic = (
        "Proyecto sobre inteligencia artificial y dimensión socioemocional "
        "en educación técnica y universitaria. "
    )
    prompt = (
        academic * 110 + "Explica el planteamiento de un problema de investigación."
        if args.long_academic else
        "Indica en una oración qué significa una hipótesis investigativa."
    )
    assert len(prompt) <= 16000
    try:
        ready = gateway.readiness()
        if not ready["local_ollama_ready"]:
            print(json.dumps({"ok": False, "phase": "model_ready",
                              "reason": "Ollama model absent or worker unreachable",
                              "ready_workers": ready["ready_workers"]}))
            return 2
        result = gateway.generate([
            {"role": "system", "content": "Eres SKY IA. Responde en español."},
            {"role": "user", "content": prompt}
        ], max_output_tokens=320 if args.long_academic else 180)
        print(json.dumps({"ok": bool(result["respuesta"].strip()),
                          "phase": "real_generation",
                          "provider": result["proveedor"],
                          "cloud": result["nube"],
                          "operation_id": result["operacion"],
                          "metrics": result["metricas"],
                          "characters": len(result["respuesta"]),
                          "input_characters": len(prompt),
                          "long_academic": args.long_academic,
                          "note": "Respuesta de modelo local generada; calidad por evaluar"},
                         ensure_ascii=False))
        return 0
    except (gateway.InferenceBusy, gateway.InferenceUnavailable,
            ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "phase": "real_generation",
                          "reason": type(exc).__name__,
                          "note": "No se pudo verificar el motor local"}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
