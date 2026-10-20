"""Extracción local universal sin restricciones de contenido.

Soporta:
- Videos: MP4, MOV, AVI, MKV, WEBM (metadatos, resolución, FPS, duración).
- Audio / Música: MP3, WAV, OGG, M4A, FLAC, AAC (duración, canales, frecuencia).
- Documentos: PDF, DOCX, DOC, PPTX, XLSX, XLS, CSV, TSV, TXT, MD, RTF, JSON, XML, YAML.
- Código: Python, JS, TS, HTML, CSS, SQL, C++, Java, Rust, Go, etc.
- Imágenes: PNG, JPG, JPEG, WEBP, GIF, BMP, SVG.
- Archivos comprimidos: ZIP, TAR (exploración de estructura interna).
"""
from __future__ import annotations
import os, io, zipfile
from io import BytesIO
from typing import Dict, Any

def extraer_texto(nombre: str, datos: bytes) -> str:
    """Extrae texto, estructura y metadatos comprensivos de cualquier archivo sin restricciones."""
    sufijo = nombre.lower().rsplit('.', 1)[-1] if '.' in nombre else ''

    # 1. Archivos de Video
    if sufijo in ('mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv'):
        duracion_sec = 0.0
        res_txt = "Desconocida"
        fps = 0.0
        try:
            import cv2
            # Escribir temporalmente para que OpenCV inspeccione los streams
            temp_path = os.path.join(os.environ.get('TEMP', '.'), f"temp_probe_{os.getpid()}.{sufijo}")
            with open(temp_path, 'wb') as tf:
                tf.write(datos[:4*1024*1024]) # Primeros 4MB para cabecera rápida
            cap = cv2.VideoCapture(temp_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS) or 0
                frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                if w and h:
                    res_txt = f"{w}x{h}"
                if fps > 0 and frames > 0:
                    duracion_sec = round(frames / fps, 1)
                cap.release()
            try:
                os.remove(temp_path)
            except OSError:
                pass
        except Exception:
            pass
        
        peso_mb = round(len(datos) / (1024 * 1024), 2)
        minutos = int(duracion_sec // 60)
        segundos = int(duracion_sec % 60)
        tiempo_fmt = f"{minutos}:{segundos:02d}" if duracion_sec > 0 else "Calculando en reproductor"
        return f"[Archivo de Video: {nombre} | Formato: {sufijo.upper()} | Duración: {tiempo_fmt} | Resolución: {res_txt} | FPS: {fps:.1f} | Peso: {peso_mb} MB. SKY puede reproducir, procesar, cortar y editar este video conforme a tus instrucciones.]"

    # 2. Archivos de Audio y Música
    if sufijo in ('mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'wma'):
        duracion_sec = 0.0
        info_audio = ""
        if sufijo == 'wav':
            try:
                import wave
                with wave.open(BytesIO(datos), 'rb') as w:
                    canales = w.getnchannels()
                    tasa = w.getframerate()
                    frames = w.getnframes()
                    duracion_sec = round(frames / float(tasa), 1)
                    info_audio = f" | Canales: {canales} | Frecuencia: {tasa}Hz"
            except Exception:
                pass
        
        peso_mb = round(len(datos) / (1024 * 1024), 2)
        minutos = int(duracion_sec // 60)
        segundos = int(duracion_sec % 60)
        tiempo_fmt = f"{minutos}:{segundos:02d}" if duracion_sec > 0 else "Disponible para reproducción"
        return f"[Pista de Audio / Música: {nombre} | Formato: {sufijo.upper()} | Duración: {tiempo_fmt}{info_audio} | Peso: {peso_mb} MB. SKY puede transcribir, analizar letra, armonía o reproducir la pista directamente.]"

    # 3. Presentaciones PowerPoint (PPTX)
    if sufijo in ('pptx', 'ppt'):
        try:
            # Inspeccionar como archivo zip XML de PowerPoint
            with zipfile.ZipFile(BytesIO(datos)) as z:
                slides_txt = []
                for fname in sorted(z.namelist()):
                    if fname.startswith('ppt/slides/slide') and fname.endswith('.xml'):
                        xml_content = z.read(fname).decode('utf-8', errors='ignore')
                        # Extraer texto entre etiquetas <a:t>
                        import re
                        textos = re.findall(r'<a:t[^>]*>(.*?)</a:t>', xml_content)
                        if textos:
                            slide_num = fname.split('slide')[-1].split('.')[0]
                            slides_txt.append(f"--- Diapositiva {slide_num} ---\n" + "\n".join(textos))
                if slides_txt:
                    return f"[Presentación PowerPoint: {nombre} ({len(slides_txt)} diapositivas)]\n\n" + "\n\n".join(slides_txt)
        except Exception:
            pass

    # 4. Hojas de Cálculo Excel (XLSX, XLS) y Tablas CSV/TSV
    if sufijo in ('xlsx', 'xls'):
        try:
            import pandas as pd
            excel = pd.ExcelFile(BytesIO(datos))
            resumenes = [f"[Libro Excel: {nombre} | Hojas: {', '.join(excel.sheet_names)}]"]
            for hoja in excel.sheet_names[:10]:
                df = excel.parse(hoja)
                resumenes.append(f"--- Hoja '{hoja}' ({len(df)} filas x {len(df.columns)} columnas) ---")
                resumenes.append("Columnas: " + ", ".join(str(c) for c in df.columns))
                resumenes.append(df.head(60).to_string(index=False))
            return "\n\n".join(resumenes)
        except Exception as e_excel:
            return f"[Libro Excel: {nombre} (Lectura estructurada disponible en SQLite)]"

    if sufijo in ('csv', 'tsv'):
        try:
            import pandas as pd
            sep = '\t' if sufijo == 'tsv' else None
            df = pd.read_csv(BytesIO(datos), sep=sep, nrows=250)
            resumen = f"[Archivo CSV/TSV: {nombre} ({len(df)} filas x {len(df.columns)} columnas)]\n"
            resumen += "Columnas: " + ", ".join(str(c) for c in df.columns) + "\n\n"
            resumen += df.head(80).to_string(index=False)
            return resumen
        except Exception:
            return datos.decode('utf-8-sig', errors='replace')

    # 5. Documentos PDF
    if sufijo == 'pdf':
        try:
            from pypdf import PdfReader
            lector = PdfReader(BytesIO(datos))
            paginas = []
            for i, p in enumerate(lector.pages[:150]):
                txt = (p.extract_text() or "").strip()
                if txt:
                    paginas.append(f"--- Página {i+1} ---\n{txt}")
            res = "\n\n".join(paginas)
            return res if res.strip() else f"[Documento PDF: {nombre} (sin texto digital embebido)]"
        except Exception as e_pdf:
            return f"[Documento PDF: {nombre} ({round(len(datos)/1024, 1)} KB)]"

    # 6. Documentos Microsoft Word (DOCX)
    if sufijo == 'docx':
        try:
            from docx import Document
            d = Document(BytesIO(datos))
            partes = [p.text for p in d.paragraphs if p.text.strip()]
            for t in d.tables:
                filas_texto = []
                for row in t.rows:
                    celdas = [c.text.strip() for c in row.cells]
                    filas_texto.append(" | ".join(celdas))
                if filas_texto:
                    partes.append("\n[Tabla en DOCX]:\n" + "\n".join(filas_texto))
            return "\n\n".join(partes)
        except Exception as e_docx:
            return f"[Documento DOCX: {nombre} ({round(len(datos)/1024, 1)} KB)]"

    # 7. Archivos comprimidos ZIP / TAR
    if sufijo in ('zip', 'tar', 'gz'):
        try:
            with zipfile.ZipFile(BytesIO(datos)) as z:
                archivos = z.namelist()
                return f"[Archivo Comprimido {sufijo.upper()}: {nombre} ({len(archivos)} archivos contenidos)]\nContenido:\n" + "\n".join(f"- {a}" for a in archivos[:80])
        except Exception:
            pass

    # 8. Archivos de Imagen (PNG, JPG, JPEG, WEBP, GIF, BMP, SVG)
    if sufijo in ('png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif', 'svg'):
        try:
            from PIL import Image
            im = Image.open(BytesIO(datos))
            ancho, alto = im.size
            formato = im.format or sufijo.upper()
            modo = im.mode
            peso_kb = round(len(datos) / 1024, 1)
            return f"[Imagen: {nombre} | Formato: {formato} | Resolución: {ancho}x{alto}px | Modo: {modo} | Tamaño: {peso_kb} KB]"
        except Exception:
            return f"[Archivo de Imagen: {nombre} ({round(len(datos)/1024, 1)} KB)]"

    # 9. Formatos de Texto, Código Fuente, Configuración
    formatos_texto = {
        'txt', 'md', 'markdown', 'rst', 'rtf', 'log', 'ini', 'env', 'conf', 'yaml', 'yml',
        'json', 'xml', 'html', 'htm', 'css', 'js', 'mjs', 'ts', 'jsx', 'tsx',
        'py', 'sql', 'sh', 'bat', 'cmd', 'ps1', 'c', 'cpp', 'h', 'hpp', 'java',
        'rs', 'go', 'php', 'rb', 'lua', 'r', 'dart', 'swift', 'kt', 'toml'
    }
    if sufijo in formatos_texto:
        try:
            return datos.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                return datos.decode('latin-1')
            except Exception:
                return datos.decode('utf-8', errors='replace')

    # 10. Fallback universal para cualquier binario o archivo desconocido
    try:
        texto = datos.decode('utf-8')
        caracteres_imprimibles = sum(1 for c in texto[:1000] if c.isprintable() or c in '\n\r\t')
        if caracteres_imprimibles / max(1, len(texto[:1000])) > 0.8:
            return texto
    except Exception:
        pass

    return f"[Archivo recibido: {nombre} | Tipo: {sufijo.upper() or 'Binario'} | Tamaño: {round(len(datos)/1024, 1)} KB. Listo para operaciones solicitadas por el usuario.]"
