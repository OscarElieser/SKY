#!/usr/bin/env python3
"""Operator-run acceptance test: real SKY API -> local Ollama, never third-party.

Run on the owner's dedicated inference server; safe to run without installed
Ollama (exits nonzero with a truthful reason). No remote data or secrets sent.
"""
from __future__ import annotations

import json
import sys
from neural_core import sky_inference_gateway as gateway


def main() -> int:
    try:
        ready = gateway.readiness()
        if not ready["local_ollama_ready"]:
            print(json.dumps({"ok": False, "phase": "model_ready",
                              "reason": "Ollama model absent or worker unreachable",
                              "ready_workers": ready["ready_workers"]}))
            return 2
        result = gateway.generate([
            {"role": "system", "content": "Eres SKY IA. Responde en español."},
            {"role": "user", "content":
                "Indica en una oración qué significa una hipótesis investigativa."}
        ], max_output_tokens=180)
        print(json.dumps({"ok": bool(result["respuesta"].strip()),
                          "phase": "real_generation",
                          "provider": result["proveedor"],
                          "cloud": result["nube"],
                          "operation_id": result["operacion"],
                          "metrics": result["metricas"],
                          "characters": len(result["respuesta"]),
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
