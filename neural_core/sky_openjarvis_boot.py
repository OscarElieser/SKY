"""Prepara el arranque opcional de OpenJarvis desde el supervisor de SKY.

Nunca descarga software ni crea entornos durante el arranque. No ocupa
puertos que ya usen otros procesos. OpenJarvis no controla al agente SKY.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def launch_spec() -> tuple[list[str], str] | None:
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    except ImportError:
        pass
    from .sky_openjarvis import configured, _base_url
    from .providers import local_only
    if local_only() or not configured():
        return None
    if os.getenv("SKY_OPENJARVIS_AUTOSTART", "0").strip() != "1":
        return None
    model = os.getenv("SKY_OPENJARVIS_MODEL", "").strip()
    if not model or len(model) > 150:
        raise ValueError("Modelo OpenJarvis no configurado.")
    path = Path(os.getenv("SKY_OPENJARVIS_HOME") or Path.home() / "OpenJarvis").expanduser().resolve()
    if not path.is_dir() or not (path / "pyproject.toml").is_file():
        raise FileNotFoundError("Falta instalación de OpenJarvis en SKY_OPENJARVIS_HOME.")
    uv = shutil.which("uv")
    if not uv:
        raise FileNotFoundError("Falta 'uv' para iniciar OpenJarvis por separado.")
    # uv --project usa su propio entorno. --no-sync evita descargas o mutaciones.
    port = _base_url().rsplit(":", 1)[1]
    return ([
        uv, "run", "--project", str(path), "--no-sync",
        "jarvis", "serve", "--host", "127.0.0.1", "--port", port,
        "--engine", "ollama", "--model", model, "--agent", "simple"
    ], str(path))
