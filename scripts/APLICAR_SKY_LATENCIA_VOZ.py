"""Aplica solo la correccion PR #52 a una instalacion SKY sin .git.

Compara cambios sin sobreescribir otros, conserva respaldos y no toca secretos.
La rama PR debe incluir el commit de funciones y pruebas previamente revisadas.
Ejecutar desde la raiz de SKY; requiere Git en PATH.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "OscarElieser/SKY"
PR = 52
REVIEWED_BASE = "909228afcc8aa9ce9624744dacd1e11d042d7492"
TARGETS = (
    "metaverse/api.py",
    "metaverse/static/hud.js",
    "neural_core/sky_http_metrics_queue.py",
    "sky_manos_libres.py",
    "tests/test_sky_latency_and_wordless_voice.py",
)
API = f"https://api.github.com/repos/{REPO}"


def get(url: str, max_bytes: int) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "SKY-Owner-Local-Patch/1.1",
        "Accept": "application/vnd.github+json" if url.startswith(API) else "text/plain",
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError("Descarga supera limite de tamano")
    return data


def git_apply(root: Path, patch: bytes, check: bool):
    cmd = ["git", "apply"]
    if check:
        cmd.append("--check")
    cmd.extend(f"--include={path}" for path in TARGETS)
    cmd.append("-")
    return subprocess.run(
        cmd, cwd=root, input=patch, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=30, check=False,
    )


def main():
    parser = argparse.ArgumentParser(description="Actualizacion reversible SKY PR #52")
    parser.add_argument("--aplicar", action="store_true")
    options = parser.parse_args()
    root = Path.cwd()
    if not (root / "SKY_INICIAR.bat").is_file() or not (root / "metaverse/api.py").is_file():
        root = Path(__file__).resolve().parent
        if root.name == "scripts":
            root = root.parent
    if not (root / "SKY_INICIAR.bat").is_file() or not (root / "metaverse/api.py").is_file():
        print("ERROR: ejecuta desde la carpeta principal de SKY.")
        return 2
    if not shutil.which("git"):
        print("ERROR: instala Git para aplicar los cambios sin reemplazar archivos completos.")
        return 2

    try:
        info = json.loads(get(f"{API}/pulls/{PR}", 100_000))
        if not (info.get("state") == "open" or info.get("merged") is True):
            raise RuntimeError("PR #52 no esta disponible o fue cerrado sin integrar.")
        sha = info.get("head", {}).get("sha", "")
        if not sha:
            raise RuntimeError("GitHub no devolvio una revision de PR.")
        if sha != REVIEWED_BASE:
            diff = json.loads(get(f"{API}/compare/{REVIEWED_BASE}...{sha}", 600_000))
            if diff.get("status") not in ("ahead", "identical") or diff.get("base_commit", {}).get("sha") != REVIEWED_BASE:
                raise RuntimeError("La rama de GitHub no contiene la revision revisada.")
        patch = get(f"https://github.com/{REPO}/pull/{PR}.diff", 850_000)
        if not patch.startswith((b"From ", b"diff --git ")):
            raise RuntimeError("GitHub no entrego un parche reconocible.")
        trial = git_apply(root, patch, check=True)
        if trial.returncode != 0:
            print("El parche NO coincide con los archivos locales. No se realizaron cambios.")
            print(trial.stderr.decode("utf-8", "replace")[:1500])
            return 1
        print("COMPATIBLE: los cambios se pueden aplicar sin reemplazar los archivos.")
        if not options.aplicar:
            print("Para instalar, ejecuta nuevamente con --aplicar.")
            return 0

        folder = root / "local_data" / "respaldos_sky" / ("pr52_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        existed = {rel: (root / rel).is_file() for rel in TARGETS}
        folder.mkdir(parents=True, exist_ok=False)
        for rel in TARGETS:
            if existed[rel]:
                copy = folder / rel
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / rel, copy)
        (folder / "cambios_pr52.diff").write_bytes(patch)
        applied = git_apply(root, patch, check=False)
        if applied.returncode != 0:
            # A partially applied patch must be reverted without discarding edits.
            for rel in TARGETS:
                destination = root / rel
                if existed[rel]:
                    shutil.copy2(folder / rel, destination)
                elif destination.exists():
                    destination.unlink()
            raise RuntimeError("No se aplico por completo; archivos restaurados: " +
                               applied.stderr.decode("utf-8", "replace")[:500])
        try:
            subprocess.run([
                sys.executable, "-m", "py_compile",
                str(root / "metaverse/api.py"),
                str(root / "sky_manos_libres.py"),
                str(root / "neural_core/sky_http_metrics_queue.py"),
            ], cwd=root, timeout=30, check=True)
            if shutil.which("node"):
                subprocess.run(["node", "--check", "metaverse/static/hud.js"],
                               cwd=root, timeout=20, check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            for rel in TARGETS:
                destination = root / rel
                if existed[rel]:
                    shutil.copy2(folder / rel, destination)
                elif destination.exists():
                    destination.unlink()
            raise RuntimeError("Sintaxis no valida; restaurado desde respaldo.") from exc

        print("INSTALADO: cambios de latencia, Vosk y HUD aplicados.")
        print("Respaldo:", folder)
        print("No se modificaron .env, datos, modelos ni permisos.")
        return 0
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, subprocess.SubprocessError) as exc:
        print("ERROR:", str(exc)[:1200])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
