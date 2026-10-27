"""Apply only the SKY PR52 single-microphone service fix to Windows SKY.

The owner already has the first PR52 latency/wordless-voice version. This
script calculates a narrow three-way merge against that known baseline.
Read-only by default, reject all conflicts, and make backups before applying.
No .git folder is needed. Git CLI is required.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

BASE = "d8183bdf9d09b6cbe1e602b5bcac4dad2edfd82b"
TARGET = "c06c3dec87549cdfcff2112d0c9c6158727a0d8d"
REPO = "OscarElieser/SKY"
EDITED = (
    "sky_manos_libres.py",
    "iniciar_sky_autonomo.py",
)
NEW = (
    "neural_core/sky_voice_single_instance.py",
    "tests/test_sky_voice_single_instance.py",
)


def project_dir() -> Path:
    root = Path.cwd().resolve()
    if (root / "SKY_INICIAR.bat").is_file():
        return root
    root = Path(__file__).resolve().parent
    if root.name.lower() == "scripts":
        root = root.parent
    if not (root / "SKY_INICIAR.bat").is_file():
        raise RuntimeError("Ejecuta esto desde la carpeta principal de SKY.")
    return root


def remote(ref: str, rel: str) -> bytes:
    url = "https://raw.githubusercontent.com/{}/{}/{}".format(
        REPO, ref, urllib.parse.quote(rel, safe="/"))
    request = urllib.request.Request(url, headers={
        "User-Agent": "SKY-ChatPanel-Fix/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(1_000_001)
    if not data or len(data) > 1_000_000:
        raise RuntimeError("Archivo remoto vacio o demasiado grande: " + rel)
    return data


def normalized(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")


def merged_three_way(local: bytes, base: bytes, updated: bytes, root: Path):
    files = [root / "local.txt", root / "base.txt", root / "desired.txt"]
    root.mkdir(exist_ok=True, parents=True)
    for filename, data in zip(files, (local, base, updated)):
        filename.write_bytes(normalized(data))
    merged = subprocess.run(
        ["git", "merge-file", "-p", "--diff3",
         "-L", "LOCAL", "-L", "BASE", "-L", "SKY_FIX",
         *(str(f) for f in files)],
        capture_output=True, timeout=25, check=False)
    if merged.returncode:
        raise RuntimeError("Conflicto: tus cambios tocan las mismas lineas.")
    return merged.stdout


def prepare(root: Path, scratch: Path):
    plan, problems, changes = {}, [], []
    for rel in EDITED + NEW:
        local_path = root / rel
        local = local_path.read_bytes() if local_path.is_file() else None
        target = normalized(remote(TARGET, rel))
        if local is not None and normalized(local) == target:
            changes.append((rel, "YA INSTALADO"))
            continue
        if rel in NEW:
            if local is not None:
                changes.append((rel, "DIFERENTE"))
                problems.append(rel + ": ya existe, pero es distinto")
            else:
                plan[rel] = target
                changes.append((rel, "CREAR"))
            continue
        if local is None:
            problems.append(rel + ": falta el archivo original")
            changes.append((rel, "AUSENTE"))
            continue
        base = normalized(remote(BASE, rel))
        if normalized(local) == base:
            new_content = target
            changes.append((rel, "ACTUALIZAR SIN CONFLICTO"))
        else:
            try:
                new_content = merged_three_way(
                    local, base, target, scratch / rel.replace("/", "_"))
                changes.append((rel, "FUSION LIMPIA"))
            except RuntimeError as exc:
                problems.append(rel + ": " + str(exc))
                changes.append((rel, "CONFLICTO"))
                continue
        if b"\r\n" in local:
            new_content = new_content.replace(b"\n", b"\r\n")
        if new_content != local:
            plan[rel] = new_content
    return changes, plan, problems


def verify(plan: dict[str, bytes]) -> list[str]:
    failures = []
    for rel, contents in plan.items():
        if rel.endswith(".py"):
            try:
                compile(contents, rel, "exec")
            except SyntaxError as error:
                failures.append(rel + ": " + str(error))
        if rel.endswith(".js") and shutil.which("node"):
            with tempfile.TemporaryDirectory(prefix="sky_js_check_") as dirname:
                filename = Path(dirname) / "hud.js"
                filename.write_bytes(contents)
                result = subprocess.run(
                    ["node", "--check", str(filename)], capture_output=True,
                    timeout=20)
                if result.returncode:
                    failures.append(rel + ": JavaScript invalido")
    return failures


def run() -> int:
    ap = argparse.ArgumentParser(description="SKY — servicio Vosk único por computadora")
    ap.add_argument("--aplicar", action="store_true",
                    help="Actualizar solo si no existen conflictos")
    options = ap.parse_args()
    try:
        root = project_dir()
        if not shutil.which("git"):
            raise RuntimeError("No se encontro Git en el equipo.")
        with tempfile.TemporaryDirectory(prefix="sky_mic_merge_") as td:
            changes, plan, errors = prepare(root, Path(td))
        errors.extend(verify(plan))
        print("SKY: revision de escucha Vosk sin duplicados")
        for path, state in changes:
            print(" -", path, ":", state)
        if errors:
            print("\nNO SE MODIFICO NADA: hay que revisar estas diferencias:")
            for error in errors:
                print(" *", error)
            return 2
        if not options.aplicar:
            print("\nSin modificaciones. Compatible para aplicar:", len(plan))
            print("Para instalar: ejecuta otra vez con --aplicar.")
            return 0
        if not plan:
            print("YA ACTUALIZADO: no es necesario modificar archivos.")
            return 0
        backup = root / "local_data" / "respaldos_sky" / (
            "voz_unica_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        backup.mkdir(parents=True, exist_ok=False)
        originals = {}
        for rel in plan:
            original = root / rel
            originals[rel] = original.read_bytes() if original.is_file() else None
            if originals[rel] is not None:
                save = backup / rel
                save.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, save)
        try:
            for rel, data in plan.items():
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                staged = dst.with_name(dst.name + ".sky_voice_temp")
                staged.write_bytes(data)
                os.replace(staged, dst)
        except Exception:
            for rel, previous in originals.items():
                dst = root / rel
                if previous is None:
                    dst.unlink(missing_ok=True)
                else:
                    dst.write_bytes(previous)
            raise RuntimeError("Error al instalar: cambios revertidos.")
        print("APLICADO:", len(plan), "archivos.")
        print("RESPALDO:", backup)
        print("Reinicia los servicios de SKY una sola vez y verifica el micrófono.")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print("ERROR:", str(exc)[:550])
        return 3


if __name__ == "__main__":
    raise SystemExit(run())
