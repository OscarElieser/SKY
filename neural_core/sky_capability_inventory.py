"""SKY capability inventory — local executables and Python libraries ONLY.

Detection is not proof that a complete Skill has been configured or tested.
No installation, remote request, shell execution or permissions are granted.
"""
from __future__ import annotations

import importlib.util
import platform
import shutil

from . import sky_advanced_planner

_TOOLS = (
    ("local-llm", "Motor de razonamiento local", "engine", ""),
    ("ffmpeg", "Edición y transcodificación de audio/video", "exe", "ffmpeg"),
    ("libreoffice", "Edición y conversión de documentos", "exe-any", "soffice|libreoffice"),
    ("blender", "Modelado y render 3D", "exe", "blender"),
    ("git", "Control de versiones", "exe", "git"),
    ("python-docx", "Documentos Word", "module", "docx"),
    ("openpyxl", "Hojas de cálculo", "module", "openpyxl"),
    ("python-pptx", "Presentaciones", "module", "pptx"),
    ("pypdf", "Lectura y organización PDF", "module", "pypdf"),
    ("playwright", "Navegador automatizado autorizado", "module", "playwright"),
    ("faster-whisper", "Transcripción local de voz", "module", "faster_whisper"),
    ("piper-tts", "Síntesis local de voz", "exe", "piper"),
    ("node", "Herramientas web JavaScript", "exe", "node"),
)


def _module_detected(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def inventory() -> dict:
    items = []
    for ident, description, kind, hint in _TOOLS:
        if kind == "engine":
            is_detected = sky_advanced_planner.local_available()
            note = "Modelo local responde al endpoint; no garantiza calidad ni licencias."
        elif kind == "module":
            is_detected = _module_detected(hint)
            note = "Biblioteca importable; las funciones deben probarse por separado."
        elif kind == "exe-any":
            is_detected = any(shutil.which(exe) for exe in hint.split("|"))
            note = "Ejecutable visible en PATH; integración aún requiere pruebas."
        else:
            is_detected = bool(shutil.which(hint))
            note = "Ejecutable visible en PATH; integración aún requiere pruebas."
        items.append({
            "id": ident, "description": description, "detected": bool(is_detected),
            "detection_only": True, "automatic_installation": False,
            "permissions_granted": False, "note": note,
        })
    detected = sum(item["detected"] for item in items)
    return {
        "owner": "SKY CORE", "scope": "local_device_only",
        "platform": platform.system(),
        "total_probes": len(items), "detected_count": detected,
        "missing_count": len(items) - detected, "tools": items,
        "warning": ("Detectar una herramienta no significa que la Skill esté completa, "
                    "autorizada ni probada. SKY nunca instala programas sin aprobación."),
    }
