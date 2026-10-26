"""Diagnostic read-only: distinguish API restarts, Ollama availability and historical KPIs.

No startup, shutdown, external requests, file edits, environment values or
tokens are exposed. Works with the existing owner API and metrics storage.
Run from the SKY root using the virtualenv Python.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _local_json(url: str, timeout: float = 1.5) -> tuple[int | None, dict]:
    try:
        req = Request(url, headers={"Accept": "application/json",
                                    "User-Agent": "SKY-Local-Diagnostic"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read(350_000)
            obj = json.loads(raw)
            return resp.status, obj if isinstance(obj, dict) else {}
    except HTTPError as exc:
        return exc.code, {}
    except (OSError, URLError, TimeoutError, ValueError):
        return None, {}


def _ports_and_processes() -> dict:
    from iniciar_sky_autonomo import PORTS
    results = {}
    try:
        import psutil
        listeners = {int(c.laddr.port): c.pid for c in psutil.net_connections(kind="tcp")
                     if c.status == "LISTEN" and c.laddr
                     and c.laddr.ip in ("127.0.0.1", "::1", "0.0.0.0", "::")}
    except Exception:
        listeners = {}
    for name, port in PORTS.items():
        pid = listeners.get(port)
        row = {"port": port, "listening_pid": pid}
        if pid:
            try:
                import psutil
                proc = psutil.Process(pid)
                row["program"] = Path(proc.exe()).name
                row["parent_pid"] = proc.ppid()
                # Never output a full command line: it can contain secrets.
                args = " ".join(proc.cmdline()).lower()
                row["is_uvicorn"] = ("uvicorn" in args)
            except Exception:
                pass
        results[name] = row
    return results


def _history() -> dict:
    try:
        from neural_core.sky_metricas import _ruta_db
        file = _ruta_db()
        if not file.is_file():
            return {"available": False, "reason": "sin_base_de_metricas"}
        uri = "file:" + quote(file.resolve().as_posix(), safe="/:") + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2) as conn:
            rows = conn.execute(
                "SELECT ts, detalle FROM eventos "
                "WHERE tipo='servicio' AND nombre='reinicio' "
                "ORDER BY id DESC LIMIT 10"
            ).fetchall()
            ai = conn.execute(
                "SELECT ts, ms, ok, origen FROM eventos "
                "WHERE tipo='turno' AND origen='cerebro' AND ms IS NOT NULL "
                "ORDER BY id DESC LIMIT 20"
            ).fetchall()
        return {
            "last_restarts": [
                {"at": datetime.fromtimestamp(float(ts)).isoformat(timespec="seconds"),
                 "detail": str(detail or "")[:110]} for ts, detail in rows],
            "last_cerebro_turns": [
                {"at": datetime.fromtimestamp(float(ts)).isoformat(timespec="seconds"),
                 "milliseconds": int(ms), "ok": bool(ok)} for ts, ms, ok, origin in ai],
            "note": "Historial local; no prueba que el proceso siga fallando ahora.",
        }
    except (sqlite3.Error, OSError, ValueError, ImportError) as exc:
        return {"available": False, "error_type": type(exc).__name__}


def _ollama() -> dict:
    root = "http://127.0.0.1:11434"
    code, tags = _local_json(root + "/api/tags")
    pscode, processes = _local_json(root + "/api/ps")
    installed = [str(p.get("name") or "")[:80] for p in
                 (tags.get("models") or []) if isinstance(p, dict)]
    loaded = [str(p.get("name") or "")[:80] for p in
              (processes.get("models") or []) if isinstance(p, dict)]
    model = os.getenv("OLLAMA_MODEL", "").strip()
    # Read only the non-sensitive model name from SKY's .env.
    if not model:
        try:
            from dotenv import dotenv_values
            model = str(dotenv_values(ROOT / ".env").get("OLLAMA_MODEL") or "").strip()
        except (ImportError, OSError):
            pass
    return {"service_responding": code == 200,
            "installed_models": installed[:20],
            "models_loaded_now": loaded[:10],
            "configured_model": model[:80] if model else "predeterminado de SKY",
            "note": "Sin modelos cargados no equivale a fallo ni implica que la latencia histórica sea actual."}


def main() -> int:
    api, payload = _local_json("http://127.0.0.1:8765/api/health")
    report = {
        "scope": "only_local_read_only",
        "api": {"http_status": api,
                "sky_service": "SKY" in str(payload.get("service", ""))},
        "ports": _ports_and_processes(),
        "metrics": _history(),
        "ollama": _ollama(),
        "next_step": (
            "Consultar los errores de arranque en la consola original del supervisor "
            "si siguen ocurriendo: el codigo 3 no identifica por sí solo la causa."
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
