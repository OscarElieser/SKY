"""Interpretación local de órdenes de archivos; jamás ejecuta ni da permisos."""
from __future__ import annotations
import json
import re
from . import sky_safe_workspace as workspace

FILE = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,90}\.(?:txt|md|csv|json|py|html|docx|xlsx|pptx|pdf)"
MAX_REQUEST=4000

def _parse(text):
    if not isinstance(text,str) or not 3<=len(text)<=MAX_REQUEST:
        return None
    t=re.sub(r"^\s*(?:(?:oye|hey|ok)\s+)?sky[\s,.:;!¡-]*","",text,flags=re.I).strip()
    rules=(
        ("create",rf"(?:crea|crear|genera|generar)\s+(?:un\s+|una\s+)?(?:archivo|documento|informe)\s+({FILE})\s+con\s+contenido\s*:\s*([\s\S]+)"),
        ("replace",rf"(?:reemplaza|reemplazar|sustituye|sustituir)\s+(?:el\s+)?(?:contenido\s+(?:de|del)\s+)?(?:archivo\s+)?({FILE})\s+(?:por|con)\s*:\s*([\s\S]+)"),
        ("append",rf"(?:anade|añade|agrega|agregar|anadir)\s+(?:texto\s+)?(?:al\s+|a\s+)?(?:archivo\s+)?({FILE})\s*:\s*([\s\S]+)"),
        ("rename",rf"(?:renombra|renombrar|cambia\s+el\s+nombre\s+de)\s+(?:el\s+)?(?:archivo\s+)?({FILE})\s+(?:a|por)\s+({FILE})"),
        ("trash",rf"(?:mueve|mover|envia|envía|enviar)\s+(?:el\s+)?(?:archivo\s+)?({FILE})\s+a\s+(?:la\s+)?papelera"),
        ("restore",rf"(?:restaura|restaurar|recupera|recuperar)\s+(?:el\s+)?(?:archivo\s+)?({FILE})\s+(?:de\s+la\s+papelera\s+)?(?:con\s+)?(?:id|identificador)\s+([a-fA-F0-9]{{32}})"),
    )
    for op,pat in rules:
        match=re.fullmatch(pat,t,flags=re.I)
        if not match:
            continue
        name=match.group(1)
        spec={"op":op,"name":name}
        if op in ("create","replace","append"):
            content=match.group(2).strip()
            if not content or len(content.encode("utf-8"))>workspace.MAX_TEXT:
                return None
            extension=name.rsplit(".",1)[-1].lower()
            if extension in ("docx","pptx","pdf"):
                spec["document"]={"kind":extension,"title":name.rsplit(".",1)[0],"content":content}
            elif extension=="xlsx":
                try:doc=json.loads(content)
                except (ValueError,TypeError):return None
                if not isinstance(doc,dict) or doc.get("kind")!="xlsx":
                    return None
                spec["document"]=doc
            else:
                spec["text"]=content
        if op=="rename":
            spec["new_name"]=match.group(2)
        if op=="restore":
            spec["trash_id"]=match.group(2).lower()
        try:
            return workspace._validate(spec)
        except (workspace.WorkspaceError,ValueError,TypeError):
            return None
    return None

def maybe_prepare(text, *, mode="chat"):
    """Sólo propuesta visible; el HUD debe obtener vista previa y aprobación."""
    if mode not in ("voz","chat"):
        return None
    spec=_parse(text)
    if spec is None:
        return None
    verb={"create":"crear","replace":"reemplazar","append":"añadir texto a",
          "rename":"renombrar","trash":"mover a papelera","restore":"restaurar"}[spec["op"]]
    return {"tipo":"safe_file_proposal",
            "mensaje":"Preparé una propuesta para "+verb+" "+spec["name"]+
                      " en el espacio seguro de SKY. No cambié ningún archivo. "+
                      "Revisá la vista previa y confirmá personalmente.",
            "propuesta_archivo":spec,"proveedor":"sky-files-local",
            "requiere_confirmacion":True,"accion_ejecutada":False,
            "scope":"private_sky_workspace_only"}
