"""Conservative HUD-only repair for a locally customized SKY Windows install.

Never opens, edits or replaces sky_manos_libres.py. Repairs only the HUD,
assistant core chat rule, missing chat-intent module and regression test.
Read-only by default; backs up all edited files before --aplicar.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

REPO = "OscarElieser/SKY"
BASE = "7526b8092301d6834e5c935407581dedcee57f09"
# Pin to the exact earlier reviewed HUD-chat implementation, not branch HEAD:
TARGET = "fa69d42b54f26693751881cf3badee6f078d6fe1"

EDITED = ("metaverse/static/hud.js", "neural_core/sky_asistente_personal.py")
NEW = ("neural_core/sky_hud_intents.py", "tests/test_sky_hud_chat_voice_bridge.py")
VOICE = "sky_manos_libres.py"

# Limit the change in the customized listener to one exact statement boundary.
VOICE_ANCHOR = "                intent=interpret_command(command)\n"
VOICE_NEXT = "                if intent:\n"
VOICE_BLOCK = """
                # SKY-HUD-CHAT-BRIDGE: UI-only, never grants device permissions.
                if (intent and intent.get('action') == 'holographic_window'
                        and (intent.get('params') or {}).get('subaction') == 'open_chat'):
                    try:
                        add_inbox(command, intent)
                        msg_chat = ('Envié la orden al HUD; el panel se abrirá '
                                    'cuando la página de SKY esté disponible.')
                    except (OSError, ValueError) as exc:
                        msg_chat = 'No pude enviar la orden al HUD.'
                        print('Fallo de bandeja de voz:', type(exc).__name__)
                    coordinador_voz.record_turn(command, msg_chat)
                    say(msg_chat)
                    continue
