"""Safe post-install acceptance measurements for SKY PR #52 on the owner's Windows PC.

No microphone recording, Windows app launch, permission changes or secret output.
The chat stream test writes three ordinary 'hola sky' turns into SKY history.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8765"
PATHS = {
    "docs": "/docs",
    "health": "/api/health",
    "hud_js": "/static/hud.js",
}


def summary(samples):
    if not samples:
        return {"count": 0, "p50_ms": None, "p95_ms": None}
    vals = sorted(samples)
    return {
        "count": len(vals),
        "p50_ms": round(statistics.median(vals), 1),
        "p95_ms": round(vals[max(0, int((len(vals) - 1) * 0.95 + 0.5))], 1),
        "max_ms": round(vals[-1], 1),
    }


def ping(session, name, path, iterations=10):
    results, errors = [], []
    for attempt in range(iterations + 1):
        t0 = time.perf_counter()
        try:
            resp = session.get(BASE + path, timeout=(4, 20))
            elapsed = 1000 * (time.perf_counter() - t0)
            valid = resp.status_code == 200
            if name == "health":
                valid = valid and resp.json().get("status") == "ok"
            if name == "hud_js":
                valid = valid and len(resp.content) > 1000
            if not valid:
                errors.append(f"{name}: HTTP {resp.status_code} or invalid payload")
            elif attempt:
                results.append(elapsed)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}")
    return {"latency": summary(results), "errors": errors}


def greeting(session, token, attempts=3):
    latencies, headers, first, errors = [], [], [], []
    for i in range(attempts):
        started = time.perf_counter()
        try:
            with session.post(
                BASE + "/api/asistente/stream",
                headers={"X-SKY-KEY": token},
                json={"texto": "hola sky", "modo": "voz", "historial": [],
                      "dispositivo": "local"},
                stream=True, timeout=(5, 30),
            ) as response:
                header_ms = (time.perf_counter() - started) * 1000
                if response.status_code != 200:
                    errors.append(f"stream HTTP {response.status_code}")
                    continue
                got_final, first_seen = False, None
                for line in response.iter_lines():
                    if not line:
                        continue
                    if first_seen is None:
                        first_seen = (time.perf_counter() - started) * 1000
                    obj = json.loads(line)
                    final = obj.get("final") or {}
                    if final:
                        got_final = (
                            final.get("tipo") == "respuesta"
                            and "te escucho" in final.get("mensaje", "").lower()
                        )
                if not got_final:
                    errors.append("El stream terminó sin saludo final verificable")
                else:
                    headers.append(header_ms)
                    first.append(first_seen)
                    latencies.append((time.perf_counter() - started) * 1000)
        except Exception as exc:
            errors.append(f"stream: {type(exc).__name__}")
    return {"latency": summary(latencies), "headers": summary(headers),
            "first_event": summary(first), "errors": errors,
            "note": "Cada intento crea un turno de prueba en el historial SKY."}


def local_status():
    checks = {}
    expected = (
        ("metaverse/api.py", "sky_http_metrics_queue"),
        ("sky_manos_libres.py", "SKY_VOICE_ALWAYS_LISTEN"),
        ("metaverse/static/hud.js", "CONV + listening"),
        ("neural_core/sky_http_metrics_queue.py", "def enqueue("),
    )
    for rel, marker in expected:
        file = ROOT / rel
        checks[rel] = file.exists() and marker in file.read_text(
            encoding="utf-8", errors="replace")
    for rel in ("metaverse/api.py", "sky_manos_libres.py",
                "neural_core/sky_http_metrics_queue.py"):
        file = ROOT / rel
        if file.exists():
            try:
                compile(file.read_bytes(), str(file), "exec")
                checks[rel + ":syntax"] = True
            except SyntaxError:
                checks[rel + ":syntax"] = False
    if shutil.which("node"):
        try:
            r = subprocess.run(["node", "--check", str(ROOT / "metaverse/static/hud.js")],
                               capture_output=True, timeout=15)
            checks["hud:javascript_syntax"] = r.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            checks["hud:javascript_syntax"] = False
    return checks


def resource_status():
    drive = shutil.disk_usage(ROOT)
    result = {
        "os": platform.platform(), "python": platform.python_version(),
        "disk_total_gb": round(drive.total / (1024 ** 3), 1),
        "disk_free_gb": round(drive.free / (1024 ** 3), 1),
        "disk_free_pct": round(drive.free / drive.total * 100, 1),
    }
    try:
        import psutil
        result.update(cpu_pct=psutil.cpu_percent(interval=0.5),
                      ram_used_pct=psutil.virtual_memory().percent)
    except ImportError:
        pass
    return result


def main():
    parser = argparse.ArgumentParser(description="Pruebas de aceptación SKY #52")
    parser.add_argument("--output", help="Ruta JSON para guardar el informe (opcional).")
    args = parser.parse_args()
    if platform.system() != "Windows":
        print("ADVERTENCIA: la validación física debe ejecutarse en Windows.", file=sys.stderr)
    os.chdir(ROOT)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "revision": "SKY PR #52",
        "resources": resource_status(),
        "patch_checks": local_status(),
        "requests": {},
        "manual_tests": {
            "microphone_and_stt": "PENDIENTE",
            "natural_wordless_audio": "PENDIENTE",
            "pause_and_resume": "PENDIENTE",
            "word_launch_verified": "PENDIENTE",
            "hud_chat_panel_verified": "PENDIENTE",
            "permissions_and_emergency_stop": "PENDIENTE",
        },
    }
    try:
        import requests
        from metaverse.api import api_token
        with requests.Session() as session:
            session.trust_env = False
            for label, path in PATHS.items():
                report["requests"][label] = ping(session, label, path)
            report["requests"]["stream_greeting"] = greeting(session, api_token())
    except Exception as exc:
        report["fatal_error"] = f"{type(exc).__name__}: {str(exc)[:140]}"
    api_health = report["requests"].get("health", {})
    static = report["requests"].get("hud_js", {})
    greeting_result = report["requests"].get("stream_greeting", {})
    def good(item, p95_limit):
        data = item.get("latency", {})
        return not item.get("errors") and data.get("count", 0) >= 3 and (
            data.get("p95_ms") is not None and data["p95_ms"] < p95_limit)
    report["automated_latency_gate"] = {
        "health_p95_under_1000ms": good(api_health, 1000),
        "hud_p95_under_500ms": good(static, 500),
        "greeting_p95_under_2000ms": good(greeting_result, 2000),
    }
    report["ready_for_main"] = False
    report["note"] = ("El equipo aún requiere comprobaciones humanas de micrófono, "
                      "acciones de Windows, seguridad y recuperación. "
                      "No se certifica ni fusiona automáticamente.")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.output:
        target = Path(args.output).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                          encoding="utf-8")
        print("Informe:", target)
    return 1 if ("fatal_error" in report or
                 not all(report["patch_checks"].values()) or
                 not all(report["automated_latency_gate"].values())) else 0


if __name__ == "__main__":
    raise SystemExit(main())
