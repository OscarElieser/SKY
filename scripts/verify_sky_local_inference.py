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
                        help="Comprobar consulta académica >16K y respuesta extensa con tokens reales")
    parser.add_argument("--maximal-academic", action="store_true",
                        help="Validar ~42K caracteres y hasta 6144 tokens con Ollama real y 64K de contexto")
    args = parser.parse_args()
    if args.long_academic and args.maximal_academic:
        parser.error("Seleccioná solo una longitud de prueba")
    academic = (
        "Proyecto sobre inteligencia artificial y dimensión socioemocional "
        "en educación técnica y universitaria. "
    )
    prompt = (
        academic * (400 if args.maximal_academic else 220) + (
            "Redacta un análisis académico estructurado con problema, objetivos, "
            "método, variables, limitaciones, implicaciones y conclusiones. "
            "No inventes referencias ni resultados empíricos; distinguí hipótesis "
            "de evidencias y utilizá ejemplos educativos concretos."
        )
        if (args.long_academic or args.maximal_academic) else
        "Indica en una oración qué significa una hipótesis investigativa."
    )
    if args.maximal_academic:
        assert 32_000 < len(prompt) <= 48_000
    elif args.long_academic:
        assert 16_000 < len(prompt) <= 32_000
    else:
        assert len(prompt) < 4000
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
        ], max_output_tokens=(6144 if args.maximal_academic else
                              4096 if args.long_academic else 180))
        output_chars = len(result["respuesta"])
        generated = result["metricas"]["tokens_salida"]
        passed = bool(result["respuesta"].strip()) and (
            (not args.long_academic and not args.maximal_academic) or
            (output_chars >= (3500 if args.maximal_academic else 2000) and
             generated >= (1000 if args.maximal_academic else 500) and
             result["metricas"]["tokens_entrada"] > 0 and
             not result.get("respuesta_incompleta", False))
        )
        print(json.dumps({"ok": passed,
                          "phase": "real_generation",
                          "provider": result["proveedor"],
                          "cloud": result["nube"],
                          "operation_id": result["operacion"],
                          "metrics": result["metricas"],
                          "characters": output_chars,
                          "complete": not result.get("respuesta_incompleta", False),
                          "input_characters": len(prompt),
                          "long_academic": args.long_academic,
                          "maximal_academic": args.maximal_academic,
                          "note": "Prueba de inferencia real; la calidad académica requiere revisión humana"},
                         ensure_ascii=False))
        return 0 if passed else 4
    except (gateway.InferenceBusy, gateway.InferenceUnavailable,
            ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "phase": "real_generation",
                          "reason": type(exc).__name__,
                          "note": "No se pudo verificar el motor local"}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
