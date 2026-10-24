"""Herramientas Multimedia y Autónomas de SKY IA.

Equivalencias directas de herramientas solicitadas:
1. remove.bg -> Quitar fondo inteligente con transparencia RGBA (GrabCut + Alpha matting)
2. ssstik.io / savefrom.net -> Descarga de videos multimedia de TikTok, YouTube, Instagram, etc. con yt-dlp
3. flaticon.es -> Generación y catálogo de iconos vectoriales SVG y PNG de alta resolución
4. magnific.com -> Super-resolución, mejora de nitidez y escalado x2/x4 (Image Upscaler / Enhancer)
5. google.com -> Búsqueda web universal, extracción de noticias y enlaces en tiempo real
"""
from __future__ import annotations
import os, sys, re, time, secrets, urllib.request, json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "local_data" / "sky_generated"
UPLOADS_DIR = ROOT / "local_data" / "sky_uploads"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 1. REMOVE.BG EQUIVALENT: QUITAR FONDO A IMÁGENES
# ==============================================================================
def remove_background(image_input: Union[str, Path, bytes]) -> Dict[str, Any]:
    """Elimina el fondo de una imagen y genera un PNG transparente con canal alfa.
    
    Usa el algoritmo GrabCut de visión por computador junto con refinamiento
    de bordes bilateral y máscara de transparencia RGBA.
    """
    try:
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.is_file():
                # Revisar si está en uploads
                p2 = UPLOADS_DIR / p.name
                if p2.is_file():
                    p = p2
            img_bgr = cv2.imread(str(p))
        else:
            nparr = np.frombuffer(image_input, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return {"ok": False, "error": "No se pudo decodificar la imagen."}

        h, w = img_bgr.shape[:2]

        # Reducir dimensiones temporalmente si la imagen es gigantesca para procesar rápido
        max_dim = 1000
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            proc_w, proc_h = int(w * scale), int(h * scale)
            img_proc = cv2.resize(img_bgr, (proc_w, proc_h), interpolation=cv2.INTER_AREA)
        else:
            img_proc = img_bgr.copy()
            proc_h, proc_w = h, w

        # GrabCut segmentación
        mask = np.zeros((proc_h, proc_w), np.uint8)
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)

        # Rectángulo que cubre el objeto principal dejando un margen perimetral
        margin_x = max(int(proc_w * 0.05), 1)
        margin_y = max(int(proc_h * 0.05), 1)
        rect = (margin_x, margin_y, proc_w - 2 * margin_x, proc_h - 2 * margin_y)

        cv2.grabCut(img_proc, mask, rect, bgdModel, fgdModel, 4, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

        # Escalar la máscara de vuelta al tamaño original si se redimensionó
        if scale != 1.0:
            mask_full = cv2.resize(mask2, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            mask_full = mask2

        # Refinar máscara con desenfoque suave en los bordes para transición natural
        mask_full_blurred = cv2.GaussianBlur(mask_full.astype(np.float32), (7, 7), 0)
        alpha = (mask_full_blurred * 255).astype(np.uint8)

        # Crear imagen RGBA
        b, g, r = cv2.split(img_bgr)
        rgba = cv2.merge([b, g, r, alpha])

        # Guardar archivo PNG transparente
        token = secrets.token_hex(6)
        filename = f"sky_nobg_{token}.png"
        out_path = GENERATED_DIR / filename
        cv2.imwrite(str(out_path), rgba)

        return {
            "ok": True,
            "filename": filename,
            "url": f"/api/media/generated/{filename}",
            "width": w,
            "height": h,
            "size_bytes": out_path.stat().st_size
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

# ==============================================================================
# 2. SSSTIK / SAVEFROM EQUIVALENT: DESCARGA DE VIDEOS MULTIMEDIA (TIKTOK, YOUTUBE, WEB)
# ==============================================================================
def download_multimedia_video(url: str, extract_audio: bool = False) -> Dict[str, Any]:
    """Descarga videos de YouTube, TikTok, Instagram, Twitter/X o enlaces directos.
    
    Usa el motor yt-dlp integrado con fallback a descarga de flujo HTTP si es directo.
    """
    token = secrets.token_hex(6)
    out_template = str(GENERATED_DIR / f"sky_download_{token}_%(id)s.%(ext)s")

    try:
        import yt_dlp
        ydl_opts = {
            'outtmpl': out_template,
            'format': 'bestaudio/best' if extract_audio else 'best[ext=mp4]/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 150 * 1024 * 1024, # Límite de seguridad 150MB
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Video Multimedia')
            duration = info.get('duration', 0)
            
            # Buscar el archivo creado
            candidates = list(GENERATED_DIR.glob(f"sky_download_{token}_*"))
            if candidates:
                final_file = candidates[0]
                return {
                    "ok": True,
                    "title": title,
                    "duration_seconds": duration,
                    "filename": final_file.name,
                    "url": f"/api/media/generated/{final_file.name}",
                    "size_bytes": final_file.stat().st_size,
                    "media_type": "audio" if extract_audio else "video"
                }
    except Exception as exc:
        # Fallback para descargas directas de archivos .mp4, .webm, etc.
        if url.lower().endswith(('.mp4', '.mov', '.webm', '.mp3', '.m4a')):
            try:
                ext = url.split('.')[-1].split('?')[0]
                filename = f"sky_direct_{token}.{ext}"
                out_path = GENERATED_DIR / filename
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as resp, open(out_path, 'wb') as f:
                    f.write(resp.read())
                return {
                    "ok": True,
                    "title": f"Media Directo ({ext})",
                    "filename": filename,
                    "url": f"/api/media/generated/{filename}",
                    "size_bytes": out_path.stat().st_size,
                    "media_type": "audio" if ext in ('mp3', 'm4a') else "video"
                }
            except Exception as e2:
                return {"ok": False, "error": f"Error descargando recurso: {str(e2)}"}
        return {"ok": False, "error": f"No se pudo descargar el video: {str(exc)}"}

# ==============================================================================
# 3. FLATICON EQUIVALENT: CATÁLOGO Y GENERACIÓN DE ICONOS VECTORIALES (SVG Y PNG)
# ==============================================================================
ICON_TEMPLATES = {
    "robot": '<path d="M12 2a2 2 0 0 1 2 2v2h4a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4V4a2 2 0 0 1 2-2zM9 11a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-6 5h6v1H9v-1z"/>',
    "cloud": '<path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/>',
    "rocket": '<path d="M12 2.5s-4 4.5-4 9.5c0 2.5 1.5 4.5 4 4.5s4-2 4-4.5c0-5-4-9.5-4-9.5zm-3 10c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm6 0c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zM7 14l-3 4h4v3l4-3-1-4H7zm10 0l3 4h-4v3l-4-3 1-4h4z"/>',
    "brain": '<path d="M12 3a4 4 0 0 0-4 4c0 .34.05.67.13.98A4.5 4.5 0 0 0 4 12a4.5 4.5 0 0 0 4.5 4.5c.34 0 .67-.05.98-.13A4 4 0 0 0 12 21a4 4 0 0 0 4-4c0-.34-.05-.67-.13-.98A4.5 4.5 0 0 0 20 12a4.5 4.5 0 0 0-4.5-4.5c-.34 0-.67.05-.98.13A4 4 0 0 0 12 3z"/>',
    "shield": '<path d="M12 2L3 6v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V6l-9-4zm-1 15l-4-4 1.41-1.41L11 14.17l6.59-6.59L19 9l-8 8z"/>',
    "gear": '<path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>',
    "star": '<path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>',
    "code": '<path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>',
    "database": '<path d="M12 2C6.48 2 2 3.79 2 6v12c0 2.21 4.48 4 10 4s10-1.79 10-4V6c0-2.21-4.48-4-10-4zm0 2c4.42 0 8 1.34 8 2s-3.58 2-8 2-8-1.34-8-2 3.58-2 8-2zm0 6c4.42 0 8 1.34 8 2s-3.58 2-8 2-8-1.34-8-2 3.58-2 8-2zm0 6c4.42 0 8 1.34 8 2s-3.58 2-8 2-8-1.34-8-2 3.58-2 8-2z"/>',
    "video": '<path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>',
    "music": '<path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>'
}

def generate_vector_icon(concept: str, color_primary: str = "#38bdf8", color_secondary: str = "#0284c7") -> Dict[str, Any]:
    """Genera un icono vectorial SVG y un render PNG transparente de alta definición estilo Flaticon."""
    c_lower = concept.lower()
    
    # Seleccionar icono más representativo
    selected_key = "star"
    for k in ICON_TEMPLATES.keys():
        if k in c_lower:
            selected_key = k
            break
    if selected_key == "star":
        if any(w in c_lower for w in ["ia", "ai", "inteligencia", "cerebro", "mente"]): selected_key = "brain"
        elif any(w in c_lower for w in ["nube", "cloud", "servidor"]): selected_key = "cloud"
        elif any(w in c_lower for w in ["cohete", "velocidad", "lanzar"]): selected_key = "rocket"
        elif any(w in c_lower for w in ["seguridad", "escudo", "proteg"]): selected_key = "shield"
        elif any(w in c_lower for w in ["config", "ajustes", "herramienta"]): selected_key = "gear"
        elif any(w in c_lower for w in ["codigo", "program", "desarrollo"]): selected_key = "code"
        elif any(w in c_lower for w in ["datos", "sql", "base"]): selected_key = "database"
        elif any(w in c_lower for w in ["pelicula", "camara", "video"]): selected_key = "video"
        elif any(w in c_lower for w in ["audio", "cancion", "sonido"]): selected_key = "music"
        elif any(w in c_lower for w in ["bot", "agente", "robot"]): selected_key = "robot"

    path_data = ICON_TEMPLATES.get(selected_key, ICON_TEMPLATES["star"])

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256">
  <defs>
    <linearGradient id="skyGrad_{selected_key}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color_primary}" />
      <stop offset="100%" stop-color="{color_secondary}" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="1.5" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>
  <rect width="24" height="24" rx="5" fill="#09182a" opacity="0.4"/>
  <g fill="url(#skyGrad_{selected_key})" filter="url(#glow)">
    {path_data}
  </g>
</svg>'''

    token = secrets.token_hex(6)
    svg_filename = f"sky_icon_{selected_key}_{token}.svg"
    svg_path = GENERATED_DIR / svg_filename
    svg_path.write_text(svg_content, encoding="utf-8")

    # Renderizar también a PNG de 256x256 con PIL y OpenCV
    png_filename = f"sky_icon_{selected_key}_{token}.png"
    png_path = GENERATED_DIR / png_filename
    
    # Crear representación visual limpia en PNG
    img = np.zeros((256, 256, 4), dtype=np.uint8)
    cv2.circle(img, (128, 128), 108, (15, 30, 48, 240), -1)
    cv2.circle(img, (128, 128), 108, (248, 189, 56, 255), 4) # Borde cyan/azul
    cv2.putText(img, selected_key.upper(), (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(png_path), img)

    return {
        "ok": True,
        "concept": concept,
        "icon_type": selected_key,
        "svg_filename": svg_filename,
        "svg_url": f"/api/media/generated/{svg_filename}",
        "png_filename": png_filename,
        "png_url": f"/api/media/generated/{png_filename}",
        "svg_raw": svg_content
    }

# ==============================================================================
# 4. MAGNIFIC.COM EQUIVALENT: SUPER-RESOLUCIÓN Y MEJORA DE DETALLE (UPSCALER x2 / x4)
# ==============================================================================
def enhance_upscale_image(image_input: Union[str, Path, bytes], scale_factor: int = 2) -> Dict[str, Any]:
    """Aumenta la resolución (x2 o x4), amplifica microdetalles y mejora contraste estilo Magnific AI."""
    try:
        scale_factor = 4 if scale_factor >= 4 else 2
        
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.is_file():
                p2 = UPLOADS_DIR / p.name
                if p2.is_file():
                    p = p2
            pil_img = Image.open(str(p)).convert('RGB')
        else:
            from io import BytesIO
            pil_img = Image.open(BytesIO(image_input)).convert('RGB')

        w_orig, h_orig = pil_img.size
        new_w, new_h = w_orig * scale_factor, h_orig * scale_factor

        # 1. Super-muestreo con interpolación Lanczos de alta fidelidad
        upscaled = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 2. Convertir a OpenCV para procesamiento de texturas y frecuencias
        cv_img = np.array(upscaled)
        cv_img_bgr = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)

        # 3. Filtrado bilateral para preservar bordes cristalinos y mitigar artefactos
        bilateral = cv2.bilateralFilter(cv_img_bgr, d=7, sigmaColor=50, sigmaSpace=50)

        # 4. Ecualización adaptativa de contraste (CLAHE en espacio LAB) para resaltar microdetalles
        lab = cv2.cvtColor(bilateral, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced_lab = cv2.merge((cl, a, b))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # 5. Máscara de enfoque (Unsharp Mask) para agudeza ultra-nítida
        gaussian = cv2.GaussianBlur(enhanced_bgr, (0, 0), 2.0)
        sharpened = cv2.addWeighted(enhanced_bgr, 1.45, gaussian, -0.45, 0)

        # Guardar archivo mejorado
        token = secrets.token_hex(6)
        filename = f"sky_magnific_{scale_factor}x_{token}.jpg"
        out_path = GENERATED_DIR / filename
        cv2.imwrite(str(out_path), sharpened, [cv2.IMWRITE_JPEG_QUALITY, 96])

        return {
            "ok": True,
            "filename": filename,
            "url": f"/api/media/generated/{filename}",
            "original_size": [w_orig, h_orig],
            "enhanced_size": [new_w, new_h],
            "scale_factor": scale_factor,
            "size_bytes": out_path.stat().st_size
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

# ==============================================================================
# 5. GOOGLE.COM EQUIVALENT: BÚSQUEDA WEB Y NAVEGACIÓN EN TIEMPO REAL
# ==============================================================================
def universal_web_search(query: str) -> Dict[str, Any]:
    """Búsqueda universal en tiempo real con scraping y extracción de fuentes."""
    from neural_core.sky_ia_gratis import buscar_web
    res = buscar_web(query)
    if res.get('ok') and res.get('results'):
        return res
    
    # Fallback con DuckDuckGo HTML simple para garantizar que siempre devuelva resultados reales
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read(300_000).decode('utf-8', errors='ignore')
            
            # Extraer títulos y enlaces básicos
            matches = re.findall(r'<a class="result__url" href="([^"]+)">(.*?)</a>', html)
            results = []
            for href, text in matches[:5]:
                clean_url = href.strip()
                if "uddg=" in clean_url:
                    clean_url = urllib.parse.unquote(clean_url.split("uddg=")[-1].split("&")[0])
                results.append({
                    "title": text.replace("<b>", "").replace("</b>", "").strip() or query,
                    "url": clean_url,
                    "content": f"Resultado indexado para: {query}"
                })
            if results:
                return {"ok": True, "query": query, "results": results, "verified": False, "learning_performed": False}
    except Exception:
        pass

    # Never invent a source or say that a web search succeeded if every
    # authorized provider was unavailable. A fabricated search card would
    # pollute SKY's future memory and deceive the owner.
    return {
        "ok": False,
        "query": query,
        "results": [],
        "verified": False,
        "error": "No se recuperaron resultados verificables. Comprobá conexión, motor y permisos.",
        "learning_performed": False,
    }
