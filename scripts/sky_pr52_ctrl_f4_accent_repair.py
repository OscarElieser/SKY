"""Repair the single Spanish 'Enviá Ctrl+F4' parsing typo, preserving local SKY.

Dry-run by default; inserts exactly one regex character change and installs
the missing AST-updater test. Backs up changed files and refuses conflicts.
No voice, browser, permissions, API, installer, or Word actions executed.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import urllib.request

ROOT_NAME = "SKY_INICIAR.bat"
SOURCE = "neural_core/sky_keyboard_shortcuts.py"
MISSING_TEST = "tests/test_sky_pr52_ctrl_f4_ast_install.py"
OLD = "env[ií]a|pon".encode("utf-8")
NEW = "env[ií][aá]|pon".encode("utf-8")
REF = "4e9ca74e5acddee05cd5aae411734396c7e2e953"
TEST_URL = (
    "https://raw.githubusercontent.com/OscarElieser/SKY/" + REF + "/" + MISSING_TEST
)


def get_test() -> bytes:
    req = urllib.request.Request(TEST_URL, headers={"User-Agent": "SKY-Repair/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read(80_001)
    if not raw or len(raw) > 80_000:
        raise RuntimeError("Test remoto incompleto o demasiado grande")
    compile(raw, MISSING_TEST, "exec")
    return raw


def plan(root: Path):
    result, messages, errors = {}, [], []
    parser = root / SOURCE
    if not parser.is_file():
        errors.append(SOURCE + ": archivo no encontrado")
    else:
        original = parser.read_bytes()
        if original.count(OLD) == 1 and original.count(NEW) == 0:
            changed = original.replace(OLD, NEW, 1)
            try:
                compile(changed, SOURCE, "exec")
            except SyntaxError:
                errors.append(SOURCE + ": el parche no pasa la compilación")
            else:
                result[SOURCE] = changed
                messages.append((SOURCE, "CAMBIO MÍNIMO: Enviá/Envía/Envia"))
        elif original.count(NEW) == 1 and original.count(OLD) == 0:
            messages.append((SOURCE, "YA CORREGIDO"))
        else:
            errors.append(SOURCE + ": patrón distinto o ambiguo, se conserva intacto")
            messages.append((SOURCE, "CONFLICTO"))
    test = root / MISSING_TEST
    if not test.is_file():
        # The missing test is added, never overwrite an existing version.
        try:
            blob = get_test()
            result[MISSING_TEST] = blob
            messages.append((MISSING_TEST, "CREAR PRUEBA FALTANTE"))
        except (OSError, ValueError, SyntaxError, RuntimeError) as e:
            errors.append("No pude preparar el test: " + type(e).__name__)
    else:
        messages.append((MISSING_TEST, "TEST YA EXISTE: NO SE REEMPLAZA"))
    return result, messages, errors


def main():
    ap = argparse.ArgumentParser(description="SKY: reparar Enviá Ctrl+F4")
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    root = Path.cwd().resolve()
    if not (root / ROOT_NAME).is_file():
        print("ERROR: ejecutá en la carpeta principal de SKY")
        return 3
    try:
        changes, status, errors = plan(root)
        print("SKY — reparación puntual del atajo de Word")
        for name, state in status:
            print(" -", name, ":", state)
        print(" - HUD, agente, cerebro, voz y permisos: NO SE REEMPLAZAN")
        if errors:
            for message in errors:
                print("CONFLICTO:", message)
            print("No se modificó ningún archivo.")
            return 2
        if not args.aplicar:
            print("SOLO COMPROBACIÓN:", len(changes), "archivos preparados")
            return 0
        if not changes:
            print("YA CORREGIDO")
            return 0
        backup = (root / "local_data" / "respaldos_sky" /
                  ("ctrl_f4_acento_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")))
        backup.mkdir(parents=True, exist_ok=False)
        before = {}
        for name in changes:
            target = root / name
            before[name] = target.read_bytes() if target.is_file() else None
            if before[name] is not None:
                saved = backup / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
        try:
            for name, data in changes.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                staged = target.with_name(target.name + ".sky_accent_stage")
                staged.write_bytes(data)
                os.replace(staged, target)
        except OSError:
            for name, previous in before.items():
                target = root / name
                if previous is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(previous)
            raise RuntimeError("Error de instalación: se restauraron los originales")
        print("APLICADOS:", len(changes), "RESPALDO:", backup)
        print("Volvé a ejecutar ambos tests; reiniciá SKY sólo cuando estén aprobados.")
        return 0
    except (OSError, RuntimeError) as exc:
        print("ERROR:", str(exc)[:400])
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
