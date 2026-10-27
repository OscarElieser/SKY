"""Install the small, verified-source news router without overwriting SKY.

Dry-run by default; applies only two precise insertions and two NEW files.
Does not touch Vosk, HUD, API, permissions, env files or user documents.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import urllib.parse
import urllib.request

REPO = "OscarElieser/SKY"
REF = "6dba416a4a98cff07430d01cd2c610489fe9c052"
NEW = ("neural_core/sky_live_updates.py", "tests/test_sky_live_updates.py")

# The original SKY functions remain intact; only a read-only route is added
# after existing explicit research commands, before the local LLM fallback.
CHAT_ANCHOR = """    research = sky_research_commands.interpretar(texto)
    if research:
        return research
    from . import sky_skills, sky_perfil"""
CHAT_TARGET = """    research = sky_research_commands.interpretar(texto)
    if research:
        return research
    # Preguntas públicas de actualidad: consultar noticias FECHADAS antes
    # del cerebro local. Evita afirmar que en 2026 no existen resultados
    # que una consulta online hubiera podido verificar.
    from .sky_live_updates import maybe_answer as _live_public
    live_result = _live_public(texto)
    if live_result is not None:
        return live_result
    from . import sky_skills, sky_perfil"""

VOICE_CHAT_ANCHOR = """    if len(pregunta) > 7000:
        raise ValueError('Pregunta demasiado larga (máximo 7000 caracteres)')
    from neural_core.sky_languages import normalize, get_preference, script_hint"""
VOICE_CHAT_TARGET = """    if len(pregunta) > 7000:
        raise ValueError('Pregunta demasiado larga (máximo 7000 caracteres)')
    # El servicio de voz Vosk utiliza este motor directamente. Mantener la
    # misma búsqueda real que en el HUD para preguntas públicas de actualidad.
    if not fuentes_externas:
        from .sky_live_updates import maybe_answer as _live_public
        actualidad = _live_public(pregunta)
        if actualidad is not None:
            return actualidad['mensaje'], []
    from neural_core.sky_languages import normalize, get_preference, script_hint"""

CHANGES = {
    "neural_core/sky_asistente_personal.py": (CHAT_ANCHOR, CHAT_TARGET),
    "neural_core/assistant.py": (VOICE_CHAT_ANCHOR, VOICE_CHAT_TARGET),
}


def download(rel: str) -> bytes:
    url = "https://raw.githubusercontent.com/{}/{}/{}".format(
        REPO, REF, urllib.parse.quote(rel, safe="/"))
    req = urllib.request.Request(url, headers={"User-Agent": "SKY-verified-current-news/1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = response.read(300_001)
    if not result or len(result) > 300_000:
        raise RuntimeError("Descarga incompleta o demasiado grande: " + rel)
    return result


def root_dir() -> Path:
    p = Path.cwd().resolve()
    if not (p / "SKY_INICIAR.bat").is_file():
        raise RuntimeError("Ejecutá desde la carpeta principal de SKY.")
    return p


def prepare(root: Path):
    plan, report, failures = {}, [], []
    for rel, (before, after) in CHANGES.items():
        file = root / rel
        if not file.is_file():
            report.append((rel, "AUSENTE"))
            failures.append(rel + ": falta archivo original.")
            continue
        original = file.read_bytes()
        src = original.decode("utf-8-sig")
        if after in src:
            report.append((rel, "YA INSTALADO"))
            continue
        if src.count(before) != 1:
            report.append((rel, "CONFLICTO"))
            failures.append(rel + ": el punto de inserción no coincide. No se reemplazará.")
            continue
        updated = src.replace(before, after)
        if b"\r\n" in original:
            updated = updated.replace("\n", "\r\n")
        data = updated.encode("utf-8")
        plan[rel] = data
        report.append((rel, "INSERCIÓN LIMITADA"))
    for rel in NEW:
        file = root / rel
        new = download(rel)
        if file.exists():
            if file.read_bytes().replace(b"\r\n", b"\n") == new.replace(b"\r\n", b"\n"):
                report.append((rel, "YA INSTALADO"))
            else:
                report.append((rel, "ARCHIVO DIFERENTE"))
                failures.append(rel + ": archivo existente diferente, no se sobrescribe.")
        else:
            plan[rel] = new
            report.append((rel, "CREAR"))
    for rel, data in plan.items():
        if rel.endswith(".py"):
            try:
                compile(data, rel, "exec")
            except SyntaxError as exc:
                failures.append(rel + ": sintaxis invalida: " + str(exc))
    return plan, report, failures


def main() -> int:
    p = argparse.ArgumentParser(description="SKY — reparar respuestas sobre noticias actuales")
    p.add_argument("--aplicar", action="store_true", help="Crear respaldo e instalar")
    args = p.parse_args()
    try:
        root = root_dir()
        plan, report, failures = prepare(root)
        print("SKY — investigación de actualidad con fuentes fechadas")
        for rel, status in report:
            print(" -", rel, ":", status)
        print(" - sky_manos_libres.py: NO SE TOCA")
        print(" - metaverse/api.py y metaverse/static/hud.js: NO SE TOCAN")
        if failures:
            print("RECHAZADO, SIN CAMBIOS:")
            for problem in failures:
                print(" *", problem)
            return 2
        if not args.aplicar:
            print("SOLO COMPROBACIÓN:", len(plan), "cambios compatibles")
            return 0
        if not plan:
            print("YA ACTUALIZADO: nada que modificar")
            return 0
        folder = root / "local_data" / "respaldos_sky" / (
            "actualidad_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        folder.mkdir(parents=True, exist_ok=False)
        previous = {}
        for rel in plan:
            file = root / rel
            previous[rel] = file.read_bytes() if file.is_file() else None
            if previous[rel] is not None:
                target = folder / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, target)
        try:
            for rel, data in plan.items():
                file = root / rel
                file.parent.mkdir(parents=True, exist_ok=True)
                tmp = file.with_name(file.name + ".sky_news_tmp")
                tmp.write_bytes(data)
                os.replace(tmp, file)
        except Exception:
            for rel, prior in previous.items():
                file = root / rel
                if prior is None:
                    file.unlink(missing_ok=True)
                else:
                    file.write_bytes(prior)
            raise RuntimeError("Error: todos los cambios se restauraron.")
        print("ACTUALIZADO:", len(plan), "archivos. RESPALDO:", folder)
        print("Reiniciá la API desde su consola original y actualizá el HUD con Ctrl+F5.")
        return 0
    except (OSError, RuntimeError, UnicodeError) as exc:
        print("ERROR:", str(exc)[:500])
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
