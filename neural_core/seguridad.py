"""Chequeos estáticos defensivos básicos. NO reemplazan antivirus ni un escáner profesional."""
import hashlib
import re
import zipfile
from io import BytesIO

MAX_ARCHIVO = 12_000_000


def revisar_archivo(nombre, contenido):
    if len(contenido) > MAX_ARCHIVO:
        raise ValueError("Máximo 12 MB por archivo")
    sha256 = hashlib.sha256(contenido).hexdigest()
    avisos=[]
    lower=nombre.lower()
    if contenido[:2] == b'MZ' or contenido.startswith(b'\x7fELF'):
        avisos.append("Es un ejecutable: no lo ejecutes si no confías en su origen")
    if lower.endswith((".js", ".py", ".ps1", ".bat", ".sh", ".html", ".txt", ".env")):
        texto = contenido[:1_000_000].decode("utf-8", errors="replace")
        patrones = [
            (r"(?i)(password|api[_-]?key|token|secret)\s*[:=]\s*['\"][^'\"]{8,}", "Posible credencial incrustada"),
            (r"(?i)verify\s*=\s*False", "Validación TLS desactivada en código"),
            (r"(?i)(eval|exec)\s*\(", "Uso de ejecución dinámica; revisar el contexto"),
            (r"(?i)subprocess\.[A-Za-z_]+\(.*shell\s*=\s*True", "Subproceso con shell=True; validar entrada"),
        ]
        for patron, aviso in patrones:
            if re.search(patron, texto):
                avisos.append(aviso)
    if contenido.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(BytesIO(contenido)) as z:
                if len(z.infolist()) > 3000:
                    avisos.append("Archivo ZIP con demasiadas entradas")
                for item in z.infolist()[:3000]:
                    ruta=item.filename.replace('\\', '/')
                    if ruta.startswith('/') or '..' in ruta.split('/'):
                        avisos.append("ZIP contiene una ruta sospechosa: posible path traversal")
                        break
                if any(n.lower().endswith("vbaproject.bin") for n in z.namelist()):
                    avisos.append("Documento con macros VBA; revisar antes de abrir")
        except zipfile.BadZipFile:
            avisos.append("Firma ZIP presente pero archivo ilegible")
    return {"nombre": nombre[:160], "sha256": sha256, "bytes": len(contenido),
            "observaciones": list(dict.fromkeys(avisos)),
            "resultado": "Alertas heurísticas" if avisos else "Sin indicadores en estas reglas (no implica que sea seguro)"}
