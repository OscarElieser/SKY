"""Strict, version-safe actions on SKY scene objects; no arbitrary scripting."""
from __future__ import annotations

from .engine import validate_object

COLORS = {
    "terminal": ("#314457", "#62DCE2"),
    "whiteboard": ("#334155", "#7ED3F7"),
    "light": ("#516171", "#FFF2B1"),
    "door": ("#4B8AAC", "#4B8AAC"),
}


def interact(scene: dict, object_id: str, action: str = "toggle",
             content: str = "") -> tuple[dict, dict]:
    if not isinstance(object_id, str) or not 1 <= len(object_id) <= 64:
        raise ValueError("ID de objeto inválido")
    if action not in {"toggle", "write"}:
        raise ValueError("Acción no permitida")
    if not isinstance(scene, dict) or not isinstance(scene.get("objects"), list):
        raise ValueError("Escena inválida")
    if not isinstance(content, str) or len(content) > 1200:
        raise ValueError("Contenido de interacción inválido")
    changed = []
    event = None
    for raw in scene["objects"]:
        obj = validate_object(raw)
        interaction = obj.get("interaction")
        if obj["id"] == object_id:
            if not interaction or interaction["type"] not in COLORS:
                raise ValueError("El objeto seleccionado no es interactivo")
            if action == "write":
                if interaction["type"] != "whiteboard":
                    raise ValueError("Solo las pizarras pueden guardar texto")
                interaction["content"] = content
                interaction["active"] = True
            elif content:
                raise ValueError("Para escribir en la pizarra usá la acción write")
            else:
                interaction["active"] = not interaction["active"]
            obj["color"] = COLORS[interaction["type"]][
                1 if interaction["active"] else 0]
            event = {
                "object_id": obj["id"], "name": obj["name"],
                "interaction": interaction["type"],
                "active": interaction["active"],
                "description": interaction["description"],
                "message": (f'Pizarra «{obj["name"]}» actualizada' if action == "write" else
                            f'{obj["name"]}: {"activado/abierto" if interaction["active"] else "desactivado/cerrado"}'),
            }
            if interaction["type"] == "whiteboard":
                event["content"] = interaction.get("content", "")
        changed.append(obj)
    if event is None:
        raise KeyError("Objeto inexistente")
    return {**scene, "objects": changed}, event


def toggle(scene: dict, object_id: str) -> tuple[dict, dict]:
    """Backward compatible wrapper for existing SKY World API callers."""
    return interact(scene, object_id, "toggle")
