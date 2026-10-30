"""Lectura limitada de documentos del espacio seguro de SKY, sin efectos."""
from io import BytesIO
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree as ET
from . import sky_safe_workspace as ws

LIMIT = 15000

def inspect(name):
    data=ws.file_bytes(name)
    ext=Path(name).suffix.lower()
    if ext in ws.TEXT_EXT:
        try: text=data[:LIMIT].decode("utf-8")
        except UnicodeDecodeError as e: raise ws.WorkspaceError("Texto no UTF-8.") from e
    elif ext in (".docx",".pptx",".xlsx"):
        chunks=[]
        total=0
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                parts=z.infolist()
                if len(parts)>100:raise ws.WorkspaceError("Documento con demasiadas partes.")
                selected=[p for p in parts if
                    (ext==".docx" and p.filename=="word/document.xml") or
                    (ext==".pptx" and re.fullmatch(r"ppt/slides/slide\d+\.xml",p.filename)) or
                    (ext==".xlsx" and (p.filename=="xl/sharedStrings.xml" or
                       re.fullmatch(r"xl/worksheets/sheet\d+\.xml",p.filename)))]
                selected.sort(key=lambda p:(0 if p.filename=="xl/sharedStrings.xml" else 1,p.filename))
                for part in selected:
                    total+=part.file_size
                    if part.file_size>2_000_000 or total>6_000_000:raise ws.WorkspaceError("Documento demasiado grande.")
                    raw=z.read(part)
                    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
                        raise ws.WorkspaceError("XML con entidades no admitido.")
                    root=ET.fromstring(raw)
                    chunks.extend(node.text for node in root.iter()
                                  if node.text and (node.tag.endswith("}t") or
                                      (ext==".xlsx" and node.tag.endswith("}v"))))
                    if sum(len(c) for c in chunks)>=LIMIT:break
        except (zipfile.BadZipFile, ET.ParseError, RuntimeError) as e:
            raise ws.WorkspaceError("Documento Office inválido.") from e
        text="\n".join(chunks)[:LIMIT]
    elif ext==".pdf":
        try:from pypdf import PdfReader
        except ImportError as e:raise ws.WorkspaceError("Lector PDF no instalado.") from e
        try:
            doc=PdfReader(BytesIO(data),strict=True)
            if doc.is_encrypted or len(doc.pages)>100:raise ws.WorkspaceError("PDF cifrado o muy extenso.")
            text=""
            for p in doc.pages:
                text+=(p.extract_text() or "")[:LIMIT-len(text)]
                if len(text)>=LIMIT:break
        except (ValueError,KeyError,TypeError,OverflowError) as e:
            raise ws.WorkspaceError("PDF inválido.") from e
    else:raise ws.WorkspaceError("Formato sin extracción.")
    return {"name":name,"format":ext.lstrip("."),"text":text[:LIMIT],
            "partial":True,"max_chars":LIMIT,"read_only":True,
            "external_services_called":False,"file_modified":False}
