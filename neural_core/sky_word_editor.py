"""Safe, visible writing inside an existing Microsoft Word document.

Only explicit owner commands are parsed. Writing uses Word COM, not Ctrl+V:
no clipboard changes and no chance of pasting into SKY's Chrome HUD. The owner
must confirm through SKY's existing API and local device-agent policy.
No automatic saving, overwriting, deleting or opening arbitrary files.
"""
from __future__ import annotations

import os
import re

MAX_CHARS = 6000
_WAKE = re.compile(r"^\s*(?:(?:oye|hey|ok)\s+)?sky[\s,;:¡!.-]*", re.I)
_WRITE = re.compile(
    r"^(?:escrib(?:i|í|e|a|ir)|redact(?:a|á|ar)|agreg(?:a|á|ar)|"
    r"añad(?:e|í|ir)|pon(?:e|é|er)?)\s+en\s+(?:microsoft\s+)?word"
    r"\s*(?:[:,;-]\s*|\s+(?:el\s+siguiente\s+texto|el\s+texto|"
    r"que\s+diga|lo\s+siguiente|este\s+texto)\s*[:;,-]?\s*)"
    r"(?P<texto>.+)$",
    re.I | re.S,
)
_OTHER = re.compile(r"^\s*(?:investigaci[oó]n|informe|tesis|monograf[ií]a|"
                    r"ensayo|investiga|investig[aá])\s+(?:sobre|acerca\s+de)\b", re.I)


def _clean_text(raw: str) -> str:
    return raw.strip().replace("\r\n", "\n").replace("\r", "\n")


def propuesta(orden: str) -> dict | None:
    """Return a device action, not a made-up 'completed document' message."""
    if not isinstance(orden, str) or len(orden) > MAX_CHARS + 200:
        return None
    cmd = _WAKE.sub("", orden, count=1).strip()
    match = _WRITE.fullmatch(cmd)
    if not match:
        return None
    content = _clean_text(match.group("texto"))
    if not (1 <= len(content) <= MAX_CHARS) or _OTHER.match(content):
        return None
    return {
        "action": "word_write",
        "params": {"text": content, "mode": "append"},
        "description": (
            f"Escribir {len(content)} caracteres en el único documento abierto "
            "de Microsoft Word (SKY no ordenará guardarlo)"
        ),
    }


def solicitud(orden: str) -> dict | None:
    p = propuesta(orden)
    if p is None:
        return None
    return {"tipo": "accion", "propuesta": p, "mensaje": p["description"],
            "proveedor": "sky-word-local"}


def validar_parametros(params: dict) -> str:
    """No alternate documents, hidden targets or arbitrary Word automation."""
    if not isinstance(params, dict) or set(params) != {"text", "mode"}:
        raise ValueError("Parámetros de escritura en Word no autorizados.")
    if params["mode"] != "append" or not isinstance(params["text"], str):
        raise ValueError("Solo se permite agregar texto explícito a Word.")
    text = _clean_text(params["text"])
    if not (1 <= len(text) <= MAX_CHARS):
        raise ValueError(f"Introducí entre 1 y {MAX_CHARS} caracteres.")
    return text


def escribir_documento_abierto(app, texto: str) -> dict:
    """Append only into one editable document; verify insertion by reading Word.

    This helper is also unit-tested without Windows or Microsoft Office.
    """
    if not bool(app.Visible):
        raise RuntimeError("Word no está visible: abrilo antes de escribir.")
    docs = app.Documents
    if int(docs.Count) != 1:
        raise RuntimeError(
            "Por seguridad, dejá abierto un solo documento en Word. "
            "SKY no escribirá en un documento ambiguo."
        )
    doc = app.ActiveDocument
    if bool(doc.ReadOnly) or int(doc.ProtectionType) != -1:
        raise RuntimeError("El documento está protegido o es de solo lectura.")
    before = str(doc.Content.Text)
    position = max(0, int(doc.Content.End) - 1)
    payload = ("\r" if before.strip("\r\n ") else "") + texto.replace("\n", "\r")
    try:
        app.Activate()
    except Exception:
        # COM works on the verified document even if Windows rejects focus.
        pass
    doc.Range(position, position).InsertAfter(payload)
    after = str(doc.Content.Text)
    if len(after) <= len(before) or payload not in after:
        raise RuntimeError(
            "Word recibió la orden, pero SKY no pudo comprobar el texto. "
            "Revisá el documento antes de reintentar."
        )
    return {
        "ok": True, "status": "VERIFIED", "characters": len(texto),
        "document": str(doc.Name)[:140],
        "save_requested": False,
        "message": (
            f"Comprobé {len(texto)} caracteres nuevos en «{str(doc.Name)[:100]}». "
            "SKY no ejecutó Guardar; Word puede tener autoguardado activo."
        ),
    }


def escribir_en_word(params: dict) -> dict:
    """Use existing, visible, desktop Word COM. Never start new Word instances."""
    text = validar_parametros(params)
    if os.name != "nt":
        raise RuntimeError("La edición directa en Word requiere Windows.")
    try:
        import pythoncom
        from win32com.client import GetActiveObject
    except ImportError as exc:
        raise RuntimeError(
            "Falta pywin32 en este entorno de SKY. "
            "No se realizó ninguna escritura."
        ) from exc
    pythoncom.CoInitialize()
    try:
        try:
            app = GetActiveObject("Word.Application")
        except Exception as exc:
            raise RuntimeError(
                "No encontré Microsoft Word abierto con un documento editable."
            ) from exc
        return escribir_documento_abierto(app, text)
    finally:
        pythoncom.CoUninitialize()
