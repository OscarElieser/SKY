"""Safe three-way reconciliation of SKY PR #52 with customized Windows files.

Read-only by default. Works in a SKY folder without .git (requires Git CLI).
Never changes .env, databases, devices, models, or personal data.
If ANY modified file conflicts, nothing is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

REPO = "OscarElieser/SKY"
BASE = "949acd93e8c8da636bbcd64f30ddc0108c58dc16"
TARGET = "67d4974788827be14d3db850ffe74cba1f558e30"
EDITED = (
    "metaverse/api.py",
    "metaverse/static/hud.js",
    "sky_manos_libres.py",
)
ADDED = (
    "neural_core/sky_http_metrics_queue.py",
    "tests/test_sky_latency_and_wordless_voice.py",
)


def root_dir() -> Path:
    here = Path.cwd().resolve()
    if (here / "SKY_INICIAR.bat").is_file():
        return here
    here = Path(__file__).resolve().parent
    if here.name.lower() == "scripts":
        here = here.parent
    if not (here / "SKY_INICIAR.bat").is_file():
        raise RuntimeError("Ejecuta este script desde la carpeta principal de SKY.")
    return here


def fetch(ref: str, path: str) -> bytes:
    url = "https://raw.githubusercontent.com/{}/{}/{}".format(
        REPO, ref, urllib.parse.quote(path, safe="/"))
    req = urllib.request.Request(url, headers={
        "User-Agent": "SKY-PR52-Reconcile/1.0",
        "Accept": "text/plain",
    })
    with urllib.request.urlopen(req, timeout=30) as stream:
        blob = stream.read(1_000_001)
    if len(blob) > 1_000_000 or not blob:
        raise RuntimeError("Descarga vacia o demasiado grande: " + path)
    return blob


def normalized(blob: bytes) -> bytes:
    return blob.replace(b"\r\n", b"\n")


def three_way(local: bytes, base: bytes, desired: bytes, workdir: Path):
    # git merge-file is a three-way content merge, *not* a git checkout.
    # A nonzero exit code with conflict markers is REFUSED (never installed).
    workdir.mkdir(exist_ok=True, parents=True)
    files = [workdir / ("local_" + str(len(local))),
             workdir / ("base_" + str(len(base))),
             workdir / ("target_" + str(len(desired)))]
    for destination, contents in zip(files, (local, base, desired)):
        destination.write_bytes(normalized(contents))
    proc = subprocess.run(
        ["git", "merge-file", "-p", "--diff3",
         "-L", "SKY_LOCAL", "-L", "SKY_BASE", "-L", "SKY_PR52",
         *[str(p) for p in files]],
        capture_output=True, timeout=20, check=False,
    )
    if proc.returncode != 0:
        return None, (proc.stderr.decode("utf-8", "replace")[:150] or
                      "Cambios en las mismas lineas; requiere revision manual.")
    return proc.stdout, ""


def make_plan(root: Path, temp: Path):
    states, updates, issues = [], {}, []
    for rel in EDITED + ADDED:
        local_path = root / rel
        local = local_path.read_bytes() if local_path.is_file() else None
        desired = normalized(fetch(TARGET, rel))
        if local is not None and normalized(local) == desired:
            states.append((rel, "YA INSTALADO"))
            continue
        if rel in ADDED:
            if local is not None:
                states.append((rel, "DISTINTO; REVISION MANUAL"))
                issues.append(rel + ": existe, pero difiere del archivo de la PR. No sobreescribir.")
            else:
                states.append((rel, "AGREGAR NUEVO"))
                updates[rel] = desired
            continue
        if local is None:
            states.append((rel, "FALTA ARCHIVO BASE"))
            issues.append(rel + ": archivo original ausente")
            continue
        base = normalized(fetch(BASE, rel))
        if normalized(local) == base:
            states.append((rel, "ACTUALIZACION EXACTA"))
            updates[rel] = desired
            continue
        merged, failure = three_way(local, base, desired, temp / rel.replace("/", "_"))
        if merged is None:
            states.append((rel, "CONFLICTO"))
            issues.append(rel + ": " + failure)
        elif normalized(local) == merged:
            states.append((rel, "YA INTEGRADO CON CAMBIOS LOCALES"))
        else:
            states.append((rel, "FUSION LIMPIA, CONSERVA CAMBIOS"))
            # Preserve CRLF on existing Windows files when appropriate.
            if b"\r\n" in local:
                merged = merged.replace(b"\n", b"\r\n")
            updates[rel] = merged
    return states, updates, issues


def validate(root: Path, updates: dict[str, bytes]) -> list[str]:
    errors = []
    for rel, blob in updates.items():
        if rel.endswith(".py"):
            try:
                compile(blob, str(root / rel), "exec")
            except (SyntaxError, UnicodeError) as error:
                errors.append(rel + ": " + str(error)[:140])
        elif rel.endswith(".js") and shutil.which("node"):
            with tempfile.TemporaryDirectory(prefix="sky_node_") as td:
                jsfile = Path(td) / "hud.js"
                jsfile.write_bytes(blob)
                proc = subprocess.run(["node", "--check", str(jsfile)],
                                      capture_output=True, timeout=20)
                if proc.returncode:
                    errors.append(rel + ": " +
                                  proc.stderr.decode("utf-8", "replace")[:160])
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="SKY PR52: diagnostico y fusion conservadora")
    ap.add_argument("--aplicar", action="store_true",
                    help="Aplicar cambios compatibles con respaldo automatico")
    args = ap.parse_args()
    try:
        root = root_dir()
        if not shutil.which("git"):
            raise RuntimeError("Git no esta disponible en PATH.")
        with tempfile.TemporaryDirectory(prefix="sky_pr52_merge_") as td:
            states, updates, issues = make_plan(root, Path(td))
        print("SKY PR #52: revision local (sin reemplazar el proyecto)")
        for rel, state in states:
            print(" - {}: {}".format(rel, state))
        errors = validate(root, updates)
        if errors:
            issues.extend(errors)
        if issues:
            print("\nNO ES SEGURO INSTALAR TODAVIA:")
            for problem in issues:
                print(" *", problem)
            print("No se modifico ningun archivo.")
            return 2
        print("\nCambios compatibles:", len(updates))
        if not args.aplicar:
            print("SOLO COMPROBACION: sin cambios.")
            print("Para aplicar, ejecuta nuevamente con --aplicar.")
            return 0
        if not updates:
            print("NADA QUE APLICAR: esta revision ya esta presente.")
            return 0
        backup = (root / "local_data" / "respaldos_sky" /
                  ("pr52_conciliado_" + datetime.now().strftime("%Y%m%d_%H%M%S")))
        if backup.exists():
            raise RuntimeError("Ya existe un respaldo con el mismo nombre.")
        backup.mkdir(parents=True)
        originals = {}
        for rel in updates:
            destination = root / rel
            originals[rel] = destination.read_bytes() if destination.is_file() else None
            if originals[rel] is not None:
                dest_backup = backup / rel
                dest_backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, dest_backup)
        try:
            for rel, blob in updates.items():
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                temp_file = dest.with_name(dest.name + ".sky_pr52_temp")
                temp_file.write_bytes(blob)
                os.replace(temp_file, dest)
        except Exception:
            for rel, previous in originals.items():
                dest = root / rel
                if previous is None:
                    dest.unlink(missing_ok=True)
                else:
                    dest.write_bytes(previous)
            raise RuntimeError("Error de escritura; archivos restaurados.")
        print("APLICADO: {} archivos. Respaldo: {}".format(len(updates), backup))
        print("Tus datos, .env y permisos no se modificaron.")
        print("Reinicia SKY y ejecuta la prueba de aceptacion.")
        return 0
    except (RuntimeError, OSError, urllib.error.URLError,
            subprocess.SubprocessError) as err:
        print("ERROR:", str(err)[:500])
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
