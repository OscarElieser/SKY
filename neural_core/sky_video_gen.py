"""Generador de Video Autónomo de SKY IA (1, 3, 5, 8, 10 minutos).

Genera composiciones visuales MP4 fluidas a 12-24 fps con títulos cinemáticos,
ondas de gradiente armónico, sistemas de partículas dinámicas y cronómetro
en pantalla según la duración solicitada por el usuario.
"""
from __future__ import annotations
import os, time, math, secrets
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import cv2

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "local_data" / "sky_generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

DURACIONES_PERMITIDAS = [1, 3, 5, 8, 10]

def detectar_duracion_solicitada(texto: str) -> int:
    """Extrae la duración en minutos solicitada del texto (1, 3, 5, 8, 10)."""
    t = texto.lower()
    for d in [10, 8, 5, 3, 1]:
        if f"{d} min" in t or f"{d}min" in t:
            return d
    for d in [10, 8, 5, 3, 1]:
        if str(d) in t and "minuto" in t:
            return d
    return 1 # Por defecto 1 minuto

def generar_video_sky(prompt: str, minutos: Optional[int] = None, ancho: int = 854, alto: int = 480) -> Dict[str, Any]:
    """Genera un archivo MP4 real con la duración especificada (1, 3, 5, 8, 10 minutos)."""
    if minutos is None:
        minutos = detectar_duracion_solicitada(prompt)
    if minutos not in DURACIONES_PERMITIDAS:
        minutos = min(DURACIONES_PERMITIDAS, key=lambda x: abs(x - minutos))

    segundos_totales = minutos * 60
    fps = 12.0
    total_frames = int(segundos_totales * fps)

    # Identificador único de archivo
    token = secrets.token_hex(6)
    filename = f"sky_video_{minutos}m_{token}.mp4"
    filepath = GENERATED_DIR / filename

    # Inicializar escritor de video OpenCV
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(filepath), fourcc, fps, (ancho, alto))

    # Limpiar título para mostrar en pantalla
    titulo_limpio = prompt.strip()[:60]
    if len(titulo_limpio) > 35:
        linea1 = titulo_limpio[:35]
        linea2 = titulo_limpio[35:]
    else:
        linea1 = titulo_limpio
        linea2 = ""

    # Paleta de colores según tema
    p_lower = prompt.lower()
    if any(k in p_lower for k in ('cyberpunk', 'neon', 'futurista', 'robot')):
        c_base = (30, 10, 50)
        c_pulse = (220, 50, 160)
        tema = "CYBERPUNK NEON"
    elif any(k in p_lower for k in ('espacio', 'galaxia', 'universo', 'estrellas')):
        c_base = (25, 10, 15)
        c_pulse = (240, 180, 50)
        tema = "COSMIC SKY"
    elif any(k in p_lower for k in ('naturaleza', 'bosque', 'selva', 'verde')):
        c_base = (15, 35, 15)
        c_pulse = (80, 220, 120)
        tema = "NATURE HARMONY"
    else:
        c_base = (40, 20, 10)
        c_pulse = (240, 150, 40)
        tema = "SKY CORE NEURAL"

    # Pre-generar posiciones de estrellas/partículas
    num_particulas = 90
    particulas_x = np.random.randint(0, ancho, num_particulas)
    particulas_y = np.random.randint(0, alto, num_particulas)
    particulas_v = np.random.uniform(0.5, 3.0, num_particulas)

    # Optimización: generamos el bucle de fotogramas con variaciones cinemáticas periódicas
    for i in range(total_frames):
        t_seg = i / fps
        min_actual = int(t_seg // 60)
        seg_actual = int(t_seg % 60)

        # Fondo con onda de gradiente armónico
        frame = np.zeros((alto, ancho, 3), dtype=np.uint8)
        factor_onda = (math.sin(t_seg * 0.4) + 1.0) / 2.0
        r_actual = int(c_base[0] + (c_pulse[0] - c_base[0]) * factor_onda * 0.4)
        g_actual = int(c_base[1] + (c_pulse[1] - c_base[1]) * factor_onda * 0.4)
        b_actual = int(c_base[2] + (c_pulse[2] - c_base[2]) * factor_onda * 0.4)
        frame[:, :] = (b_actual, g_actual, r_actual)

        # Mover partículas/estrellas
        particulas_y = (particulas_y + particulas_v) % alto
        for px, py in zip(particulas_x[:45], particulas_y[:45]):
            cv2.circle(frame, (int(px), int(py)), 2, (230, 240, 255), -1)

        # Núcleo orbital central animado
        centro_x, centro_y = ancho // 2, (alto // 2) - 20
        radio_orbital = int(55 + 18 * math.sin(t_seg * 1.2))
        angulo = t_seg * 1.5
        orb_x = int(centro_x + radio_orbital * math.cos(angulo))
        orb_y = int(centro_y + radio_orbital * math.sin(angulo))
        
        # Anillos pulsantes
        cv2.circle(frame, (centro_x, centro_y), radio_orbital, (c_pulse[2]//2, c_pulse[1]//2, c_pulse[0]//2), 2)
        cv2.circle(frame, (centro_x, centro_y), int(radio_orbital * 0.6), (70, 160, 240), 1)
        cv2.circle(frame, (orb_x, orb_y), 7, (255, 255, 255), -1)
        cv2.circle(frame, (orb_x, orb_y), 12, (c_pulse[2], c_pulse[1], c_pulse[0]), 2)

        # Insignia de Marca SKY en esquina superior izquierda
        cv2.putText(frame, "✦ SKY IA · CORE CREATIVO", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (240, 240, 255), 2)
        cv2.putText(frame, f"TEMA: {tema}", (30, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 200, 255), 1)

        # Cronómetro en tiempo real (esquina superior derecha)
        tiempo_texto = f"{min_actual:02d}:{seg_actual:02d} / {minutos:02d}:00"
        cv2.putText(frame, tiempo_texto, (ancho - 180, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 250, 180), 2)

        # Título cinemático en tercio inferior
        cv2.putText(frame, linea1, (40, alto - 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        if linea2:
            cv2.putText(frame, linea2, (40, alto - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 230, 255), 2)
        cv2.putText(frame, f"Composicion de video generativa ({minutos} min) · Creado por SKY IA", (40, alto - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 180, 210), 1)

        out.write(frame)

    out.release()

    size_bytes = os.path.getsize(filepath)
    return {
        "ok": True,
        "filename": filename,
        "duration_minutes": minutos,
        "duration_seconds": segundos_totales,
        "fps": fps,
        "resolution": f"{ancho}x{alto}",
        "url": f"/api/media/generated/{filename}",
        "size_bytes": size_bytes,
        "prompt": prompt,
        "theme": tema
    }
