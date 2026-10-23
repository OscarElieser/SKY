"""SKY v12.4 — Creación multimedia con APIs oficiales (sky-creative y sky-music).

    Imágenes        OpenAI Images API (OPENAI_API_KEY, OPENAI_IMAGE_MODEL) o Adobe Firefly Services
                    (FIREFLY_CLIENT_ID + FIREFLY_CLIENT_SECRET). Se guardan en ~/.neuralt/creaciones/imagenes.
    Presentaciones  Gamma API (GAMMA_API_KEY): SKY la crea en segundo plano y te avisa con el enlace.
                    Sin Gamma, el agente arma un .pptx local (tarea en segundo plano).
    Música          Suno no tiene API pública: SKY escribe letra, estructura, acordes y el «estilo» listo para
                    pegar en Suno u otra plataforma. Se guarda en ~/.neuralt/creaciones/musica.

Nada de esto se publica ni se comparte solo. Cada generación paga créditos del proveedor que elegiste.
"""
from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

MAX_IMAGEN = 25 * 1024 * 1024
_NOMBRE = re.compile(r'^[a-z0-9][a-z0-9_-]{0,80}\.(?:png|jpg|jpeg|webp|md)$')


def carpeta(tipo: str) -> Path:
    if tipo not in ('imagenes', 'musica', 'presentaciones'):
        raise ValueError('Tipo de creación inválido.')
    p = Path.home() / '.neuralt' / 'creaciones' / tipo
    p.mkdir(mode=0o700, parents=True, exist_ok=True)
    return p


def _slug(texto: str) -> str:
    s = unicodedata.normalize('NFD', str(texto).lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:40] or 'creacion'


def ruta_creacion(tipo: str, nombre: str) -> Path:
    if not _NOMBRE.fullmatch(nombre or ''):
        raise ValueError('Nombre de archivo inválido.')
    p = carpeta(tipo) / nombre
    if not p.is_file():
        raise FileNotFoundError(nombre)
    return p


