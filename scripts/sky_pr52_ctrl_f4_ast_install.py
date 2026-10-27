"""AST-guided incremental installation of verified Ctrl+F4 in SKY.

The owner's assistant module differs from GitHub and the exact-line installer
correctly rejected it. Detect actual function boundaries via Python AST;
insert only at verified safe locations, preserving the rest of every file.
Read-only by default; back up and roll back edits before --aplicar.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
import os
from pathlib import Path
import shutil
import urllib.parse
import urllib.request

REPO = "OscarElieser/SKY"
# Immutable reviewed implementation (this commit contains the full new feature).
REF = "b32422b28286703aa25b6964e421aa4f8a85de08"

CHAT_ORIGINAL = """    from .sky_hud_intents import panel_chat
    hud_chat = panel_chat(texto)
    if hud_chat:
        return hud_chat
    propio = _interpretar_propio(texto)"""
CHAT_UPDATED = """    from .sky_hud_intents import panel_chat
    hud_chat = panel_chat(texto)
    if hud_chat:
        return hud_chat
    from .sky_keyboard_shortcuts import propuesta as atajo_escritorio
    atajo = atajo_escritorio(texto)
    if atajo:
        return atajo
    propio = _interpretar_propio(texto)"""

RULE_ORIGINAL = """    if stop:
        return stop
    # HUD commands are local UI actions, not generative conversation."""
RULE_UPDATED = """    if stop:
        return stop
    # Atajos de teclado peligrosos NO llegan al modelo generativo, y no se
    # ejecutan como herramientas del reproductor. Siempre piden autorización.
    from .sky_keyboard_shortcuts import solicitud as atajo_local
    shortcut = atajo_local(texto)
    if shortcut:
        return shortcut
    # HUD commands are local UI actions, not generative conversation."""

CAP_ORIGINAL = """    Capacidad('windows', 'Ventanas del escritorio', 'Listar, enfocar, minimizar, restaurar, organizar y cerrar ventanas', ('window_action', 'organize_windows'), 'medio'),"""
CAP_UPDATED = """    Capacidad('windows', 'Ventanas del escritorio', 'Listar, enfocar, minimizar, restaurar, organizar y cerrar ventanas; atajo Ctrl+F4 en Word solo con confirmación', ('window_action', 'organize_windows', 'keyboard_shortcut'), 'medio'),"""
CAP_DESC_ORIGINAL = """    'window_action': 'Gestionar ventanas abiertas del escritorio',"""
CAP_DESC_UPDATED = """    'window_action': 'Gestionar ventanas abiertas del escritorio',
    'keyboard_shortcut': 'Enviar un atajo autorizado a Word en primer plano',"""
CAP_LEVEL_ORIGINAL = """NIVEL_3 = frozenset({'note_trash', 'social_action'})"""
CAP_LEVEL_UPDATED = """NIVEL_3 = frozenset({'note_trash', 'social_action', 'keyboard_shortcut'})"""

AGENT_LOG_ORIGINAL = """    if action in ('window_action', 'task_action', 'player_control'):
        return str(params.get('subaction', ''))"""
AGENT_LOG_UPDATED = """    if action in ('window_action', 'task_action', 'player_control'):
        return str(params.get('subaction', ''))
    if action == 'keyboard_shortcut':
        return str(params.get('shortcut', ''))[:30]"""

AGENT_VALID_ORIGINAL = """    if action == 'window_action' and params.get('subaction', 'list') not in WINDOW_SUBACTIONS:
        raise ValueError('Subacción de ventana no autorizada.')
    if not caps.accion_habilitada(action, politica, params):"""
AGENT_VALID_UPDATED = """    if action == 'window_action' and params.get('subaction', 'list') not in WINDOW_SUBACTIONS:
        raise ValueError('Subacción de ventana no autorizada.')
    if action == 'keyboard_shortcut':
        if params != {'shortcut': 'ctrl+f4', 'expected_app': 'winword.exe'}:
            raise ValueError('Atajo de teclado no autorizado: sólo Ctrl+F4 en Word.')
    if not caps.accion_habilitada(action, politica, params):"""

AGENT_EXEC_ORIGINAL = """    if action == 'window_action':
        sub = params.get('subaction', 'list')"""
AGENT_EXEC_UPDATED = """    if action == 'keyboard_shortcut':
        from neural_core.sky_keyboard_shortcuts import enviar_ctrl_f4_word
        return enviar_ctrl_f4_word()
    if action == 'window_action':
        sub = params.get('subaction', 'list')"""

