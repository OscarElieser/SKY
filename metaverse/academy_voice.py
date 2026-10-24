"""Adaptador docente por texto y voz para SKY Aula.

Los comandos explícitos de clase no activan herramientas del sistema,
no realizan grabaciones y no cambian las políticas de dispositivos.
"""
from __future__ import annotations
import re
import unicodedata


def _norm(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(text or "").casefold())
                   if not unicodedata.combining(c)).strip()


def class_command(text: str, *, lesson_id: str = "", source_text: str = "") -> dict | None:
    """Resuelve sólo solicitudes explícitas 'SKY, impartí ...' o 'SKY, siguiente paso'."""
    from neural_core import sky_aula
    txt = _norm(text)
    prefix = r"^(?:(?:oye|hey|ok)\s+)?sky[\s,;:!¡-]+"
    if re.fullmatch(prefix + r"(?:siguiente\s+(?:paso|momento)\s+(?:de\s+)?(?:la\s+)?clase|continua\s+(?:la\s+)?clase)\s*", txt):
        if not lesson_id:
            return {"tipo": "respuesta", "proveedor": "sky-aula", "atendido_por": "SKY",
                    "mensaje": "Indicá la sesión de tu clase o iniciá una nueva en SKY Aula."}
        try:
            stage = sky_aula.next_stage(lesson_id)
        except KeyError:
            return {"tipo": "respuesta", "proveedor": "sky-aula", "atendido_por": "SKY",
                    "mensaje": "La clase expiró o se cerró. Iniciá otra sesión."}
        msg = stage.get("step", {}).get("voice_ready_text") or "Clase finalizada."
        return {"tipo": "respuesta", "proveedor": "sky-aula", "atendido_por": "SKY",
                "mensaje": msg, "lesson_id": lesson_id, "academy": stage}
    expression = (prefix +
       r"(?:imparti|ensena|prepara|dame|inicia)\s+(?:una\s+)?clase\s+"
       r"(?:de|sobre)\s+(?P<topic>.{4,160}?)\s+(?:para\s+)?(?:nivel\s+)?"
       r"(?P<level>inicial|primaria|secundaria|media|tecnica|tecnico|"
       r"universitaria|universitario|maestria|doctorado)\s*")
    m = re.fullmatch(expression, txt)
    if not m:
        return None
    aliases = {"media": "secundaria", "tecnica": "tecnico", "universitaria": "universitario"}
    level = aliases.get(m.group("level"), m.group("level"))
    try:
        session = sky_aula.start(m.group("topic"), level,
                                 reference_text=source_text[:12000] if isinstance(source_text,str) else "")
    except (ValueError, RuntimeError) as exc:
        return {"tipo": "respuesta", "proveedor": "sky-aula", "atendido_por": "SKY",
                "mensaje": "No pude iniciar la clase: " + str(exc)[:180]}
    return {"tipo": "respuesta", "proveedor": "sky-aula", "atendido_por": "SKY",
            "mensaje": session["step"]["voice_ready_text"],
            "lesson_id": session["lesson_id"], "academy": session}
