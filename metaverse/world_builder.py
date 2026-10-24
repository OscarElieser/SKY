"""SKY World Builder: real, bounded geometry from recognized Spanish campus plans.

Never advertises realistic classrooms, generated humans or animated lessons:
all output is editable, validated procedural geometry for the existing renderer.
This module is optional and does not alter the legacy scene generator.
"""
from __future__ import annotations

import random
import re
import unicodedata
from .engine import object3d

LEVEL_WORDS = {"una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4,
               "cinco": 5, "seis": 6}
SUPPORTED = ("centro educativo", "colegio", "escuela", "universidad",
             "campus", "instituto", "centro tecnologico", "centro de formacion",
             "politecnico", "aula", "laboratorio", "innovacion", "formacion tecnica")


def plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def _floors(prompt: str) -> int:
    match = re.search(r"\b([1-6]|una|uno|dos|tres|cuatro|cinco|seis)\s+"
                      r"(?:plantas?|pisos?|niveles?)\b", prompt)
    if not match:
        return 2
    token = match.group(1)
    return int(token) if token.isdigit() else LEVEL_WORDS[token]


def build_campus(prompt: str, seed: int = 42) -> tuple[dict, dict]:
    """Build concrete editable geometry with a human-readable provenance report.

    Recognized campus requests are supported offline. Unrecognized styles fail
    instead of claiming to have fulfilled an arbitrary instruction.
    """
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 1000:
        raise ValueError("Descripción de mundo: 1 a 1000 caracteres")
    if type(seed) is not int or not -(2**31) <= seed <= (2**31 - 1):
        raise ValueError("Semilla numérica inválida")
    instruction = plain(prompt)
    if not any(key in instruction for key in SUPPORTED):
        raise ValueError("Constructor avanzado: describí un colegio, campus, laboratorio o centro educativo; otros mundos usan Crear mundo")
    floors = _floors(instruction)
    rng = random.Random(seed)
    recognized = ["campus modular", f"{floors} niveles representados"]
    spaces = [("Recepción", "house", -8, 8, 4.0, 2.7, 3.5, "#4D9EBD")]
    if any(token in instruction for token in ("informatica", "computacion", "computadora", "programacion")):
        spaces.append(("Laboratorio de informática", "house", -9, -4, 5, 2.8, 4, "#49B9BE"))
        recognized.append("laboratorio de informática")
    if "laboratorio" in instruction and not any(x[0] == "Laboratorio de informática" for x in spaces):
        spaces.append(("Laboratorio de ciencias", "house", -9, -4, 5, 2.8, 4, "#49B9BE"))
        recognized.append("laboratorio de ciencias")
    if any(token in instruction for token in ("videoconferencia", "conferencia", "reunion", "auditorio")):
        spaces.append(("Salón de videoconferencias", "house", 9, -4, 5, 2.8, 4, "#B99EE9"))
        recognized.append("salón de videoconferencias")
    if "biblioteca" in instruction:
        spaces.append(("Biblioteca", "house", 9, 9, 5, 2.8, 4, "#DAAC63"))
        recognized.append("biblioteca")
    if "aula" in instruction or "clase" in instruction or "educativ" in instruction:
        spaces.append(("Aula interactiva", "house", 1, -8, 4, 2.8, 3.5, "#7FCADE"))
        recognized.append("aula interactiva")

    objects = []
    def add(name, kind, x, y, z, sx, sy, sz, color):
        objects.append(object3d(name, kind, x, y, z, sx, sy, sz, color))

    add("Terreno SKY", "platform", 0, -0.3, 0, 38, .35, 38, "#334F67")
    add("Camino de acceso", "platform", 0, -0.1, 6, 3, .1, 22, "#3C6074")
    # Main school is away from the default player spawn at (0,4).
    add("Edificio principal", "tower", 0, 0, -13, 8, floors * 2.6, 5, "#3E86B1")
    for level in range(floors):
        add(f"Separador nivel {level+1}", "platform",
            0, .4 + level * 2.6, -13, 8.3, .16, 5.3, "#8ED6EA")
        add(f"Ventana nivel {level+1}", "box",
            0, 1.2 + level * 2.6, -10.46, 3.6, 1.15, .1, "#B5E8FC")
    for name, kind, x, z, sx, sy, sz, color in spaces:
        add(name, kind, x, 0, z, sx, sy, sz, color)
    # Three benches are actually editable objects; do not pretend students exist.
    for i in range(3):
        add(f"Banco exterior {i+1}", "box", 4.7 + i*1.5, 0, 5.1,
            1.1, .55, .4, "#BEA47F")
    for i, x in enumerate((-15, -12.5, 12.5, 15)):
        add(f"Árbol ornamental {i+1}", "tree", x, 0, 12,
            .85, 2.4 + rng.random() * 1.1, .85, "#438B67")
    if len(objects) > 180:
        raise ValueError("La escena generada supera el máximo admitido")

    scene = {"prompt": prompt, "seed": seed, "theme": "estudio",
             "sky": "#102B47", "objects": objects}
    plan = {"engine": "sky-world-builder-procedural-v1",
            "recognized": recognized, "floors": floors,
            "geometry_objects": len(objects), "generated_real_geometry": True,
            "limitations": [
                "Los salones son volúmenes geométricos editables, no interiores equipados",
                "No se generaron personas, puertas funcionales ni clases por esta operación",
                "El número de niveles aparece en geometría externa; no habilita ascensores ni escaleras",
            ]}
    return scene, plan
