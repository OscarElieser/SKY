"""Integración oficial de IA.GRATIS para SKY IA.

Endpoints disponibles:
- Búsqueda web en vivo (/api/tools/search/)
- Generación de imágenes Flux (/api/tools/image/)
- Generación de video Kling / Veo 3 (/api/tools/video/)
- Síntesis de voz ElevenLabs (/api/tools/tts/)
- Transcripción Whisper (/api/tools/stt/)
- Chat multi-modelo (/api/tools/chat/)
"""
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

BASE_URL = "https://ia.gratis/api/tools"

def _headers() -> Dict[str, str]:
    token = os.getenv("IA_GRATIS_TOKEN", "").strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 SKY-IA/1.0"
    }

def buscar_web(query: str, num: int = 5) -> Dict[str, Any]:
    """Realiza una búsqueda web en vivo a través de ia.gratis."""
    url = f"{BASE_URL}/search/"
    data = json.dumps({"query": query, "num": num}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def generar_imagen(prompt: str, num_images: int = 1, size: str = "landscape_4_3") -> Dict[str, Any]:
    """Genera una imagen con modelos avanzados (Flux / Imagen 4) en ia.gratis."""
    url = f"{BASE_URL}/image/"
    data = json.dumps({
        "prompt": prompt,
        "num_images": num_images,
        "size": size,
        "model": "image_fast"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def texto_a_voz(texto: str, voz: str = "Rachel") -> Dict[str, Any]:
    """Convierte texto a voz con calidad ElevenLabs vía ia.gratis."""
    url = f"{BASE_URL}/tts/"
    data = json.dumps({"text": texto, "voice": voz}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
