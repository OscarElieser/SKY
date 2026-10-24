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
    # Open-air rooms with physical walls, usable walkways and actual furniture.
    # A missing roof is deliberate: the existing orbital camera can see the interior.
    spaces = [("Recepción", -11, 7, 6, 6, "#4D9EBD", "reception")]
    if any(token in instruction for token in ("informatica", "computacion", "computadora", "programacion")):
        spaces.append(("Laboratorio de informática", -10, -5, 6, 6, "#49B9BE", "computers"))
        recognized.append("laboratorio de informática equipado con mesas y terminal")
    elif "laboratorio" in instruction:
        spaces.append(("Laboratorio de ciencias", -10, -5, 6, 6, "#49B9BE", "science"))
        recognized.append("laboratorio de ciencias con mobiliario geométrico")
    if any(token in instruction for token in ("videoconferencia", "conferencia", "reunion", "auditorio")):
        spaces.append(("Salón de videoconferencias", 10, -5, 6, 6, "#B99EE9", "meeting"))
        recognized.append("salón de videoconferencias con pantalla")
    if "biblioteca" in instruction:
        spaces.append(("Biblioteca", 10, 9, 6, 6, "#DAAC63", "library"))
        recognized.append("biblioteca con estanterías y mesa")
    if "aula" in instruction or "clase" in instruction or "educativ" in instruction:
        spaces.append(("Aula interactiva", 0, -3, 5.6, 6, "#7FCADE", "classroom"))
        recognized.append("aula abierta con pizarra y escritorios")

    objects = []
    def add(name, kind, x, y, z, sx, sy, sz, color, interactive=None):
        item = object3d(name, kind, x, y, z, sx, sy, sz, color)
        if interactive:
            # Validate with the existing scene schema; never embed executable code.
            from .engine import validate_object
            item["interaction"] = interactive
            item = validate_object(item)
        objects.append(item)

    def interact(kind, description, active=False):
        return {"type": kind, "description": description, "active": active}

    add("Terreno SKY", "platform", 0, -.3, 0, 38, .35, 38, "#334F67")
    add("Camino de acceso", "platform", 0, -.1, 6, 3, .1, 22, "#3C6074")
    add("Edificio principal", "tower", 0, 0, -13, 8, floors * 2.6, 5, "#3E86B1")
    for level in range(floors):
        add(f"Separador nivel {level+1}", "platform",
            0, .4 + level * 2.6, -13, 8.3, .16, 5.3, "#8ED6EA")
        add(f"Ventana nivel {level+1}", "box",
            0, 1.2 + level * 2.6, -10.46, 3.6, 1.15, .1, "#B5E8FC")

    def room(name, x, z, width, depth, accent, use):
        # Floor and walls: walkable inside; 1.8 m central doorway can open/close.
        add(name, "platform", x, -.11, z, width, .14, depth, accent)
        h = 2.45
        add(f"Pared fondo · {name}", "box", x, 0, z-depth/2, width, h, .17, "#7897AC")
        for side in (-1, 1):
            add(f"Pared lateral {side} · {name}", "box",
                x+side*width/2, 0, z, .17, h, depth, "#7897AC")
            add(f"Frente lateral {side} · {name}", "box",
                x+side*(width+1.9)/4, 0, z+depth/2, (width-1.9)/2, h, .17, "#7897AC")
        add(f"Puerta · {name}", "box", x, 0, z+depth/2, 1.8, 2.2, .15, "#4B8AAC",
            interact("door", "Permite entrar o cerrar este espacio", True))
        add(f"Luz · {name}", "sphere", x, 2.03, z,
            .54, .54, .54, "#FFF2B1", interact("light", "Encender o apagar la iluminación de referencia", True))
        add(f"Pizarra · {name}", "box", x, .85, z-depth/2+.29,
            2.25, 1.3, .12, "#334155",
            interact("whiteboard", "Activar la pizarra y explicar el propósito del espacio"))
        if use in ("computers", "classroom", "reception"):
            # Furniture is solid. Monitors have true toggled state and color.
            for i in (-1, 1):
                desk_x = x + i*1.35
                desk_z = z + .45
                add(f"Mesa {i} · {name}", "box", desk_x, 0, desk_z, 1.12, .72, .68, "#B8966C")
                add(f"Computadora {i} · {name}", "box", desk_x, .78, desk_z-.2,
                    .55, .52, .12, "#314457",
                    interact("terminal", "Activar terminal de demostración para esta estación"))
        elif use == "science":
            add(f"Mesa de prácticas · {name}", "box", x, 0, z, 2.25, .8, .9, "#B8966C")
            add(f"Instrumento de laboratorio · {name}", "cylinder", x, .83, z,
                .27, .52, .27, "#65CBD3")
        elif use == "meeting":
            add(f"Mesa de reunión · {name}", "box", x, 0, z+.3, 2.4, .78, 1.15, "#B8966C")
            add(f"Pantalla de videoconferencia · {name}", "box", x, .9, z-depth/2+.42,
                2.0, 1.2, .18, "#314457",
                interact("terminal", "Activar pantalla de reunión local; no inicia llamadas reales"))
        elif use == "library":
            for i in (-1, 1):
                add(f"Estantería {i} · {name}", "box",
                    x+i*2.08, 0, z-1.35, .65, 1.75, .65, "#B58C61")
            add(f"Mesa de lectura · {name}", "box", x, 0, z+.45, 2.2, .74, .9, "#B8966C")

    for args in spaces:
        room(*args)
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
            "interactive_objects": sum(bool(o.get("interaction")) for o in objects),
            "limitations": [
                "Los salones son espacios abiertos con mesas y pantallas geométricas; no interiores fotorrealistas cerrados",
                "Las puertas, pizarras y terminales tienen estados funcionales; no se generan personas ni clases por esta operación",
                "El número de niveles aparece en geometría externa; no habilita ascensores ni escaleras",
            ]}
    return scene, plan
