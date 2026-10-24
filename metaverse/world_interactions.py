"""Strict, version-safe actions on SKY scene objects; no arbitrary scripting."""
from __future__ import annotations

from .engine import validate_object

COLORS = {
    "terminal": ("#314457", "#62DCE2"),
    "whiteboard": ("#334155", "#7ED3F7"),
    "light": ("#516171", "#FFF2B1"),
    "door": ("#4B8AAC", "#4B8AAC"),
}

def toggle(scene: dict, object_id: str) -> tuple[dict, dict]:
    if not isinstance(object_id, str) or not 1 <= len(object_id) <= 64:
        raise ValueError("ID de objeto inválido")
    if not isinstance(scene, dict) or not isinstance(scene.get("objects"), list):
        raise ValueError("Escena inválida")
    changed = []
    event = None
    for raw in scene["objects"]:
        obj = validate_object(raw)
        interaction = obj.get("interaction")
        if obj["id"] == object_id:
            if not interaction or interaction["type"] not in COLORS:
                raise ValueError("El objeto seleccionado no es interactivo")
            next_state = not interaction["active"]
            interaction["active"] = next_state
            obj["color"] = COLORS[interaction["type"]][1 if next_state else 0]
            event = {
                "object_id": obj["id"], "name": obj["name"],
                "interaction": interaction["type"], "active": next_state,
                "description": interaction["description"],
                "message": f'{obj["name"]}: {"activado/abierto" if next_state else "desactivado/cerrado"}',
            }
        changed.append(obj)
    if event is None:
        raise KeyError("Objeto inexistente")
    return {**scene, "objects": changed}, event