EDITS = {
    "neural_core/sky_capacidades.py": [
        (CAP_ORIGINAL, CAP_UPDATED), (CAP_DESC_ORIGINAL, CAP_DESC_UPDATED),
        (CAP_LEVEL_ORIGINAL, CAP_LEVEL_UPDATED),
    ],
    "agente_dispositivo.py": [
        (AGENT_LOG_ORIGINAL, AGENT_LOG_UPDATED),
        (AGENT_VALID_ORIGINAL, AGENT_VALID_UPDATED),
        (AGENT_EXEC_ORIGINAL, AGENT_EXEC_UPDATED),
    ],
}
NEW = ("neural_core/sky_keyboard_shortcuts.py",
       "tests/test_sky_keyboard_shortcuts.py")


def root_dir() -> Path:
    root = Path.cwd().resolve()
    if not (root / "SKY_INICIAR.bat").is_file():
        raise RuntimeError("Ejecutá desde la carpeta principal de SKY.")
    return root


def download(path: str) -> bytes:
    url = "https://raw.githubusercontent.com/{}/{}/{}".format(
        REPO, REF, urllib.parse.quote(path, safe="/"))
    req = urllib.request.Request(url, headers={"User-Agent": "SKY-CtrlF4-Installer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(400_001)
    if not raw or len(raw) > 400_000:
        raise RuntimeError("Descarga incompleta: " + path)
    return raw


def plan(root: Path):
    changes, issues, items = [], [], {}
    for rel, replacements in EDITS.items():
        local = root / rel
        if not local.is_file():
            issues.append(rel + " no existe.")
            changes.append((rel, "AUSENTE"))
            continue
        raw = local.read_bytes()
        text = raw.decode("utf-8-sig").replace("\r\n", "\n")
        conflict = False
        for before, after in replacements:
            if after in text:
                continue
            if text.count(before) != 1:
                issues.append(rel + ": punto de inserción distinto o duplicado.")
                conflict = True
                break
            text = text.replace(before, after, 1)
        if conflict:
            changes.append((rel, "CONFLICTO; NO SE TOCA"))
            continue
        if b"\r\n" in raw:
            text = text.replace("\n", "\r\n")
        new = text.encode("utf-8")
        if new != raw:
            items[rel] = new
            changes.append((rel, "INSERCIONES LIMITADAS"))
        else:
            changes.append((rel, "YA INSTALADO"))
    for rel in NEW:
        new = download(rel)
        local = root / rel
        if local.is_file():
            if local.read_bytes().replace(b"\r\n", b"\n") == new.replace(b"\r\n", b"\n"):
                changes.append((rel, "YA INSTALADO"))
            else:
                issues.append(rel + ": existe con contenido diferente.")
                changes.append((rel, "DIFERENTE; NO SE TOCA"))
        else:
            items[rel] = new
            changes.append((rel, "CREAR"))
    for rel, value in items.items():
        try:
            compile(value, rel, "exec")
        except (SyntaxError, UnicodeError) as exc:
            issues.append(rel + ": sintaxis inválida: " + str(exc))
    return items, changes, issues



def assistant_ast_patch(raw: bytes) -> tuple[bytes | None, str]:
    """Patch two functions using their AST, never using guessed local line matches.

    Respect any code already present in the owner's interpreter. No function
    is replaced, and no other statements are reordered or deleted.
    """
    src = raw.decode("utf-8-sig").replace("\r\n", "\n")
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)

    def find_func(name):
        hits = [n for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == name]
        if len(hits) != 1:
            raise RuntimeError("No encontré una única función " + name)
        if isinstance(hits[0], ast.AsyncFunctionDef):
            raise RuntimeError(name + " es asíncrona; necesita revisión manual.")
        return hits[0]

    def contains(node, name):
        return name in ast.get_source_segment(src, node) if ast.get_source_segment(src, node) else False

    interpreter = find_func("interpretar")
    rules = find_func("reglas")
    edits = []

    if not contains(interpreter, "from .sky_keyboard_shortcuts import propuesta as atajo_escritorio"):
        body = interpreter.body
        if not body:
            raise RuntimeError("interpretar está vacía; revisión manual.")
        insert_at = body[0].lineno - 1
        if (isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            if len(body) == 1:
                raise RuntimeError("interpretar no tiene lógica para conservar.")
            insert_at = body[1].lineno - 1
        edits.append((insert_at,
            "    # SKY-CTRL-F4: intención explícita antes del reproductor/LLM.\n"
            "    from .sky_keyboard_shortcuts import propuesta as atajo_escritorio\n"
            "    atajo = atajo_escritorio(texto)\n"
            "    if atajo:\n"
            "        return atajo\n"))
    else:
        if not (contains(interpreter, "atajo_escritorio(texto)") and
                contains(interpreter, "return atajo")):
            raise RuntimeError("interpretar tiene un parche parcial de atajos.")

    if not contains(rules, "from .sky_keyboard_shortcuts import solicitud as atajo_local"):
        guards = [n for n in rules.body if isinstance(n, ast.If)
                  and isinstance(n.test, ast.Name) and n.test.id == "stop"
                  and len(n.body) == 1 and isinstance(n.body[0], ast.Return)
                  and isinstance(n.body[0].value, ast.Name)
                  and n.body[0].value.id == "stop"]
        if len(guards) != 1:
            raise RuntimeError(
                "No encuentro una única parada de emergencia comprobable "
                "en reglas(); no haré inserciones."
            )
        # Immediately after the emergency-stop guard, never before it.
        edits.append((guards[0].end_lineno,
            "    # SKY-CTRL-F4: orden sensible, requiere permiso y confirmación.\n"
            "    from .sky_keyboard_shortcuts import solicitud as atajo_local\n"
            "    atajo_seguro = atajo_local(texto)\n"
            "    if atajo_seguro is not None:\n"
            "        return atajo_seguro\n"))
    else:
        if not (contains(rules, "atajo_local(texto)") and
                contains(rules, "return shortcut") or
                contains(rules, "return atajo_seguro")):
            raise RuntimeError("reglas tiene un parche parcial de atajos.")

    if not edits:
        return None, "YA INSTALADO: no reemplazar"
    for at, addition in sorted(edits, reverse=True):
        if at < 0 or at > len(lines):
            raise RuntimeError("Ubicación de AST inválida.")
        lines.insert(at, addition)
    updated = "".join(lines)
    compile(updated, "sky_asistente_personal.py", "exec")
    if b"\r\n" in raw:
        updated = updated.replace("\n", "\r\n")
    data = updated.encode("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8")
    return data, "INSERCIÓN AST, CÓDIGO EXISTENTE CONSERVADO"


_ordinary_plan = plan


def plan(root: Path):
    updates, changes, issues = _ordinary_plan(root)
    rel = "neural_core/sky_asistente_personal.py"
    file = root / rel
    if not file.is_file():
        changes.append((rel, "AUSENTE"))
        issues.append(rel + ": archivo no encontrado.")
    else:
        try:
            modified, status = assistant_ast_patch(file.read_bytes())
            changes.append((rel, status))
            if modified is not None:
                updates[rel] = modified
        except (SyntaxError, UnicodeError, ValueError, RuntimeError) as exc:
            changes.append((rel, "CONFLICTO; NO SE TOCA"))
            issues.append(rel + ": " + str(exc)[:230])
    return updates, changes, issues

def main() -> int:
    p = argparse.ArgumentParser(description="SKY — Ctrl+F4 con parches AST seguros para Word")
    p.add_argument("--aplicar", action="store_true", help="Instalar solo si no hay conflictos")
    a = p.parse_args()
    try:
        root = root_dir()
        updates, changes, errors = plan(root)
        print("SKY — reparar Ctrl+F4 conservando intérprete personalizado")
        for name, state in changes:
            print(" -", name, ":", state)
        print(" - sky_manos_libres.py, HUD y API: NO SE MODIFICAN")
        if errors:
            print("RECHAZADO: No se modificó nada.")
            for error in errors:
                print(" *", error[:250])
            return 2
        if not a.aplicar:
            print("SOLO COMPROBACIÓN:", len(updates), "archivos preparados")
            return 0
        if not updates:
            print("YA INSTALADO")
            return 0
        backup = root / "local_data" / "respaldos_sky" / (
            "ctrl_f4_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        backup.mkdir(parents=True, exist_ok=False)
        previous = {}
        for name in updates:
            source = root / name
            previous[name] = source.read_bytes() if source.exists() else None
            if previous[name] is not None:
                dest = backup / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
        try:
            for name, value in updates.items():
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                stage = dest.with_name(dest.name + ".sky_ctrlf4_tmp")
                stage.write_bytes(value)
                os.replace(stage, dest)
        except Exception:
            for name, before in previous.items():
                dest = root / name
                if before is None:
                    dest.unlink(missing_ok=True)
                else:
                    dest.write_bytes(before)
            raise RuntimeError("Instalación fallida; archivos originales restaurados.")
        print("APLICADOS:", len(updates), "RESPALDO:", backup)
        print("Reiniciá el agente Windows y la API desde sus consolas.")
        return 0
    except (OSError, RuntimeError, UnicodeError) as exc:
        print("ERROR:", str(exc)[:500])
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
