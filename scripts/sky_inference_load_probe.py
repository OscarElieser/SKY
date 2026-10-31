#!/usr/bin/env python3
"""Bounded, owner-run load probe for a locally hosted SKY Ollama model.

Not a commercial scale benchmark. No third-party API requests or stored prompts.
Requires a real model on loopback and intentionally limits test pressure.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neural_core import sky_inference_gateway as gateway


def _single(index: int) -> dict:
    started = time.monotonic()
    try:
        response = gateway.generate(
            [{"role": "system", "content": "Eres SKY IA, responde brevemente."},
             {"role": "user", "content":
              "Define claramente una variable de investigación educativa."}],
            max_output_tokens=120)
        return {"ok": bool(response["respuesta"].strip()),
                "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                "output_tokens": response["metricas"]["tokens_salida"]}
    except (gateway.InferenceBusy, gateway.InferenceUnavailable, ValueError):
        return {"ok": False, "elapsed_ms": round(
            (time.monotonic() - started) * 1000, 1),
                "output_tokens": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=6)
    parser.add_argument("--parallel", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.requests <= 30 or not 1 <= args.parallel <= 4:
        parser.error("Máximo 30 solicitudes y 4 paralelas por prueba")
    if not gateway.readiness()["local_ollama_ready"]:
        print(json.dumps({"ok": False, "reason": "Modelo local no disponible"}))
        return 2
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        jobs = [pool.submit(_single, i) for i in range(args.requests)]
        results = [future.result() for future in as_completed(jobs)]
    elapsed = max(0.001, time.monotonic() - start)
    samples = sorted(x["elapsed_ms"] for x in results if x["ok"])
    p95 = samples[max(0, (95 * len(samples) + 99) // 100 - 1)] if samples else None
    success = sum(1 for item in results if item["ok"])
    print(json.dumps({
        "requests": args.requests, "parallel": args.parallel,
        "completed": success, "failed_or_rejected": args.requests - success,
        "rps_observed": round(args.requests / elapsed, 2),
        "p95_ms_success": p95,
        "mean_ms_success": round(statistics.mean(samples), 1) if samples else None,
        "output_tokens": sum(x["output_tokens"] for x in results),
        "scope": "single local process, not cluster benchmark",
    }, ensure_ascii=False))
    return 0 if success == args.requests else 1


if __name__ == "__main__":
    sys.exit(main())
