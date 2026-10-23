"""SKY v12.1 — Voz natural 100 % local con Piper (https://github.com/rhasspy/piper).

El instalador de SKY deja Piper y una voz en español en ~/.neuralt/piper. También:
    SKY_PIPER_BIN=C:\\ruta\\piper.exe
    SKY_PIPER_VOICE=C:\\ruta\\es_MX-claude-high.onnx   (junto a su .onnx.json)
    SKY_PIPER_SPEED=1.0     (más alto = más lento; 0.8–1.4)
Sin Piper, el HUD usa una voz del sistema marcada como local.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

BASE = Path.home() / '.neuralt' / 'piper'
MAX_CHARS = 700


def piper_bin() -> str | None:
    env = os.getenv('SKY_PIPER_BIN', '').strip()
    candidatos = [env] if env else []
    candidatos += [shutil.which('piper') or '', str(BASE / 'piper' / 'piper.exe'), str(BASE / 'piper.exe'),
                   str(BASE / 'piper' / 'piper'), str(BASE / 'piper')]
    for c in candidatos:
        if c and Path(c).is_file() and not Path(c).is_symlink():
            return c
    return None


def piper_voz() -> str | None:
    env = os.getenv('SKY_PIPER_VOICE', '').strip()
    if env:
        p = Path(env).expanduser()
        return str(p) if p.is_file() and Path(str(p) + '.json').is_file() else None
    carpeta = BASE / 'voces'
    if carpeta.is_dir():
        for p in sorted(carpeta.glob('*.onnx')):
            if Path(str(p) + '.json').is_file():
                return str(p)
    return None


def disponible() -> bool:
    return bool(piper_bin() and piper_voz())


def sintetizar(texto: str) -> bytes:
    """Devuelve audio WAV. Sin red ni shell: Piper recibe el texto por la entrada estándar."""
    texto = ' '.join(str(texto or '').split())[:MAX_CHARS]
    if not texto:
        raise ValueError('Texto vacío.')
    binario, voz = piper_bin(), piper_voz()
    if not binario or not voz:
        raise RuntimeError('Piper no está instalado. Ejecutá INSTALAR_SKY_WINDOWS.bat o configurá SKY_PIPER_BIN y SKY_PIPER_VOICE.')
    try:
        velocidad = max(0.6, min(1.6, float(os.getenv('SKY_PIPER_SPEED', '1.0'))))
    except ValueError:
        velocidad = 1.0
    with tempfile.TemporaryDirectory(prefix='sky_tts_') as tmp:
        salida = Path(tmp) / 'voz.wav'
        proc = subprocess.run([binario, '--model', voz, '--output_file', str(salida), '--length_scale', f'{velocidad:.2f}'],
                              input=texto.encode('utf-8'), capture_output=True, timeout=30, shell=False)
        if proc.returncode or not salida.is_file():
            raise RuntimeError('Piper no pudo generar la voz: ' + proc.stderr.decode('utf-8', 'replace')[-160:])
        return salida.read_bytes()
