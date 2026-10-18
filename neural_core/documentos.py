"""Extracción local de contenido: TXT, MD, PDF y DOCX."""
from io import BytesIO

def extraer_texto(nombre, datos):
    if len(datos) > 10*1024*1024:
        raise ValueError("Archivo máximo 10 MB")
    sufijo = nombre.lower().rsplit('.',1)[-1]
    if sufijo in ('txt', 'md'):
        return datos.decode('utf-8-sig', errors='replace')
    if sufijo == 'pdf':
        from pypdf import PdfReader
        lector = PdfReader(BytesIO(datos))
        if lector.is_encrypted:
            raise ValueError("PDF protegido por contraseña")
        return "\n".join((p.extract_text() or "") for p in lector.pages[:100])
    if sufijo == 'docx':
        from docx import Document
        d = Document(BytesIO(datos))
        return "\n".join(p.text for p in d.paragraphs)
    raise ValueError("Formato no permitido")
