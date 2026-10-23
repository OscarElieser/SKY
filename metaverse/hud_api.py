"""SKY v12 — API de la interfaz HUD (sólo el dueño, con su llave y 2FA si está activo).

    GET  /api/hud/estado      agente, motor de IA (local/nube), Home Assistant, voz local, versión
    GET  /api/hud/acciones    registro verificable de acciones del agente
    GET  /api/hud/tareas      tareas en segundo plano del agente
    GET  /api/hud/notas       nombres de tus notas locales (sólo lectura)
    GET  /api/hud/casa        entidades de Home Assistant (sin token)
    GET  /api/hud/youtube?q=  video incrustable vía YouTube Data API oficial (si hay YOUTUBE_API_KEY)
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from .api import require_key
from neural_core import dispositivos
from neural_core.sky_asistente_personal import token_agente_local, url_agente_local

router = APIRouter(prefix='/api/hud', dependencies=[Depends(require_key)])
VERSION_SKY = '12.0.0'


def _credenciales() -> tuple[str, str]:
    try:
        from neural_core.sky_voice_actions import local_agent_credentials
        return local_agent_credentials()
    except Exception:
        return url_agente_local(), token_agente_local()


def _get_agente(ruta: str) -> dict:
    base, token = _credenciales()
    if len(token) < 32:
        raise RuntimeError('Agente no iniciado')
    req = urllib.request.Request(base + ruta, headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read(262_144))


def _ollama() -> dict:
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=0.8) as resp:
            modelos = [m.get('name', '') for m in json.loads(resp.read(200_000)).get('models', [])][:20]
            return {'activo': True, 'modelos': modelos}
    except Exception:
        return {'activo': False, 'modelos': []}


@router.get('/estado')
def estado():
    from neural_core.providers import choose_provider, local_only
    from neural_core import sky_home_assistant as casa
    try:
        agente = {'ok': True, **dispositivos.call_device(*_credenciales(), 'status', timeout=3)}
    except Exception as exc:
        agente = {'ok': False, 'error': str(exc)[:160]}
    try:
        nombre, modelo = choose_provider('auto')
        ia = {'proveedor': nombre, 'modelo': modelo}
    except Exception as exc:
        ia = {'proveedor': None, 'error': str(exc)[:160]}
    ia['solo_local'] = local_only()
    ia['ollama'] = _ollama()
    ia['local'] = ia.get('proveedor') == 'ollama'
    try:
        from neural_core.sky_stt_local import capabilities as stt_caps
        stt = {'disponible': bool(stt_caps().get('available'))}
    except Exception:
        stt = {'disponible': False}
    return {'version': VERSION_SKY, 'agente': agente, 'ia': ia, 'stt_local': stt,
            'casa': {'configurado': casa.configurado()},
            'youtube_api': bool(os.getenv('YOUTUBE_API_KEY') or os.getenv('GOOGLE_API_KEY'))}


@router.get('/acciones')
def acciones():
    try:
        filas = _get_agente('/actions_history').get('actions', [])
    except Exception:
        return {'acciones': []}
    # El ledger guarda una línea por cambio de estado: quedarse con el último de cada orden.
    ultimo: dict = {}
    for f in filas:
        if isinstance(f, dict):
            ultimo[f.get('command_id') or id(f)] = {k: f.get(k) for k in ('command_id', 'action', 'target', 'status', 'created_at', 'error')}
    return {'acciones': list(reversed(list(ultimo.values())))[:30]}


@router.get('/tareas')
def tareas():
    try:
        return {'tareas': _get_agente('/tasks').get('tasks', [])[:12]}
    except Exception:
        return {'tareas': []}


@router.get('/notas')
def notas():
    from neural_core.sky_notes_local import notes_root
    try:
        raiz = notes_root()
        items = sorted((p for p in raiz.glob('*.txt') if p.is_file() and not p.is_symlink()),
                       key=lambda p: p.stat().st_mtime, reverse=True)[:40]
        return {'notas': [{'nombre': p.stem, 'bytes': p.stat().st_size} for p in items]}
    except Exception:
        return {'notas': []}


@router.get('/casa')
def casa_estado():
    from neural_core import sky_home_assistant as casa
    return casa.resumen()


@router.get('/youtube')
def youtube(q: str):
    q = ' '.join(str(q).split())[:120]
    if not q:
        raise HTTPException(400, 'Consulta vacía')
    clave = os.getenv('YOUTUBE_API_KEY') or os.getenv('GOOGLE_API_KEY')
    busqueda = 'https://www.youtube.com/results?search_query=' + urllib.request.quote(q)
    if not clave:
        return {'embebible': False, 'busqueda': busqueda,
                'motivo': 'Agregá YOUTUBE_API_KEY en .env para reproducir dentro de SKY.'}
    from neural_core.multimedia import _search_youtube_api
    try:
        candidatos = _search_youtube_api(q, clave)
    except Exception:
        candidatos = []
    candidatos = [c for c in candidatos if re.fullmatch(r'[A-Za-z0-9_-]{11}', c.get('id', ''))]
    if not candidatos:
        return {'embebible': False, 'busqueda': busqueda, 'motivo': 'Sin resultados incrustables.'}
    return {'embebible': True, 'busqueda': busqueda,
            'videos': [{'id': c['id'], 'titulo': str(c.get('title', ''))[:140]} for c in candidatos[:6]]}