def listar(tipo: str, limite: int = 30) -> list[dict]:
    archivos = sorted(carpeta(tipo).glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)
    return [{'nombre': p.name, 'bytes': p.stat().st_size,
             'fecha': datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds')}
            for p in archivos if _NOMBRE.fullmatch(p.name)][:limite]


def _json(url: str, cuerpo: dict | None = None, cabeceras: dict | None = None, datos: bytes | None = None,
          timeout: int = 120) -> dict:
    if cuerpo is not None:
        datos = json.dumps(cuerpo).encode('utf-8')
        cabeceras = {'Content-Type': 'application/json', **(cabeceras or {})}
    req = urllib.request.Request(url, data=datos, headers=cabeceras or {}, method='POST' if datos is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(MAX_IMAGEN * 2))


def _metrica(nombre: str, ok: bool, ms: float, detalle: str = '') -> None:
    try:
        from . import sky_metricas
        sky_metricas.registrar('accion', nombre, ok, ms, detalle=detalle)
    except Exception:
        pass


# ------------------------------------------------------------------ imágenes

def proveedor_imagen(preferido: str = '') -> str | None:
    disponibles = []
    if os.getenv('OPENAI_API_KEY', '').strip():
        disponibles.append('openai')
    if os.getenv('FIREFLY_CLIENT_ID', '').strip() and os.getenv('FIREFLY_CLIENT_SECRET', '').strip():
        disponibles.append('firefly')
    if preferido in disponibles:
        return preferido
    return disponibles[0] if disponibles else None


def _firefly_token() -> str:
    datos = urllib.parse.urlencode({'grant_type': 'client_credentials', 'client_id': os.environ['FIREFLY_CLIENT_ID'],
                                    'client_secret': os.environ['FIREFLY_CLIENT_SECRET'],
                                    'scope': os.getenv('FIREFLY_SCOPE', 'openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis')}).encode()
    r = _json('https://ims-na1.adobelogin.com/ims/token/v3', datos=datos,
              cabeceras={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=30)
    return r['access_token']


def generar_imagen(prompt: str, proveedor: str = '') -> dict:
    """Genera una imagen con la API oficial elegida y la guarda en tu PC. Devuelve {archivo, proveedor}."""
    from .sky_capacidades import parada_activa
    prompt = ' '.join(str(prompt or '').split())[:1500]
    if len(prompt) < 3:
        raise ValueError('Describime la imagen.')
    if parada_activa():
        raise RuntimeError('SKY está en parada de emergencia.')
    if os.getenv('SKY_LOCAL_ONLY', '0').strip() in ('1', 'true', 'si', 'yes'):
        raise RuntimeError('Modo 100 % local: generar imágenes usa una API en la nube y está desactivado.')
    prov = proveedor_imagen(proveedor)
    if not prov:
        raise RuntimeError('Para generar imágenes configurá OPENAI_API_KEY (OpenAI) o FIREFLY_CLIENT_ID y '
                           'FIREFLY_CLIENT_SECRET (Adobe Firefly Services) en .env.')
    inicio = time.perf_counter()
    try:
        if prov == 'openai':
            r = _json('https://api.openai.com/v1/images/generations',
                      {'model': os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-2'), 'prompt': prompt, 'n': 1,
                       'size': os.getenv('OPENAI_IMAGE_SIZE', '1024x1024')},
                      {'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY']})
            b64 = ((r.get('data') or [{}])[0]).get('b64_json')
            if not b64:
                raise RuntimeError('OpenAI no devolvió la imagen.')
            datos = base64.b64decode(b64)
        else:
            token = _firefly_token()
            r = _json('https://firefly-api.adobe.io/v3/images/generate', {'prompt': prompt, 'numVariations': 1},
                      {'X-Api-Key': os.environ['FIREFLY_CLIENT_ID'], 'Authorization': 'Bearer ' + token})
            url = (((r.get('outputs') or [{}])[0]).get('image') or {}).get('url', '')
            if not url.startswith('https://'):
                raise RuntimeError('Firefly no devolvió la imagen.')
            with urllib.request.urlopen(url, timeout=60) as resp:
                datos = resp.read(MAX_IMAGEN + 1)
        if len(datos) > MAX_IMAGEN or not (datos[:8] == b'\x89PNG\r\n\x1a\n' or datos[:3] == b'\xff\xd8\xff' or datos[8:12] == b'WEBP'):
            raise RuntimeError('El archivo recibido no es una imagen válida.')
    except urllib.error.HTTPError as exc:
        _metrica('generar_imagen', False, (time.perf_counter() - inicio) * 1000, f'{prov} HTTP {exc.code}')
        raise RuntimeError(f'{prov} rechazó la solicitud (HTTP {exc.code}). Revisá la clave, el saldo o el modelo.') from exc
    except Exception as exc:
        _metrica('generar_imagen', False, (time.perf_counter() - inicio) * 1000, str(exc)[:120])
        raise
    ext = 'png' if datos[:4] == b'\x89PNG' else 'jpg' if datos[:3] == b'\xff\xd8\xff' else 'webp'
    nombre = f"{datetime.now():%Y%m%d-%H%M%S}-{_slug(prompt)}.{ext}"
    destino = carpeta('imagenes') / nombre
    destino.write_bytes(datos)
    _metrica('generar_imagen', True, (time.perf_counter() - inicio) * 1000, prov)
    return {'archivo': nombre, 'proveedor': prov, 'ruta': str(destino), 'prompt': prompt}


# ------------------------------------------------------------------ presentaciones con Gamma

GAMMA = 'https://public-api.gamma.app/v1.0'


def crear_presentacion_gamma(tema: str, tarjetas: int = 10, esperar: bool = False, al_terminar=None) -> dict:
    """Pide a Gamma una presentación. Gamma trabaja en segundo plano: SKY consulta el estado y avisa con el enlace."""
    clave = os.getenv('GAMMA_API_KEY', '').strip()
    if not clave:
        raise RuntimeError('Configurá GAMMA_API_KEY en .env (planes Pro o superiores de Gamma).')
    if os.getenv('SKY_LOCAL_ONLY', '0').strip() in ('1', 'true', 'si', 'yes'):
        raise RuntimeError('Modo 100 % local: Gamma es un servicio en la nube y está desactivado.')
    tema = ' '.join(str(tema or '').split())[:4000]
    if len(tema) < 3:
        raise ValueError('¿Sobre qué querés la presentación?')
    r = _json(f'{GAMMA}/generations', {'inputText': tema, 'format': 'presentation', 'numCards': max(1, min(int(tarjetas), 30)),
                                       'textMode': 'generate', 'exportAs': 'pptx'},
              {'X-API-KEY': clave}, timeout=60)
    gid = str(r.get('generationId') or r.get('id') or '')
    if not re.fullmatch(r'[\w-]{4,80}', gid):
        raise RuntimeError('Gamma no devolvió un identificador de generación.')

    def seguir():
        resultado = {'generationId': gid, 'estado': 'pendiente'}
        for _ in range(60):                       # hasta ~5 minutos
            time.sleep(5)
            try:
                e = _json(f'{GAMMA}/generations/{gid}', cabeceras={'X-API-KEY': clave}, timeout=30)
            except Exception:
                continue
            estado = str(e.get('status', '')).lower()
            if estado in ('completed', 'complete', 'done', 'succeeded'):
                resultado = {'generationId': gid, 'estado': 'lista', 'url': e.get('gammaUrl', ''), 'exportar': e.get('exportUrl', '')}
                break
            if estado in ('failed', 'error'):
                resultado = {'generationId': gid, 'estado': 'error', 'error': str(e.get('error', ''))[:200]}
                break
        _metrica('presentacion_gamma', resultado['estado'] == 'lista', None, resultado.get('error', ''))
        _guardar_gamma(tema, resultado)
        if al_terminar:
            al_terminar(resultado)
        return resultado

    if esperar:
        return seguir()
    threading.Thread(target=seguir, daemon=True).start()
    return {'generationId': gid, 'estado': 'en_proceso'}


def _guardar_gamma(tema: str, resultado: dict) -> None:
    nombre = f"{datetime.now():%Y%m%d-%H%M%S}-{_slug(tema)}.md"
    (carpeta('presentaciones') / nombre).write_text(
        f"# Presentación: {tema[:200]}\n\n- Estado: {resultado['estado']}\n- Gamma: {resultado.get('url', '')}\n"
        f"- Exportar (PPTX): {resultado.get('exportar', '')}\n", encoding='utf-8')


def avisar_presentacion(resultado: dict) -> None:
    from .sky_rutinas import avisar
    if resultado['estado'] == 'lista':
        texto = f"Tu presentación de Gamma está lista: {resultado.get('url', '')}"
    else:
        texto = 'Gamma no pudo terminar la presentación: ' + resultado.get('error', 'sin detalle')
    avisar(texto, 'creativo')
    try:
        from .sky_whatsapp import enviar_aviso
        enviar_aviso(texto)
    except Exception:
        pass


# ------------------------------------------------------------------ música (letras)

SISTEMA_MUSICA = ('Sos SKY, compositora. Escribís canciones originales en español (sin copiar letras existentes ni imitar '
                  'a un artista con nombre propio). Devolvé SOLO JSON válido con las claves: titulo, estilo (una línea con '
                  'género, tempo en BPM, instrumentos y voz, apta para pegar en una plataforma de música), estructura (lista '
                  'de secciones), letra (texto con [Verso 1], [Coro], [Verso 2], [Puente], [Coro]), acordes (progresión '
                  'sugerida por sección).')


def escribir_cancion(tema: str, estilo: str = '', proveedor: str = 'auto') -> dict:
    tema = ' '.join(str(tema or '').split())[:600]
    if len(tema) < 3:
        raise ValueError('¿Sobre qué querés la canción?')
    from .providers import reply
    mensajes = [{'role': 'system', 'content': SISTEMA_MUSICA},
                {'role': 'user', 'content': f'Tema: {tema}. Estilo deseado: {estilo or "el que mejor le quede"}.'}]
    inicio = time.perf_counter()
    crudo = str(reply(mensajes, proveedor, max_output_tokens=1500))
    m = re.search(r'\{.*\}', crudo, re.S)
    try:
        datos = json.loads(m.group(0)) if m else {}
    except ValueError:
        datos = {}
    if not datos.get('letra'):
        datos = {'titulo': tema[:60], 'estilo': estilo, 'estructura': [], 'letra': crudo.strip(), 'acordes': ''}
    titulo = str(datos.get('titulo') or tema)[:80]
    acordes = datos.get('acordes')
    if isinstance(acordes, dict):
        acordes = '\n'.join(f'- {k}: {v}' for k, v in acordes.items())
    md = (f"# {titulo}\n\n**Estilo:** {datos.get('estilo', '')}\n\n"
          f"**Estructura:** {', '.join(map(str, datos.get('estructura') or []))}\n\n"
          f"## Letra\n\n{datos.get('letra', '')}\n\n## Acordes\n\n{acordes or ''}\n\n"
          '---\nCreada por SKY. Para escucharla, pegá la letra y el estilo en tu plataforma de música (por ejemplo, Suno).\n')
    nombre = f"{datetime.now():%Y%m%d-%H%M%S}-{_slug(titulo)}.md"
    (carpeta('musica') / nombre).write_text(md, encoding='utf-8')
    _metrica('escribir_cancion', True, (time.perf_counter() - inicio) * 1000)
    return {'archivo': nombre, 'titulo': titulo, 'estilo': datos.get('estilo', ''), 'letra': datos.get('letra', '')}
