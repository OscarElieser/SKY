"""SKY v12 — API de la interfaz HUD (sólo el dueño, con su llave y 2FA si está activo).

    GET  /api/hud/estado      agente, motor de IA (local/nube), Home Assistant, voz local, versión
    GET  /api/hud/acciones    registro verificable de acciones del agente
    GET  /api/hud/tareas      tareas en segundo plano del agente
    GET  /api/hud/notas       nombres de tus notas locales (sólo lectura)
    GET  /api/hud/casa        entidades de Home Assistant (sin token)
    GET  /api/hud/youtube?q=  video incrustable vía YouTube Data API oficial (si hay YOUTUBE_API_KEY)
    POST /api/hud/tts         voz natural local con Piper (WAV)
    GET  /api/hud/avisos      recordatorios y rutinas que el HUD debe decir (se marcan como vistos)
    GET  /api/hud/agenda      recordatorios pendientes y rutinas · DELETE /api/hud/agenda/{id}
    GET  /api/hud/diagnostico qué funciona, qué falta y cómo arreglarlo
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .api import require_key
from neural_core import dispositivos
from neural_core.sky_asistente_personal import token_agente_local, url_agente_local

router = APIRouter(prefix='/api/hud', dependencies=[Depends(require_key)])
VERSION_SKY = '12.5.0'


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
    from neural_core import sky_tts, sky_correo, sky_cerebro
    ia['cerebro'] = sky_cerebro.disponible()
    from neural_core.sky_unified_agents import capability_status
    ia['subagentes_cognitivos'] = capability_status()
    from neural_core.sky_social_hub import capabilities as social_capabilities
    from neural_core.providers import provider_summary
    ia['proveedores_sky'] = provider_summary()
    ia['redes_sociales'] = social_capabilities()
    return {'version': VERSION_SKY, 'agente': agente, 'ia': ia, 'stt_local': stt,
            'tts_local': sky_tts.disponible(), 'correo': sky_correo.configurado(),
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


class TextoVoz(BaseModel):
    texto: str = Field(min_length=1, max_length=700)


@router.post('/tts')
def tts(body: TextoVoz):
    from neural_core import sky_tts
    try:
        return Response(sky_tts.sintetizar(body.texto), media_type='audio/wav', headers={'Cache-Control': 'no-store'})
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except (RuntimeError, OSError) as exc:
        raise HTTPException(503, str(exc)[:200])


@router.get('/avisos')
def avisos():
    from neural_core import sky_rutinas
    return {'avisos': sky_rutinas.avisos_nuevos()}


@router.get('/agenda')
def agenda():
    from neural_core import sky_rutinas
    data = sky_rutinas.agenda()
    return {'recordatorios': sky_rutinas.pendientes()[:30],
            'rutinas': [{'id': r.get('id'), 'nombre': r.get('nombre'), 'hora': r.get('hora'), 'frases': r.get('frases', [])}
                        for r in data['rutinas']]}


@router.delete('/agenda/{item_id}')
def borrar_recordatorio(item_id: str):
    from neural_core import sky_rutinas
    if not re.fullmatch(r'[a-f0-9]{6,32}', item_id):
        raise HTTPException(400, 'Identificador inválido')
    return {'ok': sky_rutinas.borrar(item_id)}


class Rutina(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    frases: list[str] = Field(default_factory=list, max_length=6)
    hora: str | None = Field(default=None, max_length=5)
    dias: list[int] = Field(default_factory=list, max_length=7)
    pasos: list[dict] = Field(min_length=1, max_length=12)
    activa: bool = True


@router.post('/rutinas')
def guardar_rutina(body: Rutina):
    from neural_core import sky_rutinas
    try:
        return sky_rutinas.guardar_rutina(body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get('/diagnostico')
def diagnostico():
    from neural_core import sky_diagnostico
    items = sky_diagnostico.revisar()
    return {'items': items, 'resumen': sky_diagnostico.resumen(items)}


@router.get('/kpi')
def kpi(periodo: str = 'hoy'):
    """KPIs reales (API, asistente, acciones) y problemas detectados. periodo: hoy | semana."""
    from neural_core import sky_metricas
    if periodo not in ('hoy', 'semana'):
        raise HTTPException(400, 'periodo debe ser hoy o semana')
    datos = sky_metricas.resumen(periodo)
    return {**datos, 'texto': sky_metricas.describir(datos)}


@router.get('/aprendizaje')
def aprendizaje():
    """Lo que SKY aprendió: atajos, órdenes enseñadas, temas de internet, datos y temas que sigue."""
    from neural_core import sky_aprendizaje
    return sky_aprendizaje.estadisticas()


@router.delete('/aprendizaje/atajos/{frase}')
def olvidar_atajo(frase: str):
    from neural_core import sky_aprendizaje
    if len(frase) > 120:
        raise HTTPException(400, 'Frase demasiado larga.')
    return {'ok': sky_aprendizaje.olvidar_orden(frase)}


class EventoKPI(BaseModel):
    tipo: str = Field(pattern='^(voz|tarea)$')
    nombre: str = Field(pattern='^(primera_voz|interrupcion|error_microfono|error_reproduccion|cancelada)$')
    ms: int | None = Field(default=None, ge=0, le=600_000)
    ok: bool = True


@router.post('/kpi/evento')
def kpi_evento(body: EventoKPI):
    """Mediciones que sólo el navegador conoce (voz y cancelaciones). Lista cerrada de nombres."""
    from neural_core import sky_metricas
    sky_metricas.registrar(body.tipo, body.nombre, body.ok, body.ms)
    return {'ok': True}


@router.get('/memoria')
def memoria_exportar(request: Request):
    """Exporta todo lo que SKY recuerda y aprendió (para revisarlo o guardarlo). Exportar datos privados pide PIN."""
    from .sentinel import exigir_pin
    exigir_pin(request, 'exportar tu memoria')
    from neural_core import sky_aprendizaje
    return sky_aprendizaje.exportar()


@router.delete('/memoria/{memoria_id}')
def memoria_borrar(memoria_id: int):
    from neural_core import sky_aprendizaje
    return {'ok': sky_aprendizaje.borrar_memoria(memoria_id)}


# ------------------------------------------------------------------ v12.3: perfil, skills, tareas, borradores, WhatsApp

class Perfil(BaseModel):
    texto: str = Field(max_length=8000)


@router.get('/perfil')
def perfil_ver():
    from neural_core import sky_perfil
    return {'texto': sky_perfil.leer(), 'ruta': str(sky_perfil.ruta())}


@router.put('/perfil')
def perfil_guardar(body: Perfil):
    from neural_core import sky_perfil
    try:
        return sky_perfil.guardar(body.texto)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


class Skill(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    descripcion: str = Field(default='', max_length=300)
    frases: list[str] = Field(default_factory=list, max_length=6)
    pasos: list[dict] = Field(min_length=1, max_length=12)


@router.get('/skills')
def skills_listar():
    from neural_core import sky_skills
    return {'skills': sky_skills.listar(), 'carpeta': str(sky_skills.carpeta())}


@router.post('/skills')
def skills_guardar(body: Skill):
    from neural_core import sky_skills
    try:
        return sky_skills.guardar(body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.delete('/skills/{skill_id}')
def skills_borrar(skill_id: str):
    from neural_core import sky_skills
    if not re.fullmatch(r'[a-z0-9-]{1,40}', skill_id):
        raise HTTPException(400, 'Identificador inválido.')
    return {'ok': sky_skills.borrar(skill_id)}


@router.post('/skills/{skill_id}/ejecutar')
def skills_ejecutar(skill_id: str):
    from neural_core import sky_skills
    sk = sky_skills.obtener(skill_id)
    if not sk:
        raise HTTPException(404, 'Skill no encontrada.')
    return sky_skills.ejecutar(sk)


@router.get('/programadas')
def programadas():
    from neural_core import sky_skills
    return {'tareas': sky_skills.programadas(), 'texto': sky_skills.describir_programadas()}


class Activar(BaseModel):
    activa: bool


@router.patch('/programadas/{rutina_id}')
def programadas_activar(rutina_id: str, body: Activar):
    from neural_core import sky_rutinas
    if not re.fullmatch(r'[a-z0-9-]{1,40}', rutina_id):
        raise HTTPException(400, 'Identificador inválido.')
    r = sky_rutinas.activar_rutina(rutina_id, body.activa)
    if not r:
        raise HTTPException(404, 'Tarea no encontrada.')
    return r


@router.delete('/programadas/{rutina_id}')
def programadas_borrar(rutina_id: str):
    from neural_core import sky_rutinas
    if not re.fullmatch(r'[a-z0-9-]{1,40}', rutina_id):
        raise HTTPException(400, 'Identificador inválido.')
    return {'ok': sky_rutinas.borrar_rutina(rutina_id)}


@router.get('/borradores')
def borradores():
    from neural_core import sky_borradores
    return {'borradores': sky_borradores.listar()}


@router.post('/borradores/preparar')
def borradores_preparar():
    from neural_core import sky_borradores
    try:
        return sky_borradores.preparar()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)[:200])


class Cuerpo(BaseModel):
    cuerpo: str = Field(min_length=1, max_length=20000)


@router.patch('/borradores/{item_id}')
def borradores_editar(item_id: str, body: Cuerpo):
    from neural_core import sky_borradores
    try:
        return sky_borradores.editar(item_id, body.cuerpo)
    except KeyError:
        raise HTTPException(404, 'Borrador no encontrado.')
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post('/borradores/{item_id}/enviar')
def borradores_enviar(item_id: str, request: Request):
    """Este clic ES la confirmación del dueño (nivel 3), con su PIN si lo configuró."""
    from .sentinel import exigir_pin
    exigir_pin(request, 'enviar un correo')
    from neural_core import sky_borradores, sky_metricas
    try:
        res = sky_borradores.enviar(item_id)
    except KeyError:
        raise HTTPException(404, 'Borrador no encontrado.')
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:200])
    except RuntimeError as exc:
        raise HTTPException(409 if 'parada' in str(exc) else 502, str(exc)[:200])
    sky_metricas.registrar('accion', 'enviar_correo', True, detalle='borrador aprobado')
    return res


@router.delete('/borradores/{item_id}')
def borradores_descartar(item_id: str):
    from neural_core import sky_borradores
    return {'ok': sky_borradores.descartar(item_id)}


@router.get('/whatsapp')
def whatsapp_estado():
    from neural_core import sky_whatsapp
    return sky_whatsapp.estado()


@router.post('/whatsapp/prueba')
def whatsapp_prueba():
    """Manda «SKY conectada» al WhatsApp del dueño (sólo funciona dentro de la ventana de 24 h)."""
    from neural_core import sky_whatsapp
    if not sky_whatsapp.configurado():
        raise HTTPException(409, 'WhatsApp no está configurado. Guía: docs/guias/SKY_WHATSAPP.md')
    if not sky_whatsapp.ventana_abierta():
        raise HTTPException(409, 'Escribile primero a SKY por WhatsApp: Meta sólo permite responder dentro de las 24 h.')
    try:
        sky_whatsapp.enviar_texto('✅ SKY conectada a tu WhatsApp.')
    except Exception as exc:
        raise HTTPException(502, 'Meta rechazó el envío: ' + str(exc)[:160])
    return {'ok': True}


# ------------------------------------------------------------------ v12.4: habilidades, Skill Builder, integraciones, creaciones

@router.get('/habilidades')
def habilidades():
    from neural_core import sky_habilidades
    return sky_habilidades.catalogo()


class Interruptor(BaseModel):
    activa: bool


@router.patch('/habilidades/{hid}')
def habilidades_cambiar(hid: str, body: Interruptor):
    from neural_core import sky_habilidades
    if not sky_habilidades.cambiar(hid, body.activa):
        raise HTTPException(400, 'Habilidad desconocida o protegida.')
    return {'id': hid, 'activa': sky_habilidades.activa(hid)}


@router.get('/integraciones')
def integraciones():
    from neural_core import sky_integraciones
    return {'integraciones': sky_integraciones.listar()}


class Pedido(BaseModel):
    pedido: str = Field(min_length=6, max_length=500)


@router.post('/builder/proponer')
def builder_proponer(body: Pedido):
    """La IA diseña la habilidad, se revisa y se prueba aislada. NO la instala."""
    from neural_core import sky_skill_builder
    try:
        return sky_skill_builder.proponer(body.pedido)
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:300])
    except Exception as exc:
        raise HTTPException(503, 'No pude diseñarla (¿hay un modelo de IA disponible?): ' + str(exc)[:200])


class Version(BaseModel):
    manifiesto: dict
    codigo: str = Field(min_length=10, max_length=20000)


@router.post('/builder/version')
def builder_version(body: Version):
    """Una versión escrita o corregida por el dueño: se revisa y se prueba igual que la de la IA."""
    from neural_core import sky_skill_builder
    try:
        return sky_skill_builder.guardar_propuesta(body.manifiesto, body.codigo, 'versión del dueño')
    except ValueError as exc:
        raise HTTPException(400, str(exc)[:300])


@router.get('/builder/{sid}')
def builder_ver(sid: str, version: int | None = None):
    from neural_core import sky_skill_builder
    try:
        m, codigo, reporte = sky_skill_builder.cargar(sid, version)
    except (KeyError, OSError, ValueError):
        raise HTTPException(404, 'Habilidad no encontrada.')
    return {'manifiesto': m, 'codigo': codigo, 'reporte': reporte}


class Aprobacion(BaseModel):
    version: int = Field(ge=1, le=10000)
    permisos: list[str] = Field(default_factory=list, max_length=10)


@router.post('/builder/{sid}/aprobar')
def builder_aprobar(sid: str, body: Aprobacion, request: Request):
    """Este clic del dueño ES la aprobación (nivel 3): instala esa versión con esos permisos (con PIN si existe)."""
    from .sentinel import exigir_pin
    exigir_pin(request, 'instalar una habilidad')
    from neural_core import sky_skill_builder
    try:
        return sky_skill_builder.aprobar(sid, body.version, body.permisos)
    except KeyError:
        raise HTTPException(404, 'Habilidad o versión no encontrada.')
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)[:300])


@router.post('/builder/{sid}/desactivar')
def builder_desactivar(sid: str):
    from neural_core import sky_skill_builder
    return {'ok': sky_skill_builder.desactivar(sid)}


@router.delete('/builder/{sid}')
def builder_eliminar(sid: str):
    from neural_core import sky_skill_builder
    if not re.fullmatch(r'[a-z0-9-]{1,40}', sid):
        raise HTTPException(400, 'Identificador inválido.')
    return {'ok': sky_skill_builder.eliminar(sid)}


@router.get('/creaciones/{tipo}')
def creaciones(tipo: str):
    from neural_core import sky_creativo
    try:
        return {'archivos': sky_creativo.listar(tipo)}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get('/creaciones/{tipo}/{nombre}')
def creacion_archivo(tipo: str, nombre: str):
    from fastapi.responses import FileResponse
    from neural_core import sky_creativo
    try:
        ruta = sky_creativo.ruta_creacion(tipo, nombre)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except FileNotFoundError:
        raise HTTPException(404, 'No existe.')
    tipos = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.md': 'text/markdown; charset=utf-8'}
    return FileResponse(ruta, media_type=tipos[ruta.suffix.lower()], headers={'Cache-Control': 'private, no-store'})