"""


def root_dir() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "SKY_INICIAR.bat").is_file():
        return cwd
    cwd = Path(__file__).resolve().parent
    if cwd.name.lower() == "scripts":
        cwd = cwd.parent
    if not (cwd / "SKY_INICIAR.bat").is_file():
        raise RuntimeError("Ejecutá desde la carpeta principal de SKY.")
    return cwd


def download(ref: str, relative: str) -> bytes:
    url = "https://raw.githubusercontent.com/{}/{}/{}".format(
        REPO, ref, urllib.parse.quote(relative, safe="/"))
    request = urllib.request.Request(url, headers={"User-Agent": "SKY-Surgical-Chat/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        blob = response.read(1_000_001)
    if not blob or len(blob) > 1_000_000:
        raise RuntimeError("Descarga incompleta o demasiado grande: " + relative)
    return blob.replace(b"\r\n", b"\n")


def merge(existing: bytes, baseline: bytes, target: bytes, folder: Path) -> bytes:
    folder.mkdir(parents=True, exist_ok=True)
    sources = [folder / "local", folder / "base", folder / "target"]
    for p, raw in zip(sources, (existing, baseline, target)):
        p.write_bytes(raw.replace(b"\r\n", b"\n"))
    cmd = ["git", "merge-file", "-p", "--diff3", "-L", "LOCAL",
           "-L", "BASE", "-L", "SKY_CHAT", *(str(p) for p in sources)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError("Hay cambios superpuestos; no se alterará este archivo.")
    return proc.stdout


def surgically_prepare_voice(contents: bytes) -> tuple[bytes | None, str]:
    """Never replace the listener: at most one minimal, parseable addition."""
    text = contents.decode("utf-8-sig")
    if ("'holographic_window'" in text and "'open_chat'" in text
            and "add_inbox(command" in text):
        return None, "PUENTE DE VOZ YA EXISTENTE"
    lf = text.replace("\r\n", "\n")
    if lf.count(VOICE_ANCHOR) != 1:
        raise RuntimeError("No se encontró un único punto seguro para la voz.")
    index = lf.index(VOICE_ANCHOR) + len(VOICE_ANCHOR)
    next_lines = lf[index:].lstrip("\n").splitlines()
    if not next_lines or next_lines[0] != VOICE_NEXT.rstrip("\n"):
        raise RuntimeError("La estructura local del intérprete es diferente. Revisión manual.")
    if "from neural_core.voz_inbox import add_inbox" not in lf:
        raise RuntimeError("No existe importación de la bandeja de voz.")
    if "from neural_core.sky_asistente_personal import interpretar as interpret_command" not in lf:
        raise RuntimeError("La importación del intérprete cambió.")
    if "coordinador_voz.record_turn" not in lf or "def say(" not in lf:
        raise RuntimeError("No están disponibles los métodos de voz que necesitamos.")
    proposed = lf[:index] + VOICE_BLOCK.lstrip("\n") + lf[index:]
    compile(proposed, VOICE, "exec")
    if b"\r\n" in contents:
        proposed = proposed.replace("\n", "\r\n")
    return proposed.encode("utf-8"), "INSERCIÓN MÍNIMA, SIN REEMPLAZAR VOZ"


def build_plan(root: Path, workspace: Path):
    changes, plan, problems = [], {}, []
    for rel in EDITED + NEW:
        target = download(TARGET, rel)
        file = root / rel
        current = file.read_bytes() if file.is_file() else None
        if current is not None and current.replace(b"\r\n", b"\n") == target:
            changes.append((rel, "YA INSTALADO"))
            continue
        if rel in NEW:
            if current is not None:
                changes.append((rel, "DISTINTO"))
                problems.append(rel + ": ya existe con contenido distinto.")
            else:
                plan[rel] = target
                changes.append((rel, "CREAR"))
            continue
        if current is None:
            problems.append(rel + ": archivo base ausente.")
            changes.append((rel, "AUSENTE"))
            continue
        baseline = download(BASE, rel)
        try:
            desired = (target if current.replace(b"\r\n", b"\n") == baseline
                       else merge(current, baseline, target,
                                  workspace / rel.replace("/", "_")))
            if b"\r\n" in current:
                desired = desired.replace(b"\n", b"\r\n")
            if desired != current:
                plan[rel] = desired
                changes.append((rel, "FUSIÓN CONSERVADORA"))
            else:
                changes.append((rel, "YA INTEGRADO"))
        except RuntimeError as exc:
            problems.append(rel + ": " + str(exc))
            changes.append((rel, "CONFLICTO"))
    # Deliberately preserve the owner's voice daemon: different versions use
    # distinct loops. The existing intent->inbox fallback already supports
    # UI-only proposals, and this repair must never guess how to patch it.
    changes.append((VOICE, "NO SE TOCA: se conserva tu voz local"))
    return changes, plan, problems


def validate(plan: dict[str, bytes]) -> list[str]:
    problems = []
    for rel, data in plan.items():
        if rel.endswith(".py"):
            try:
                compile(data, rel, "exec")
            except (SyntaxError, UnicodeError) as exc:
                problems.append(rel + ": error de sintaxis: " + str(exc)[:170])
        elif rel.endswith(".js") and shutil.which("node"):
            with tempfile.TemporaryDirectory(prefix="sky_chat_node_") as td:
                f = Path(td) / "hud.js"
                f.write_bytes(data)
                proc = subprocess.run(["node", "--check", str(f)],
                                      capture_output=True, timeout=20)
                if proc.returncode:
                    problems.append(rel + ": JavaScript inválido; no instalar.")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="SKY: reparar únicamente el HUD sin tocar voz")
    parser.add_argument("--aplicar", action="store_true")
    options = parser.parse_args()
    try:
        root = root_dir()
        if not shutil.which("git"):
            raise RuntimeError("Git es necesario para la conciliación.")
        with tempfile.TemporaryDirectory(prefix="sky_chat_surgical_") as td:
            changes, plan, problems = build_plan(root, Path(td))
        problems.extend(validate(plan))
        print("SKY — reparación SOLO HUD; sky_manos_libres.py queda intacto")
        for path, status in changes:
            print(" -", path, ":", status)
        if problems:
            print("NO APLICAR: se detectaron diferencias que requieren revisión:")
            for problem in problems:
                print(" *", problem)
            print("No se modificó ningún archivo.")
            return 2
        if not options.aplicar:
            print("SOLO COMPROBACIÓN: cambios compatibles", len(plan))
            print("Ejecutá --aplicar únicamente con SKY detenido.")
            return 0
        if not plan:
            print("SIN CAMBIOS: todo estaba instalado.")
            return 0
        backup = (root / "local_data" / "respaldos_sky" /
                  ("hud_solo_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")))
        backup.mkdir(parents=True)
        originals = {}
        for rel in plan:
            file = root / rel
            originals[rel] = file.read_bytes() if file.is_file() else None
            if originals[rel] is not None:
                saved = backup / rel
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, saved)
        try:
            for rel, contents in plan.items():
                file = root / rel
                file.parent.mkdir(parents=True, exist_ok=True)
                stage = file.with_name(file.name + ".sky_tmp")
                stage.write_bytes(contents)
                os.replace(stage, file)
        except Exception:
            for rel, before in originals.items():
                file = root / rel
                if before is None:
                    file.unlink(missing_ok=True)
                else:
                    file.write_bytes(before)
            raise RuntimeError("Falló instalación; restauré los archivos originales.")
        print("APLICADOS", len(plan), "archivos. Respaldo:", backup)
        print("Reiniciá la API y el HUD con Ctrl+F5. La voz local no fue modificada.")
        return 0
    except (RuntimeError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
        print("ERROR:", str(exc)[:600])
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
