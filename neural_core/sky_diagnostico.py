"""SKY v12.1 — Autodiagnóstico: qué funciona, qué falta y cómo arreglarlo.

    python sky_diagnostico.py          (o botón DIAG del HUD)
"""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _item(id_: str, nombre: str, ok: bool, detalle: str, solucion: str = '', importante: bool = True) -> dict:
    return {'id': id_, 'nombre': nombre, 'ok': bool(ok), 'detalle': detalle[:200],
            'solucion': '' if ok else solucion[:300], 'importante': importante}


def _modulo(nombre: str) -> bool:
    try:
        return importlib.util.find_spec(nombre) is not None
    except (ImportError, ValueError):
        return False


def revisar() -> list[dict]:
    r = []
    v = sys.version_info
    r.append(_item('python', 'Python', v >= (3, 10), f'{v.major}.{v.minor}.{v.micro}',
                   'Instalá Python 3.11 o 3.12 (el instalador de SKY lo hace).'))
    # Agente del equipo
    try:
        from .sky_voice_actions import local_agent_credentials
        from .dispositivos import call_device
        base, token = local_agent_credentials()
        st = call_device(base, token, 'status', timeout=3)
        r.append(_item('agente', 'Agente del equipo', True, f"{st.get('device')} · perfil {st.get('profile')} · v{st.get('version')}"))
    except Exception as exc:
        r.append(_item('agente', 'Agente del equipo', False, str(exc)[:120],
                       'Iniciá SKY completo (SKY_INICIAR.bat → 0) o python agente_dispositivo.py.'))
    # Cerebro local
    modelo = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=1.5) as resp:
            modelos = [m.get('name', '') for m in json.loads(resp.read(200_000)).get('models', [])]
        r.append(_item('ollama', 'Ollama (IA local)', True, f'{len(modelos)} modelo(s)'))
        tiene = any(m == modelo or m.split(':')[0] == modelo.split(':')[0] for m in modelos)
        r.append(_item('modelo', 'Modelo del cerebro', tiene, modelo if tiene else f'{modelo} no está descargado',
                       f'Ejecutá: ollama pull {modelo}'))
    except Exception:
        r.append(_item('ollama', 'Ollama (IA local)', False, 'no responde en 127.0.0.1:11434',
                       'Instalá Ollama (winget install Ollama.Ollama) y abrilo; luego: ollama pull ' + modelo))
    from .providers import local_only
    r.append(_item('privacidad', 'Modo 100 % local', local_only(), 'activo' if local_only() else 'la IA puede usar la nube',
                   'Poné SKY_LOCAL_ONLY=1 en .env si querés que nada salga del equipo.', importante=False))
    # Voz
    from . import sky_tts
    r.append(_item('piper', 'Voz natural (Piper)', sky_tts.disponible(),
                   'lista' if sky_tts.disponible() else 'no instalada',
                   'Ejecutá INSTALAR_SKY_WINDOWS.bat (descarga Piper y una voz en español).'))
    try:
        from .sky_stt_local import capabilities
        stt = capabilities()
        r.append(_item('stt', 'Escucha local (faster-whisper)', stt.get('available'),
                       'lista' if stt.get('available') else ('falta el modelo' if stt.get('installed') else 'faster-whisper no instalado'),
                       'Ejecutá INSTALAR_SKY_WINDOWS.bat o definí SKY_STT_MODEL_DIR con un modelo de faster-whisper.'))
    except Exception as exc:
        r.append(_item('stt', 'Escucha local (faster-whisper)', False, str(exc)[:100], 'pip install faster-whisper'))
    vosk = (RAIZ / 'modelos' / 'vosk-model-es').is_dir() and _modulo('vosk') and _modulo('sounddevice')
    r.append(_item('vosk', 'Manos libres en segundo plano (Vosk)', vosk, 'listo' if vosk else 'falta modelo o librerías',
                   'Ejecutá INSTALAR_SKY_WINDOWS.bat (descarga el modelo Vosk español).', importante=False))
    ffmpeg = bool(shutil.which('ffmpeg')) or _modulo('static_ffmpeg')
    r.append(_item('ffmpeg', 'FFmpeg (audio y video)', ffmpeg, 'disponible' if ffmpeg else 'no encontrado', 'pip install static-ffmpeg'))
    # Integraciones opcionales
    from . import sky_home_assistant as casa, sky_correo
    if casa.configurado():
        res = casa.resumen()
        r.append(_item('casa', 'Home Assistant', res.get('ok', False), f"{len(res.get('entidades', []))} entidades" if res.get('ok') else res.get('error', ''),
                       'Revisá SKY_HA_URL y SKY_HA_TOKEN.', importante=False))
    else:
        r.append(_item('casa', 'Home Assistant', False, 'no configurado', 'Opcional: SKY_HA_URL y SKY_HA_TOKEN en .env.', importante=False))
    r.append(_item('correo', 'Correo', sky_correo.configurado(), sky_correo.usuario() or 'no configurado',
                   'Opcional: SKY_MAIL_USER y SKY_MAIL_APP_PASSWORD (contraseña de aplicación) en .env.', importante=False))
    yt = bool(os.getenv('YOUTUBE_API_KEY') or os.getenv('GOOGLE_API_KEY'))
    r.append(_item('youtube', 'Reproductor interno de YouTube', yt, 'configurado' if yt else 'sin clave',
                   'Opcional: YOUTUBE_API_KEY en .env.', importante=False))
    r.append(_item('sistema', 'Sistema operativo', True, f'{platform.system()} {platform.release()}', importante=False))
    return r


def resumen(items: list[dict]) -> str:
    malos = [i for i in items if not i['ok'] and i['importante']]
    return 'Todo listo.' if not malos else f'{len(malos)} punto(s) por resolver: ' + ', '.join(i['nombre'] for i in malos) + '.'


def main() -> None:
    items = revisar()
    for i in items:
        marca = '✔' if i['ok'] else ('✖' if i['importante'] else '·')
        print(f"{marca} {i['nombre']:<38} {i['detalle']}")
        if i['solucion']:
            print(f"    → {i['solucion']}")
    print('\n' + resumen(items))


if __name__ == '__main__':
    main()
