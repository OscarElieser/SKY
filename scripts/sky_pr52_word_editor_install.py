"""Conservative Word-in-place editor installer for owner's customized SKY.

Preflight by default. AST inserts only routing code in the existing assistant;
strictly anchored edits to the existing capability registry and device agent.
No wholesale file replacement, no HUD/API/Vosk changes, backup + rollback.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
import os
from pathlib import Path
import shutil
import urllib.request

ROOT = Path.cwd()
REF = "4c689a505cf5b9f36c692b17ec5c7195c11809e7"
REPO = "OscarElieser/SKY"
NEW = (
    "neural_core/sky_word_editor.py",
    "tests/test_sky_word_editor.py",
    "tests/test_sky_pr52_word_editor_install.py",
)

CAP_CHANGES = [
    (
        "Capacidad('type_text', 'Escribir en la app activa', "
        "'Teclear un texto dictado dentro de la ventana que está al frente', "
        "('type_text',), 'alto'),",
        "Capacidad('type_text', 'Escribir en aplicaciones', "
        "'Escritura en la app activa (legado) y en un documento Word abierto "
        "por automatización verificada', ('type_text', 'word_write'), 'alto'),",
    ),
    (
        "    'type_text': 'Escribir texto en la aplicación activa',",
        "    'type_text': 'Escribir texto en la aplicación activa',\n"
        "    'word_write': 'Agregar texto y verificarlo en el único documento Word abierto',",
    ),
    (
        "def requiere_confirmacion(accion: str, params: dict, politica: dict) -> bool:\n"
        "    if nivel_riesgo(accion, params) >= 3:",
        "def requiere_confirmacion(accion: str, params: dict, politica: dict) -> bool:\n"
        "    if accion == 'word_write':\n"
        "        return True  # El dueño confirma cada edición de su documento.\n"
        "    if nivel_riesgo(accion, params) >= 3:",
    ),
]

AGENT_CHANGES = [
    (
        "    if action in ('window_action', 'task_action', 'player_control'):\n"
        "        return str(params.get('subaction', ''))\n"
        "    if action == 'keyboard_shortcut':",
        "    if action in ('window_action', 'task_action', 'player_control'):\n"
        "        return str(params.get('subaction', ''))\n"
        "    if action == 'word_write':\n"
        "        return str(len(str(params.get('text', '')))) + ' caracteres a Word'\n"
        "    if action == 'keyboard_shortcut':",
    ),
    (
        "    if action == 'keyboard_shortcut':\n"
        "        if params != {'shortcut': 'ctrl+f4', 'expected_app': 'winword.exe'}:\n"
        "            raise ValueError('Atajo de teclado no autorizado: sólo Ctrl+F4 en Word.')\n"
        "    if not caps.accion_habilitada(action, politica, params):",
        "    if action == 'keyboard_shortcut':\n"
        "        if params != {'shortcut': 'ctrl+f4', 'expected_app': 'winword.exe'}:\n"
        "            raise ValueError('Atajo de teclado no autorizado: sólo Ctrl+F4 en Word.')\n"
        "    if action == 'word_write':\n"
        "        from neural_core.sky_word_editor import validar_parametros\n"
        "        validar_parametros(params)\n"
        "    if not caps.accion_habilitada(action, politica, params):",
    ),
    (
        "    if action == 'keyboard_shortcut':\n"
        "        from neural_core.sky_keyboard_shortcuts import enviar_ctrl_f4_word\n"
        "        return enviar_ctrl_f4_word()\n"
        "    if action == 'window_action':",
        "    if action == 'keyboard_shortcut':\n"
        "        from neural_core.sky_keyboard_shortcuts import enviar_ctrl_f4_word\n"
        "        return enviar_ctrl_f4_word()\n"
        "    if action == 'word_write':\n"
        "        from neural_core.sky_word_editor import escribir_en_word\n"
        "        return escribir_en_word(params)\n"
        "    if action == 'window_action':",
    ),
]


def root_dir() -> Path:
    root = ROOT.resolve()
    if not (root / "SKY_INICIAR.bat").is_file():
        raise RuntimeError("Ejecutá desde la carpeta principal de SKY.")
    return root


def read_source(raw: bytes) -> str:
    return raw.decode("utf-8-sig").replace("\r\n", "\n")


def encode_source(text: str, original: bytes) -> bytes:
    if b"\r\n" in original:
        text = text.replace("\n", "\r\n")
    return text.encode("utf-8-sig" if original.startswith(b"\xef\xbb\xbf")
                       else "utf-8")


def exact_patch(raw: bytes, changes: list, filename: str) -> bytes | None:
    text = read_source(raw)
    for before, after in changes:
        if after in text:
            continue
        if text.count(before) != 1:
            raise RuntimeError(filename + ": fragmento distinto o duplicado.")
        text = text.replace(before, after, 1)
    if text == read_source(raw):
        return None
    compile(text, filename, "exec")
    return encode_source(text, raw)


def assistant_patch(raw: bytes) -> bytes | None:
    text = read_source(raw)
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)

    def function(name):
        hits = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == name]
        if len(hits) != 1:
            raise RuntimeError(
                "No encuentro una función " + name + "() única y compatible."
            )
        return hits[0]

    def contains(fn, needle):
        return needle in (ast.get_source_segment(text, fn) or "")

    interp, rules = function("interpretar"), function("reglas")
    edits = []
    if not contains(interp, "from .sky_word_editor import propuesta as word_direct"):
        body = interp.body
        if not body:
            raise RuntimeError("interpretar() no tiene cuerpo.")
        ix = body[0].lineno - 1
        if (isinstance(body[0], ast.Expr) and
                isinstance(body[0].value, ast.Constant) and
                isinstance(body[0].value.value, str)):
            if len(body) < 2:
                raise RuntimeError("interpretar() solo tiene documentación.")
            ix = body[1].lineno - 1
        edits.append((
            ix, "    # SKY-WORD: orden explícita, sin pasar por el LLM.\n"
            "    from .sky_word_editor import propuesta as word_direct\n"
            "    word = word_direct(texto)\n"
            "    if word:\n"
            "        return word\n",
        ))
    elif not (contains(interp, "word_direct(texto)") and
              contains(interp, "return word")):
        raise RuntimeError("interpretar() tiene una integración parcial de Word.")

    if not contains(rules, "from .sky_word_editor import solicitud as word_local"):
        guard = [
            n for n in rules.body if isinstance(n, ast.If)
            and isinstance(n.test, ast.Name) and n.test.id == "stop"
            and len(n.body) == 1 and isinstance(n.body[0], ast.Return)
            and isinstance(n.body[0].value, ast.Name)
            and n.body[0].value.id == "stop"
        ]
        if len(guard) != 1:
            raise RuntimeError(
                "No encuentro una parada de emergencia única en reglas(); "
                "no modificar."
            )
        edits.append((
            guard[0].end_lineno,
            "    # SKY-WORD: confirmar escritura después de parada de emergencia.\n"
            "    from .sky_word_editor import solicitud as word_local\n"
            "    word = word_local(texto)\n"
            "    if word:\n"
            "        return word\n",
        ))
    elif not (contains(rules, "word_local(texto)") and
              contains(rules, "return word")):
        raise RuntimeError("reglas() tiene una integración parcial de Word.")

    if not edits:
        return None
    for ix, block in sorted(edits, reverse=True):
        lines.insert(ix, block)
    updated = "".join(lines)
    compile(updated, "neural_core/sky_asistente_personal.py", "exec")
    return encode_source(updated, raw)


def download(path: str) -> bytes:
    url = ("https://raw.githubusercontent.com/" + REPO + "/" + REF + "/" + path)
    req = urllib.request.Request(url, headers={"User-Agent": "SKY-Word-Installer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read(100_001)
    if not data or len(data) > 100_000:
        raise RuntimeError("Descarga Word incompleta o excesiva: " + path)
    compile(data, path, "exec")
    return data


def plan(root: Path):
    changes, lines, errors = {}, [], []
    existing = {
        "neural_core/sky_asistente_personal.py": assistant_patch,
        "neural_core/sky_capacidades.py": (
            lambda raw: exact_patch(raw, CAP_CHANGES, "neural_core/sky_capacidades.py")
        ),
        "agente_dispositivo.py": (
            lambda raw: exact_patch(raw, AGENT_CHANGES, "agente_dispositivo.py")
        ),
    }
    for name, patch in existing.items():
        dest = root / name
        if not dest.is_file():
            errors.append(name + ": no existe.")
            lines.append((name, "FALTA; NO TOCAR"))
            continue
        try:
            patched = patch(dest.read_bytes())
            if patched is None:
                lines.append((name, "YA INTEGRADO"))
            else:
                changes[name] = patched
                lines.append((name, "INSERCIÓN CONTROLADA"))
        except (SyntaxError, RuntimeError, UnicodeError, ValueError) as e:
            errors.append(name + ": " + str(e)[:180])
            lines.append((name, "CONFLICTO; NO TOCAR"))
    for name in NEW:
        dest = root / name
        try:
            expected = download(name)
        except (OSError, RuntimeError, SyntaxError) as e:
            errors.append(name + ": no puedo descargarlo (" +
                          type(e).__name__ + ")")
            continue
        if dest.exists():
            if dest.read_bytes().replace(b"\r\n", b"\n") != expected.replace(b"\r\n", b"\n"):
                errors.append(name + ": ya existe con contenido distinto.")
                lines.append((name, "CONFLICTO; NO TOCAR"))
            else:
                lines.append((name, "YA INTEGRADO"))
        else:
            changes[name] = expected
            lines.append((name, "CREAR"))
    return changes, lines, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="SKY · editor seguro de Word")
    parser.add_argument("--aplicar", action="store_true",
                        help="Escribir únicamente si todo es compatible")
    args = parser.parse_args()
    try:
        root = root_dir()
        changed, states, errors = plan(root)
        print("SKY · escribir directamente en Word, sin perder módulos")
        for name, state in states:
            print(" -", name, ":", state)
        print(" - HUD, API propia, Vosk, micrófono y Ollama: NO SE MODIFICAN")
        if errors:
            print("RECHAZADO: no se modificó nada.")
            for err in errors:
                print(" *", err[:230])
            return 2
        if not args.aplicar:
            print("SOLO COMPROBACIÓN:", len(changed), "archivos preparados")
            return 0
        if not changed:
            print("YA INSTALADO")
            return 0
        backup = root / "local_data" / "respaldos_sky" / (
            "word_editor_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        )
        backup.mkdir(parents=True, exist_ok=False)
        previous = {}
        for name in changed:
            path = root / name
            previous[name] = path.read_bytes() if path.is_file() else None
            if previous[name] is not None:
                saved = backup / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, saved)
        try:
            for name, data in changed.items():
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                staged = destination.with_name(destination.name + ".sky_word_tmp")
                staged.write_bytes(data)
                os.replace(staged, destination)
        except OSError:
            for name, old in previous.items():
                destination = root / name
                if old is None:
                    destination.unlink(missing_ok=True)
                else:
                    destination.write_bytes(old)
            raise RuntimeError("Instalación fallida: se restauraron los originales.")
        print("APLICADOS:", len(changed), "RESPALDO:", backup)
        print("Para probar, detené y reiniciá una sola instancia de API y agente.")
        return 0
    except (RuntimeError, OSError, SyntaxError, UnicodeError) as e:
        print("ERROR:", str(e)[:300])
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
