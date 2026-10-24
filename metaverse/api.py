"""API propia de SKY. Local, autenticada y explícitamente extensible.

Inicia con: python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
"""
from __future__ import annotations
import os,secrets,time,asyncio,json,math
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException,Depends,WebSocket,WebSocketDisconnect,Request,Query,File,UploadFile
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel,Field
from .engine import generate_scene,validate_object,KINDS
from .store import get_world,create_world,list_worlds,save_scene,delete_world,demo_world
from .export3d import export_scene_glb

ROOT=Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
load_dotenv(ROOT/'.env', override=False)
STATIC=Path(__file__).resolve().parent/'static'
SECRET_PATH=ROOT/'local_data'/'sky_api_token.txt'

def api_token():
    from .secrets_v107 import get_secret
    val=get_secret('SKY_API_KEY')
    if val:
        if len(val)<24:raise RuntimeError('SKY_API_KEY debe tener 24 caracteres o más')
        return val
    SECRET_PATH.parent.mkdir(exist_ok=True,parents=True)
    if not SECRET_PATH.exists():
        with SECRET_PATH.open('x',encoding='utf-8') as f:f.write(secrets.token_urlsafe(32))
        try:os.chmod(SECRET_PATH,0o600)
        except OSError:pass
    token=SECRET_PATH.read_text(encoding='utf-8').strip()
    if len(token)<24:raise RuntimeError('Token local inválido: eliminá el token para regenerarlo')
    return token

scheme=APIKeyHeader(name='X-SKY-KEY',auto_error=False)
def require_owner_key_only(token:Optional[str]=Depends(scheme)):
    if not token or not secrets.compare_digest(token,api_token()):
        raise HTTPException(401,detail='Credenciales inválidas',headers={'WWW-Authenticate':'APIKey'})
    return True

def require_key(request:Request, owner_key:bool=Depends(require_owner_key_only)):
    from . import owner_mfa
    if owner_mfa.required() and not owner_mfa.valid(request.headers.get('X-SKY-SESSION')):
        raise HTTPException(401,detail='Se requiere sesión de segundo factor del creador')
    return True

async def _workflow_pump():
    # SKY no ejecuta flujos sin aprobación. Esta cola vive mientras el servidor
    # permanezca activo; las tareas pendientes sobreviven en SQLite al reinicio.
    from neural_core.sky_workflows import run_once
    while True:
        try:
            await asyncio.to_thread(run_once)
        except Exception:
            # Un error del motor no debe apagar la API; diagnósticos en /workflows.
            pass
        await asyncio.sleep(2)

async def _agenda_pump():
    # SKY v12.1: recordatorios, alarmas y rutinas programadas. Avisa al HUD, al escritorio
    # (si la capacidad notify es automática) y al celular (SKY_HA_NOTIFY), sin red externa.
    from neural_core import sky_rutinas
    def ciclo():
        for r in sky_rutinas.vencidos():
            texto=('⏰ ' if r.get('clase')=='alarma' else '🔔 ')+r.get('texto','Recordatorio')
            sky_rutinas.avisar(texto,'recordatorio')
            _avisar_fuera(r.get('texto','Recordatorio'))
        for rutina in sky_rutinas.rutinas_programadas():
            res=sky_rutinas.ejecutar_rutina(rutina)
            if res['mensaje']:
                sky_rutinas.avisar(res['mensaje'],'rutina')
                _whatsapp(rutina.get('nombre','Tarea')+': '+res['mensaje'])
        _vigilancia()
    while True:
        try:await asyncio.to_thread(ciclo)
        except Exception:pass
        await asyncio.sleep(20)

_VIGILANCIA={'kpi':0.0,'intereses':0.0,'avisados':set(),'dia':''}

def _vigilancia():
    # SKY v12.2: cada 5 min revisa sus KPIs y avisa UNA vez por día cada problema nuevo;
    # cada hora actualiza los temas que sigue (si SKY_INTERNET no es 0).
    import time as _t
    from datetime import date
    from neural_core import sky_rutinas, sky_metricas, sky_aprendizaje
    ahora=_t.time();hoy=date.today().isoformat()
    if _VIGILANCIA['dia']!=hoy:
        _VIGILANCIA.update(dia=hoy,avisados=set())
    if ahora-_VIGILANCIA['kpi']>=300:
        _VIGILANCIA['kpi']=ahora
        for p in sky_metricas.detectar():
            if p['id'] not in _VIGILANCIA['avisados']:
                _VIGILANCIA['avisados'].add(p['id'])
                sky_rutinas.avisar('Detecté un problema: '+p['titulo']+'. '+p['sugerencia'],'kpi')
                _whatsapp('⚠️ Detecté un problema: '+p['titulo']+'. '+p['sugerencia'])
    if ahora-_VIGILANCIA['intereses']>=3600:
        _VIGILANCIA['intereses']=ahora
        for linea in sky_aprendizaje.actualizar_intereses():
            sky_rutinas.avisar('Novedad: '+linea,'aprendizaje')

def _whatsapp(texto:str):
    # v12.3: avisos al WhatsApp del dueño (dentro de la ventana de 24 h, o con su plantilla aprobada).
    try:
        from neural_core import sky_whatsapp
        sky_whatsapp.enviar_aviso(texto)
    except Exception:pass

def _avisar_fuera(texto:str):
    _whatsapp('🔔 '+texto)
    try:
        from neural_core.sky_asistente_personal import ejecutar_local_si_autorizado
        ejecutar_local_si_autorizado({'action':'notify','params':{'title':'SKY','message':texto},'description':'Recordatorio'})
    except Exception:pass
    try:
        from neural_core import sky_home_assistant
        sky_home_assistant.notificar_celular(texto)
    except Exception:pass

async def _creative_pump():
    from neural_core.sky_creative import run_next_job
    while True:
        try:await asyncio.to_thread(run_next_job)
        except Exception:pass
        await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app):
    api_token()
    from .owner_mfa import validate_configuration
    from .deployment_v102 import validate_environment
    validate_configuration()
    validate_environment()
    demo_world()
    from neural_core.sky_creative import mark_interrupted
    mark_interrupted()
    pump=None
    creative_pump=asyncio.create_task(_creative_pump()) if os.getenv('SKY_CREATIVE_WORKER','1')=='1' else None
    if os.getenv('SKY_WORKFLOWS_ENABLED','1')=='1':
        pump=asyncio.create_task(_workflow_pump())
    try:
        from neural_core import sky_metricas
        sky_metricas.registrar('servicio','inicio',True,detalle='API iniciada')
    except Exception:pass
    agenda_pump=asyncio.create_task(_agenda_pump()) if os.getenv('SKY_AGENDA_ENABLED','1')=='1' else None
    try:
        yield
    finally:
        if agenda_pump:
            agenda_pump.cancel()
            try:await agenda_pump
            except asyncio.CancelledError:pass
        if creative_pump:
            creative_pump.cancel()
            try:await creative_pump
            except asyncio.CancelledError:pass
        if pump:
            pump.cancel()
            try:await pump
            except asyncio.CancelledError:pass

app=FastAPI(title='SKY Engine API',version='10.5.0',description='Interfaz local de SKY: mundos 3D, herramientas y motores autorizados.',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=STATIC),name='static')

# Installable SKY client for Windows browsers and Android; same SKY API and HUD.
from .mobile_pwa_api import router as mobile_pwa_router
app.include_router(mobile_pwa_router)

# SKY Teléfono reuses the private SKY API, owner key and SENTINEL MFA.
from .phone_api import router as sky_phone_router
app.include_router(sky_phone_router)

from .telemetria_api import router as telemetria_router
app.include_router(telemetria_router)

@app.get('/office')
def office_home():return FileResponse(STATIC/'office.html')

@app.get('/aula/3d/computadora')
def aula_computer_3d():
    # Fixed public educational model; never exposes teacher/student records.
    return FileResponse(STATIC/'sky-aula-computer-3d.html',
                        headers={"Cache-Control":"public, max-age=180"})


class OfficeRequest(BaseModel):
    kind: str=Field(default='docx',max_length=5)
    title: str=Field(default='Mi creación SKY',max_length=160)
    prompt: str=Field(default='',max_length=6000)
    content: str=Field(default='',max_length=50000)
    csv: str=Field(default='',max_length=30000)
    headers: list=Field(default_factory=list,max_length=40)
    rows: list=Field(default_factory=list,max_length=300)
    template: str='general'
    language: str='es'
    ai_provider: str='none'  # SOLO bajo solicitud explícita, no fallback oculto

@app.get('/api/office/formats',dependencies=[Depends(require_key)])
def office_formats():
    from neural_core.sky_office import FORMATS
    return {'formats':{ext:{'description':label,'mime':mime} for ext,(label,mime) in FORMATS.items()},
            'ai_optional':True,'data_shared_by_default':False}

@app.post('/api/office/generate',dependencies=[Depends(require_key)])
def office_generate(request:OfficeRequest):
    from neural_core.sky_office import create_document
    spec=request.model_dump()
    from neural_core.sky_languages import normalize
    try:document_language=normalize(request.language,strict=True)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    provider=request.ai_provider.lower()
    if provider!='none':
        if provider not in ('gemini','openai','anthropic','ollama','mistral','groq','deepseek'):
            raise HTTPException(422,'Proveedor no disponible.')
        if not request.prompt.strip():raise HTTPException(422,'Añadí un tema para redactar con IA.')
        try:
            from neural_core.assistant import responder
            instructions=(f'Redactá un borrador estructurado en el idioma {document_language} para un documento tipo {request.kind} titulado '
                          f'{request.title}. Tema: {request.prompt}. Devolvé texto con encabezados Markdown (#) '
                          'y contenido claro, preciso y editable. No inventés cifras ni fuentes.')
            result,_=responder(instructions,'SKY Office Studio',proveedor=provider)
            spec['content']=result[:49000]
            if request.content.strip():spec['content']+='\n\n'+request.content[:900]
        except Exception as exc:
            raise HTTPException(503,'Motor de IA no disponible ('+type(exc).__name__+').') from exc
    try:doc=create_document(spec)
    except (ValueError,RuntimeError,ImportError) as exc:raise HTTPException(422,str(exc)[:200]) from exc
    return Response(content=doc.data,media_type=doc.media_type,
      headers={'Content-Disposition':f'attachment; filename="{doc.filename}"',
               'X-SKY-Office-Format':request.kind.upper()})

class WorldCreate(BaseModel):
    name:str=Field(min_length=1,max_length=65)
    prompt:str=Field(min_length=1,max_length=1000)
    seed:int=Field(default=42,ge=-2147483648,le=2147483647)

class WorldSave(BaseModel):
    version:int=Field(ge=1)
    scene:dict

class PromptRequest(BaseModel):
    prompt:str=Field(min_length=1,max_length=1000)
    seed:int=42
    append:bool=False
    version:int=Field(ge=1)

class ChatRequest(BaseModel):
    message:str=Field(min_length=1,max_length=15000)
    language:str='es'
    provider:str='local'
    area:str='Metaverso'
    file_context:Optional[str]=None

class SkillRequest(BaseModel):
    name:str
    argument:str=''

class ObjectRequest(BaseModel):
    version:int=Field(ge=1)
    object:dict

class PositionMessage(BaseModel):
    type:str
    avatar:str='SKY'
    x:float=0
    y:float=0
    z:float=0

@app.get('/')
def index():
    # SKY v12: la interfaz principal es el HUD; la clásica sigue en /sky (también dentro del HUD).
    resp = FileResponse(STATIC/'hud.html')
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.get('/sky')
def sky_home():
    resp = FileResponse(STATIC/'sky.html')
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@app.get('/flows')
def workflows_page():return FileResponse(STATIC/'flows.html')

@app.get('/owner/baqueano')
def baqueano_owner_page():return FileResponse(STATIC/'baqueano-owner.html')

@app.get('/world')
def metaverse_world():return FileResponse(STATIC/'index.html')

@app.get('/api/health')
def health():return {'service':'SKY Engine API','status':'ok','version':'10.4.0','private':'key required for data'}

@app.get('/api/capabilities',dependencies=[Depends(require_key)])
def capabilities():
    from neural_core.providers import provider_summary
    return {'engine':'SKY','offline':True,'modules':['metaverso 3D local','escenas proceduralmente generadas','GLB export','herramientas SKY','memoria existente','studio 2.5D','SKY Office Studio: DOCX, PPTX, PDF, XLSX, CSV, Markdown, HTML','SKY v9: roles especializados, Workbench, Creator HTML, Neural Activity','voz navegador si disponible','presencia en vivo'],
            'shapes':sorted(KINDS),'providers':provider_summary(),
            'limitations':['API propia no equivale a modelo fundacional propio','escenarios generados por reglas, no video/juego fotorrealista','WebXR requiere equipo y navegador compatibles']}

@app.get('/api/worlds',dependencies=[Depends(require_key)])
def worlds():
    demo_world();return list_worlds()

@app.post('/api/worlds',dependencies=[Depends(require_key)],status_code=201)
def new_world(body:WorldCreate):
    try:return create_world(body.name,body.prompt,body.seed)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.get('/api/worlds/{wid}',dependencies=[Depends(require_key)])
def world(wid:str):
    result=get_world(wid)
    if not result:raise HTTPException(404,'Mundo no existe')
    return result

@app.put('/api/worlds/{wid}',dependencies=[Depends(require_key)])
def replace_world(wid:str,body:WorldSave):
    try:return save_scene(wid,body.scene,body.version)
    except KeyError:raise HTTPException(404,'Mundo no existe')
    except RuntimeError as exc:raise HTTPException(409,str(exc))
    except ValueError as exc:raise HTTPException(422,str(exc))

@app.post('/api/worlds/{wid}/generate',dependencies=[Depends(require_key)])
def regenerate(wid:str,body:PromptRequest):
    current=get_world(wid)
    if current is None:raise HTTPException(404,'Mundo no existe')
    try:
        new=generate_scene(body.prompt,body.seed)
        if body.append:
            # No duplicate floors when extending a world.
            objs=[ob for ob in new['objects'] if ob['name']!='Terreno SKY']
            new={**current['scene'],'prompt':body.prompt,'objects':current['scene']['objects']+objs}
        return save_scene(wid,new,body.version)
    except ValueError as exc:raise HTTPException(422,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@app.post('/api/worlds/{wid}/objects',dependencies=[Depends(require_key)])
def add_object(wid:str,body:ObjectRequest):
    current=get_world(wid)
    if current is None:raise HTTPException(404,'Mundo no existe')
    try:
        ob=validate_object({k:v for k,v in body.object.items() if k!='id'})
        current['scene']['objects'].append(ob)
        return save_scene(wid,current['scene'],body.version)
    except ValueError as exc:raise HTTPException(422,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@app.get('/api/worlds/{wid}/export.glb',dependencies=[Depends(require_key)])
def export(wid:str):
    current=get_world(wid)
    if not current:raise HTTPException(404,'Mundo no existe')
    try:blob=export_scene_glb(current['scene'])
    except (ValueError,ImportError) as exc:raise HTTPException(422,str(exc))
    return Response(content=blob,media_type='model/gltf-binary',headers={'Content-Disposition':'attachment; filename="SKY_metaverse.glb"'})

@app.delete('/api/worlds/{wid}',dependencies=[Depends(require_key)])
def remove_world(wid:str):
    if not delete_world(wid):raise HTTPException(404,'Mundo no existe')
    return {'removed':wid}

@app.post('/api/tools/run',dependencies=[Depends(require_key)])
def run_tool(body:SkillRequest):
    from neural_core.sky_agent import execute_skill,SKILLS
    if body.name not in SKILLS:raise HTTPException(422,'Herramienta no reconocida')
    try:result=execute_skill(body.name,body.argument)
    except Exception as exc:raise HTTPException(422,'Argumento inválido: '+type(exc).__name__) from exc
    return {'tool':body.name,'result':result}

UPLOADS_DIR = ROOT / 'local_data' / 'sky_uploads'
GENERATED_DIR = ROOT / 'local_data' / 'sky_generated'
# La importación debe ser segura con --read-only; crear carpetas sólo al escribir.

@app.get('/api/media/uploads/{filename}')
def get_uploaded_media(filename: str):
    p = (UPLOADS_DIR / filename).resolve()
    if not p.is_file() or not p.is_relative_to(UPLOADS_DIR.resolve()):
        raise HTTPException(404, 'Archivo no encontrado')
    return FileResponse(p)

@app.get('/api/media/generated/{filename}')
def get_generated_media(filename: str):
    p = (GENERATED_DIR / filename).resolve()
    if not p.is_file() or not p.is_relative_to(GENERATED_DIR.resolve()):
        raise HTTPException(404, 'Archivo generado no encontrado')
    return FileResponse(p)

@app.post('/api/chat/upload',dependencies=[Depends(require_key)])
async def upload_chat_file(file:UploadFile=File(...)):
    """Sube un archivo de cualquier tipo (Video, Música, Audio, PDF, DOCX, XLSX, CSV, TXT, Código, etc.) sin restricciones."""
    from neural_core.documentos import extraer_texto
    from neural_core.storage import agregar_documento, guardar_memoria
    from neural_core.sky_evolution import feedback
    data = await file.read()
    filename = file.filename or 'archivo_adjunto'
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    
    # Guardar copia física local en sky_uploads para reproducción inmediata
    safe_name = f"{secrets.token_hex(4)}_{Path(filename).name}"
    local_path = UPLOADS_DIR / safe_name
    try:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
    except Exception:
        pass

    media_type = 'document'
    if ext in ('mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv'):
        media_type = 'video'
    elif ext in ('mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac'):
        media_type = 'audio'
    elif ext in ('png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'svg'):
        media_type = 'image'

    try:
        texto = extraer_texto(filename, data)
    except Exception as exc:
        texto = f"[Archivo {filename} ({len(data)} bytes) listo para procesamiento]"

    doc_id = None
    try:
        doc_id = agregar_documento(filename, texto[:245000])
    except Exception:
        pass
    try:
        guardar_memoria(f"Archivo asimilado: '{filename}' ({media_type.upper()}, {round(len(data)/1024, 1)} KB). Conocimiento integrado.")
        feedback("aprendizaje_documental", 5, f"Incorporado conocimiento desde archivo {filename}")
    except Exception:
        pass
    return {
        'ok': True,
        'filename': filename,
        'size_bytes': len(data),
        'media_type': media_type,
        'media_url': f'/api/media/uploads/{safe_name}',
        'doc_id': doc_id,
        'chars_extracted': len(texto),
        'summary': texto[:800],
        'full_text': texto[:30000]
    }

@app.get('/api/evolution/stats',dependencies=[Depends(require_key)])
def evolution_stats():
    from neural_core.storage import memorias, documentos
    from neural_core.sky_evolution import feedback_resumen, metas
    mems = len(memorias())
    docs = len(documentos())
    fb = feedback_resumen()
    evals = sum(x.get('evaluaciones', 0) for x in fb)
    return {
        'status': 'Evolución Activa',
        'level': 'Nivel Adaptativo Autónomo',
        'total_memories': mems,
        'total_documents': docs,
        'total_interactions': evals,
        'active_goals': len(metas()),
    }

@app.post('/api/chat',dependencies=[Depends(require_key)])
def chat(body:ChatRequest):
    from neural_core.sky_agent import interpret_local_command
    local=interpret_local_command(body.message)
    if local is not None:return {'provider':'sky-local','answer':local}
    if body.provider=='local':
        return {'provider':'sky-local','answer':'SKY local puede generar mundos por descripción, guardar escenarios, exportar GLB y usar /sky calcula, /sky metas o /sky hora. Para diálogo abierto, configurá Ollama, Gemini, OpenAI u otro motor en SKY y elegilo aquí.'}
    
    prompt = body.message
    if body.file_context:
        prompt = f"Archivos y documentos adjuntos por el usuario:\n{body.file_context}\n\nInstrucción o solicitud del usuario sobre estos datos:\n{body.message}"
    
    prov = 'auto' if body.provider in ('auto', 'sky') else body.provider
    try:
        from neural_core.assistant import responder
        answer, evidencias = responder(prompt, body.area, proveedor=prov, idioma=body.language)
        try:
            from neural_core.sky_evolution import feedback
            feedback("asistente_unificado", 5, f"Consulta procesada con éxito por SKY")
        except Exception:
            pass
        return {'provider':'SKY Autónomo','answer':answer,'evidencias':[e.get('nombre') for e in evidencias] if evidencias else []}
    except Exception as exc:
        if prov != 'ollama':
            try:
                from neural_core.assistant import responder
                answer, evidencias = responder(prompt, body.area, proveedor='ollama', idioma=body.language)
                return {'provider':'SKY Autónomo (Local)','answer':answer,'evidencias':[e.get('nombre') for e in evidencias] if evidencias else []}
            except Exception:
                pass
        raise HTTPException(503,'Motor no disponible ('+type(exc).__name__+'). Revisá configuración y conectividad.') from exc

# Compatibilidad básica de chat para aplicaciones propias que usan cliente estilo OpenAI.
# No implementa streaming, tool-calls, embeddings, fine-tuning ni los pesos de ningún proveedor.
class CompatibleChat(BaseModel):
    model:str='local'
    messages:list[dict]
    stream:bool=False

@app.get('/v1/models',dependencies=[Depends(require_key)])
def models_compatible():
    from neural_core.providers import provider_summary
    return {'object':'list','data':[{'id':'local','object':'model','owned_by':'sky'}, *[
        {'id':m['id'],'object':'model','owned_by':m['proveedor']} for m in provider_summary()]]}

@app.post('/v1/chat/completions',dependencies=[Depends(require_key)])
def compatible_chat(payload:CompatibleChat):
    if payload.stream:raise HTTPException(422,'Streaming todavía no está implementado')
    if len(payload.messages)>24:raise HTTPException(422,'Demasiados turnos')
    last=next((m for m in reversed(payload.messages) if m.get('role')=='user'),None)
    if last is None or not isinstance(last.get('content'),str):
        raise HTTPException(422,'Se requiere un mensaje de usuario en texto')
    reply_data=chat(ChatRequest(message=last['content'],provider=payload.model))
    return {'id':'sky-'+secrets.token_hex(8),'object':'chat.completion','created':int(time.time()),
            'model':payload.model,'choices':[{'index':0,'finish_reason':'stop',
              'message':{'role':'assistant','content':reply_data['answer']}}]}

@app.get('/api/evolution',dependencies=[Depends(require_key)])
def evolution():
    from neural_core.sky_evolution import metas,mejoras,feedback_resumen
    return {'goals':metas(),'improvements':mejoras(),'feedback':feedback_resumen()}

@app.post('/api/studio/photo-to-glb',dependencies=[Depends(require_key)])
async def photo_to_glb(request:Request,x0:float=Query(.08,ge=0,le=1),y0:float=Query(.08,ge=0,le=1),
                        x1:float=Query(.92,ge=0,le=1),y1:float=Query(.92,ge=0,le=1),
                        depth:float=Query(.12,ge=.005,le=2)):
    """Una foto -> selección asistida -> extrusión de silueta 2.5D. Sin enviar fotos a la nube."""
    if request.headers.get('content-type','').split(';')[0] not in {'image/png','image/jpeg','image/webp'}:
        raise HTTPException(415,'Solo PNG, JPG o WebP')
    data=bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data)>12_000_000:raise HTTPException(413,'La imagen supera 12 MB')
    try:
        from neural_core.sky_3d import leer_imagen,caja_relativa,segmentar_parte,png_bytes,ensamblar_glb
        im=leer_imagen(bytes(data))
        box=caja_relativa(im.width,im.height,x0,y0,x1,y1)
        cut=segmentar_parte(im,box,modo='grabcut')
        glb=ensamblar_glb([{'name':'Pieza fotografica','png':png_bytes(cut),'depth':depth}],*im.size)
    except (ValueError,OSError) as exc:
        raise HTTPException(422,'No se pudo procesar la imagen: '+str(exc)[:180]) from exc
    return Response(content=glb,media_type='model/gltf-binary',headers={
        'Content-Disposition':'attachment; filename="SKY_foto_3D.glb"',
        'X-SKY-3D-Method':'2.5D-silhouette-extrusion'})

# WebSocket tickets: single-use, short-lived and never stored in URL after login.
_tickets:dict[str,float]={}
_connections:dict[str,dict[WebSocket,dict]]={}

def _cleanup_tickets():
    for t,expiry in list(_tickets.items()):
        if expiry<time.monotonic():_tickets.pop(t,None)

@app.post('/api/ws-ticket',dependencies=[Depends(require_key)])
def ticket():
    _cleanup_tickets()
    t=secrets.token_urlsafe(26);_tickets[t]=time.monotonic()+35
    return {'ticket':t,'expires_in_seconds':35}

async def _send_all(wid:str,msg:dict):
    for sock in list(_connections.get(wid,{})):
        try:await sock.send_json(msg)
        except Exception:_connections[wid].pop(sock,None)

@app.websocket('/api/ws/{wid}')
async def ws_room(socket:WebSocket,wid:str,ticket:str=''):
    _cleanup_tickets()
    # No credentials or persistent API key in URL: only one-time ticket.
    expiry=_tickets.pop(ticket,None)
    if not expiry or expiry<time.monotonic() or get_world(wid) is None:
        await socket.close(code=1008);return
    await socket.accept()
    room=_connections.setdefault(wid,{})
    user=secrets.token_hex(5)
    room[socket]={'id':user,'name':'Visitante','position':[0,0,0]}
    try:
        await socket.send_json({'type':'peers','you':user,'peers':list(room.values())})
        await _send_all(wid,{'type':'join','peer':room[socket]})
        while True:
            data=await socket.receive_json()
            if not isinstance(data,dict):continue
            if data.get('type')=='move':
                xyz=data.get('position')
                try:
                    if not isinstance(xyz,list) or len(xyz)!=3 or any(abs(float(v))>80 or not math.isfinite(float(v)) for v in xyz):continue
                except (ValueError,TypeError):continue
                room[socket]['position']=[float(v) for v in xyz]
                await _send_all(wid,{'type':'move','peer':room[socket]})
            elif data.get('type')=='say':
                text=str(data.get('text','')).strip()[:280]
                if text:await _send_all(wid,{'type':'say','from':user,'text':text})
    except (WebSocketDisconnect,RuntimeError):pass
    finally:
        room.pop(socket,None)
        await _send_all(wid,{'type':'leave','id':user})

# Se añade como módulo: no cambia las rutas privadas de SKY v6.
from .community_api import router as community_router
app.include_router(community_router)


# SKY v9: orquestación de roles, diseño visual editable y trazas REALES del motor API.
from .workspace_api import router as sky_workspace_router
app.include_router(sky_workspace_router)

@app.middleware('http')
async def sky_real_activity(request:Request,call_next):
    from neural_core.sky_telemetry import record
    start=time.perf_counter()
    try:
        response=await call_next(request)
        ms=(time.perf_counter()-start)*1000
        record(request.url.path,ms,response.status_code)
        _kpi_api(request,ms,response.status_code)
        return response
    except Exception:
        ms=(time.perf_counter()-start)*1000
        record(request.url.path,ms,500)
        _kpi_api(request,ms,500)
        raise

def _kpi_api(request:Request,ms:float,status:int):
    # SKY v12.2: KPIs reales por ruta (plantilla sin IDs), código y milisegundos.
    path=request.url.path
    if not path.startswith('/api/'):return
    from neural_core import sky_metricas
    ruta=getattr(request.scope.get('route'),'path',None) or sky_metricas.ruta_plantilla(path)
    sky_metricas.registrar('api',f'{request.method} {ruta}',status<500,ms,codigo=status)

# v9.3: flujos autónomos locales, privilegios exclusivos del creador.
from .workflow_api import router as workflow_router
app.include_router(workflow_router)
from .intelligent_api import router as sky_intelligent_router
app.include_router(sky_intelligent_router)

# SKY v9.7: editor profesional por capas + renders multimedia, propietario solamente.
from .creative_api import router as creative_router
app.include_router(creative_router)


# SKY v10.1: idiomas y protección HTTP por defecto.
from .language_api import router as sky_language_router
app.include_router(sky_language_router)
from .security_v101 import install as install_sky_security
install_sky_security(app)
# SKY SENTINEL (v12.5): toda /api/* es privada salvo excepciones explícitas; falla cerrado.
from .sentinel import install as install_sentinel
install_sentinel(app)
from .sentinel_api import router as sentinel_router
app.include_router(sentinel_router)

# SKY 10.2: optional creator TOTP + short-lived server-side sessions.
from .security_api import router as sky_security_router
app.include_router(sky_security_router)

# SKY v10.2: private subtitle and multilingual narration tools.
from .global_media_api import router as sky_global_media_router
app.include_router(sky_global_media_router)

# SKY v10.3: local voice and dubbing routes (no network or new public controls).
from .voice_v103_api import router as sky_voice_v103_router
app.include_router(sky_voice_v103_router)

# SKY v10.5: private, explicit offline speech transcription. No model downloads.
from .stt_v105_api import router as sky_stt_v105_router
app.include_router(sky_stt_v105_router)

# Telemetría industrial y hardware físico real (COM / IoT / Arduino)
from .telemetria_api import router as sky_telemetria_router
app.include_router(sky_telemetria_router)

# SKY v11.1/v12: Asistente Personal — órdenes en lenguaje natural sobre tus dispositivos.
from .asistente_api import router as sky_asistente_router
app.include_router(sky_asistente_router)

# SKY Impacto, Scholar y Pro Skills — API y protección original.
from .impacto_api import router as sky_impacto_router
app.include_router(sky_impacto_router, dependencies=[Depends(require_key)])

# SKY Aula: módulo aislado, comparte la autenticación principal.
from .academy_api import router as sky_academy_router
app.include_router(sky_academy_router)

# SKY Verification Lab — solo lectura, usa la misma API y el control del propietario.
from .verification_api import router as sky_verification_router
app.include_router(sky_verification_router)

# MCP oficial opcional: reutiliza el dueño/SENTINEL; desactivado por defecto.
from .mcp_api import router as sky_mcp_router
app.include_router(sky_mcp_router)
# SKY Core / Guardian / Knowledge: reutilizan las mismas credenciales y MFA.
from .neural_memory_api import router as sky_neural_memory_router
app.include_router(sky_neural_memory_router)
from .multimodal_api import router as sky_multimodal_router
app.include_router(sky_multimodal_router)
from .guardian_api import router as sky_guardian_router
app.include_router(sky_guardian_router)
from .mobile_unlock_api import router as sky_mobile_unlock_router
app.include_router(sky_mobile_unlock_router)
from .device_hub_api import router as sky_device_hub_router
app.include_router(sky_device_hub_router)
from .knowledge_api import router as sky_knowledge_router
app.include_router(sky_knowledge_router)


from .hud_api import router as sky_hud_router
app.include_router(sky_hud_router)

@app.get('/hud')
def hud_page():
    resp=FileResponse(STATIC/'hud.html')
    resp.headers['Cache-Control']='no-cache, no-store, must-revalidate'
    return resp

@app.get('/aula')
def sky_aula_page():
    return FileResponse(STATIC/'sky-academy.html',headers={'Cache-Control':'no-store'})

@app.get('/asistente')
def asistente_page():
    # v12: el Asistente Personal vive dentro del HUD.
    from fastapi.responses import RedirectResponse
    return RedirectResponse('/', status_code=307)

@app.get('/api/client/bootstrap')
def client_bootstrap(request: Request):
    """Inicializa la sesión directa del creador/superadministrador en localhost."""
    client_ip = request.client.host if request.client else '127.0.0.1'
    is_local = client_ip in ('127.0.0.1', '::1', 'localhost', 'testclient', 'testserver')
    # En despliegues públicos, una conexión interna del proxy no prueba que sea el dueño.
    reveal_owner_key = is_local and os.getenv('SKY_DEPLOYMENT_MODE', 'local').strip().lower() == 'local'
    # SENTINEL: con PIN configurado la llave nunca se entrega sin él (POST /api/sentinel/desbloquear).
    from neural_core.sentinel_identidad import pin_configurado
    requiere_pin = pin_configurado()
    if requiere_pin:
        reveal_owner_key = False
    return {
        'key': api_token() if reveal_owner_key else '',
        'requiere_pin': requiere_pin,
        'local': is_local,
        'ollama_active': True,
        'gemini_active': bool(os.getenv('GEMINI_API_KEY')),
        'mistral_active': bool(os.getenv('MISTRAL_API_KEY')),
        'deepseek_active': bool(os.getenv('DEEPSEEK_API_KEY')),
        'ia_gratis_active': bool(os.getenv('IA_GRATIS_TOKEN'))
    }

@app.post('/api/tools/image')
def tool_image(body: dict):
    """Genera imágenes mediante el token de ia.gratis y las guarda localmente para prevenir enlaces rotos."""
    from neural_core.sky_ia_gratis import generar_imagen
    prompt = body.get('prompt', '')
    res = generar_imagen(prompt)
    if res.get('ok') and res.get('result') and len(res['result']):
        try:
            import urllib.request
            img_url = res['result'][0]
            token = secrets.token_hex(6)
            local_name = f"flux_{token}.jpg"
            GENERATED_DIR.mkdir(parents=True, exist_ok=True)
            dest = GENERATED_DIR / local_name
            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as r, open(dest, 'wb') as f:
                f.write(r.read())
            res['result'] = [f'/api/media/generated/{local_name}']
            res['local_url'] = f'/api/media/generated/{local_name}'
        except Exception:
            pass
    return res

@app.post('/api/tools/video')
def tool_video(body: dict):
    """Genera video en duraciones de 1, 3, 5, 8 o 10 minutos."""
    from neural_core.sky_video_gen import generar_video_sky
    prompt = body.get('prompt', '')
    minutos = body.get('minutes')
    return generar_video_sky(prompt, minutos=minutos)

@app.post('/api/tools/search')
def tool_search(body: dict):
    """Realiza búsquedas web con resumen mediante ia.gratis o motor universal."""
    from neural_core.sky_media_tools import universal_web_search
    query = body.get('query', '')
    return universal_web_search(query)

@app.post('/api/tools/remove-bg')
async def tool_remove_bg(body: dict):
    """Quitar fondo transparente estilo remove.bg (imagen local, adjunta o url)."""
    from neural_core.sky_media_tools import remove_background
    image_ref = body.get('image', '') or body.get('filename', '')
    return remove_background(image_ref)

@app.post('/api/tools/download-video')
async def tool_download_video(body: dict):
    """Descargar video multimedia estilo savefrom.net / ssstik.io (TikTok, YouTube, etc.)."""
    from neural_core.sky_media_tools import download_multimedia_video
    url = body.get('url', '')
    extract_audio = body.get('audio_only', False)
    return download_multimedia_video(url, extract_audio=extract_audio)

@app.post('/api/tools/icon')
async def tool_icon(body: dict):
    """Generación de iconos vectoriales SVG y PNG de alta definición estilo flaticon.es."""
    from neural_core.sky_media_tools import generate_vector_icon
    concept = body.get('concept', '') or body.get('prompt', 'star')
    primary = body.get('primary', '#38bdf8')
    secondary = body.get('secondary', '#0284c7')
    return generate_vector_icon(concept, color_primary=primary, color_secondary=secondary)

@app.post('/api/tools/upscale')
async def tool_upscale(body: dict):
    """Super-resolución, mejora de nitidez y escalado x2/x4 estilo magnific.com."""
    from neural_core.sky_media_tools import enhance_upscale_image
    image_ref = body.get('image', '') or body.get('filename', '')
    scale = body.get('scale', 2)
    return enhance_upscale_image(image_ref, scale_factor=scale)

# ==============================================================================
# SKY DEVELOPER INTELLIGENCE CORE ENDPOINTS
# ==============================================================================
@app.get('/api/developer/sources')
def developer_sources():
    """Devuelve el catálogo de repositorios de referencia autorizados."""
    from neural_core.github_reader import list_reference_repositories
    return {'ok': True, 'sources': list_reference_repositories()}

@app.post('/api/developer/consult')
def developer_consult(body: dict):
    """Consulta código o documentación de referencia desde un repositorio oficial."""
    from neural_core.github_reader import fetch_file_content, search_reference_code
    repo = body.get('repository', '')
    path = body.get('path', '')
    query = body.get('query', '')
    if path:
        return fetch_file_content(repo, path)
    if query:
        return search_reference_code(query, repo_identifier=repo or None)
    return {'ok': False, 'error': 'Se requiere "path" o "query" para la consulta.'}

@app.post('/api/developer/analyze')
def developer_analyze(body: dict):
    """Analiza la solicitud y devuelve stack tecnológico y plan de ingeniería."""
    from neural_core.developer_core import analyze_tech_stack
    text = body.get('prompt', '') or body.get('text', '')
    return {'ok': True, 'analysis': analyze_tech_stack(text)}

@app.get('/api/developer/toolchains', dependencies=[Depends(require_key)])
def developer_toolchains(language: str = ''):
    """Detecta los compiladores presentes en PATH sin ejecutar código ni exponer rutas."""
    from neural_core.sky_programming_capabilities import toolchain_status
    try:
        return toolchain_status(language or None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post('/api/developer/syntax-check', dependencies=[Depends(require_key)])
def developer_syntax_check(body: dict):
    """Valida sintaxis Python/JSON sin ejecutar código arbitrario."""
    from neural_core.sky_programming_capabilities import validate_source
    try:
        return validate_source(body.get('language', ''), body.get('code', ''))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/developer/build/capabilities', dependencies=[Depends(require_key)])
def developer_build_capabilities():
    """Catálogo de ejecutores aislados, sin arrancar Docker ni descargar imágenes."""
    from neural_core.sky_docker_builder import catalogue
    return catalogue()


@app.post('/api/developer/build/execute', dependencies=[Depends(require_key)])
def developer_build_execute(body: dict, request: Request):
    """Compilación real en Docker local, con consentimiento, PIN y opt-in separados."""
    from neural_core import sentinel_identidad as ident
    from .sentinel import exigir_pin
    from neural_core.sky_docker_builder import build, RunnerInvalid, RunnerUnavailable
    if not ident.pin_configurado():
        raise HTTPException(403, "Configurá un PIN SKY SENTINEL antes de ejecutar código.")
    exigir_pin(request, "compilar y ejecutar código externo en contenedor aislado")
    if body.get("approved") is not True:
        raise HTTPException(403, "Se necesita consentimiento explícito para ESTA ejecución.")
    try:
        return build(body.get("language", ""), body.get("files"),
                     approved=True, expected_stdout=body.get("expected_stdout"),
                     timeout_seconds=body.get("timeout_seconds", 15))
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except RunnerInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except RunnerUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


# SKY Developer Workbench shares the existing private API and SENTINEL guard.
@app.get('/api/developer/workbench/catalogue', dependencies=[Depends(require_key)])
def developer_ecosystem(category: str = '', query: str = '', limit: int = 80):
    from neural_core.sky_developer_workbench import ecosystem, WorkbenchInvalid
    try:
        return ecosystem(category or None, query, limit)
    except WorkbenchInvalid as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/developer/workbench/readiness', dependencies=[Depends(require_key)])
def developer_sdk_readiness():
    from neural_core.sky_developer_workbench import sdk_readiness
    return sdk_readiness()


@app.post('/api/developer/workbench/inspect', dependencies=[Depends(require_key)])
def developer_inspect(body: dict):
    from neural_core.sky_developer_workbench import inspect_project, WorkbenchInvalid
    try:
        return inspect_project(body.get('files'))
    except WorkbenchInvalid as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post('/api/developer/workbench/explain', dependencies=[Depends(require_key)])
def developer_explain_lines(body: dict):
    from neural_core.sky_developer_workbench import explain_code, WorkbenchInvalid
    try:
        return explain_code(body.get('language', ''),
                            body.get('source', ''),
                            body.get('start_line', 1), body.get('max_lines', 80))
    except WorkbenchInvalid as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post('/api/developer/workbench/starter/web', dependencies=[Depends(require_key)])
def developer_starter_web(body: dict):
    from neural_core.sky_developer_workbench import scaffold_web, WorkbenchInvalid
    try:
        return scaffold_web(body.get('title', 'Mi proyecto SKY'),
                            body.get('subtitle', 'Sitio web creado con SKY'))
    except WorkbenchInvalid as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/developer/workbench/packages/lookup', dependencies=[Depends(require_key)])
def developer_package_lookup(registry: str, name: str):
    from neural_core.sky_developer_workbench import (
        lookup_package, WorkbenchInvalid, RegistryUnavailable
    )
    try:
        return lookup_package(registry, name)
    except WorkbenchInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except RegistryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get('/api/developer/design/capabilities', dependencies=[Depends(require_key)])
def developer_design_capabilities():
    """Real local templates and explicit library manifests (no installations)."""
    from neural_core.sky_design_studio import studio_capabilities
    return studio_capabilities()


@app.post('/api/developer/design/create', dependencies=[Depends(require_key)])
def developer_design_create(body: dict):
    """Returns all editable web/app source files; does not touch owner's files."""
    from neural_core.sky_design_studio import create_design, DesignInvalid
    try:
        return create_design(body.get('title', ''), body.get('brief', ''),
                             platform=body.get('platform', 'react'),
                             domain=body.get('domain', ''),
                             style=body.get('style', 'auto'),
                             layout=body.get('layout', 'auto'))
    except DesignInvalid as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post('/api/developer/design/download', dependencies=[Depends(require_key)])
def developer_design_download(body: dict):
    """Owner-requested in-memory zip of generated files, without executing code."""
    from neural_core.sky_design_studio import create_design, design_archive, DesignInvalid
    try:
        project = create_design(body.get('title', ''), body.get('brief', ''),
                                platform=body.get('platform', 'react'),
                                domain=body.get('domain', ''),
                                style=body.get('style', 'auto'),
                                layout=body.get('layout', 'auto'))
        payload = design_archive(project)
    except DesignInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(content=payload, media_type='application/zip',
                    headers={'Content-Disposition':
                             f'attachment; filename="sky-design-{project["platform"]}.zip"',
                             'Cache-Control': 'no-store',
                             'X-Content-Type-Options': 'nosniff'})


# ==============================================================================
# SKY UNIVERSAL KNOWLEDGE & EDUCATION ENGINE ENDPOINTS
# ==============================================================================
@app.get('/api/academic/engines')
def academic_engines():
    """Devuelve la lista de los 25 motores especializados de educación y ciencia."""
    from neural_core.academic_core import list_academic_engines
    return {'ok': True, 'engines': list_academic_engines()}

@app.post('/api/academic/analyze')
def academic_analyze(body: dict):
    """Analiza una solicitud educativa o técnica identificando nivel y pedagogía."""
    from neural_core.academic_core import analyze_academic_request
    text = body.get('prompt', '') or body.get('text', '')
    return {'ok': True, 'analysis': analyze_academic_request(text)}

# ==============================================================================
# SKY DETERMINISTIC CAS & CODE EXECUTION ENDPOINTS
# ==============================================================================
@app.post('/api/math/cas')
def math_cas(body: dict):
    """Ejecuta cálculo simbólico determinista con SymPy (derivadas, integrales, límites, ecuaciones)."""
    from neural_core.math_engine import ejecutar_cas
    expr = body.get('expresion', '') or body.get('expression', '')
    op = body.get('operacion', 'auto')
    var = body.get('variable', 'x')
    punto = float(body.get('punto', 0.0))
    if not expr:
        return {'ok': False, 'error': 'Se requiere "expresion" para el cálculo.'}
    return ejecutar_cas(expr, operacion=op, variable=var, punto=punto)

@app.post('/api/developer/repl')
def developer_repl(body: dict):
    """Ejecuta código en el sandbox seguro Python REPL con SymPy, NumPy y SciPy."""
    from neural_core.math_engine import ejecutar_python_repl
    code = body.get('code', '') or body.get('codigo', '')
    timeout = float(body.get('timeout', 3.0))
    if not code:
        return {'ok': False, 'error': 'Se requiere "code" para ejecutar en REPL.'}
    return ejecutar_python_repl(code, timeout_segundos=timeout)

@app.post('/api/developer/audit')
def developer_audit(body: dict):
    """Audita código contra directivas DEV-CORE (Zero Placeholders, defensivo, Big-O)."""
    from neural_core.math_engine import auditar_codigo_fuente
    code = body.get('code', '') or body.get('codigo', '')
    lang = body.get('language', 'python')
    if not code:
        return {'ok': False, 'error': 'Se requiere "code" para auditar.'}
    return auditar_codigo_fuente(code, lenguaje=lang)

# ==============================================================================
# SKY SPORTS CENTER · REAL MADRID ENDPOINTS
# ==============================================================================
@app.get('/api/sports/madrid/match')
def sports_madrid_match():
    """Devuelve el partido en vivo o próximo del Real Madrid y canales oficiales."""
    from neural_core.sky_sports_madridista import consultar_partido_actual_madrid
    return {"ok": True, **consultar_partido_actual_madrid()}

@app.get('/api/sports/channels')
def sports_channels():
    """Devuelve la guía oficial de canales deportivos (ViX, ESPN, SKY Sports, RMTV)."""
    from neural_core.sky_sports_madridista import CANALES_DEPORTIVOS_OFICIALES
    return {"ok": True, "channels": CANALES_DEPORTIVOS_OFICIALES}

@app.post('/api/sports/predict')
def sports_predict(body: dict):
    """Calcula predicción deportiva con probabilidades de victoria y marcador probable."""
    from neural_core.sky_sports_madridista import generar_prediccion_deportiva
    local = body.get('equipo_local', 'Real Madrid')
    visitante = body.get('equipo_visitante', 'RB Leipzig')
    competicion = body.get('competicion', 'UEFA Champions League')
    return {"ok": True, "prediccion": generar_prediccion_deportiva(local, visitante, competicion)}

# ==============================================================================
# SKY IA UNIVERSAL v12.0 ENDPOINTS
# ==============================================================================
@app.post('/api/universal/plan')
def universal_plan(body: dict):
    """Genera el plan de ejecución y fuentes recomendadas por el Universal Engine."""
    from neural_core.sky_universal_engine import SkyUniversalEngine
    pregunta = body.get('prompt') or body.get('pregunta', '')
    area = body.get('area', 'General')
    plan = SkyUniversalEngine.clasificar_intencion(pregunta, area)
    return {
        "ok": True,
        "modo": plan.modo.value,
        "disciplina": plan.disciplina,
        "nivel_academico": plan.nivel_academico.value,
        "requiere_investigacion": plan.requiere_investigacion,
        "requiere_calculo_determinista": plan.requiere_calculo_determinista,
        "requiere_codigo": plan.requiere_codigo,
        "fuentes_recomendadas": [
            {"entidad": f.entidad, "pais_o_region": f.pais_o_region, "url": f.url_base, "descripcion": f.descripcion}
            for f in plan.fuentes_recomendadas
        ],
        "pasos": plan.pasos
    }

@app.post('/api/universal/factcheck')
def universal_factcheck(body: dict):
    """Audita afirmaciones, contrasta fuentes y valida cálculos deterministas."""
    from neural_core.factcheck_engine import SkyFactCheckEngine
    texto = body.get('texto', '')
    report = SkyFactCheckEngine.auditar_respuesta(texto)
    return {
        "ok": True,
        "total_afirmaciones": report.total_afirmaciones,
        "respaldadas": report.respaldadas,
        "contradictorias": report.contradictorias,
        "no_comprobadas": report.no_comprobadas,
        "desactualizadas": report.desactualizadas,
        "es_consistente": report.es_consistente,
        "calculos_verificados": report.calculos_verificados,
        "advertencia_incertidumbre": report.advertencia_incertidumbre,
        "detalles": [
            {
                "afirmacion": c.afirmacion,
                "tipo": c.tipo,
                "estado": c.estado.value,
                "fuente": c.fuente_corroborante,
                "observacion": c.observacion
            }
            for c in report.detalles
        ]
    }

@app.get('/api/universal/sources')
def universal_sources(disciplina: str = None):
    """Consulta el directorio mundial del Global Source Router."""
    from neural_core.sky_universal_engine import GLOBAL_SOURCES_REGISTRY
    if disciplina and disciplina.lower() in GLOBAL_SOURCES_REGISTRY:
        sources = GLOBAL_SOURCES_REGISTRY[disciplina.lower()]
    else:
        # Combinar todas las disciplinas
        sources = [s for sublist in GLOBAL_SOURCES_REGISTRY.values() for s in sublist]
    return {
        "ok": True,
        "sources": [
            {"entidad": s.entidad, "pais_o_region": s.pais_o_region, "categoria": s.categoria, "url": s.url_base, "descripcion": s.descripcion}
            for s in sources
        ]
    }

@app.post('/api/universal/memory/save')
def memory_save(body: dict):
    """Guarda una memoria de proyecto o preferencia bajo control del usuario."""
    from neural_core.smart_memory import get_smart_memory_manager
    categoria = body.get('categoria', 'preferencia')
    clave = body.get('clave', 'general')
    valor = body.get('valor', '')
    usuario_id = body.get('usuario_id', 'default_user')
    es_privado = body.get('es_privado', True)
    sm = get_smart_memory_manager()
    entry = sm.guardar_memoria(categoria, clave, valor, usuario_id, es_privado)
    return {"ok": True, "memoria_id": entry.id, "categoria": entry.categoria, "clave": entry.clave}

@app.get('/api/universal/memory/list')
def memory_list(usuario_id: str = 'default_user', categoria: str = None):
    """Recupera la lista de memorias de un usuario autorizado."""
    from neural_core.smart_memory import get_smart_memory_manager
    sm = get_smart_memory_manager()
    mems = sm.consultar_memorias(usuario_id=usuario_id, categoria=categoria)
    return {
        "ok": True,
        "total": len(mems),
        "memorias": [
            {"id": m.id, "categoria": m.categoria, "clave": m.clave, "valor": m.valor, "es_privado": m.es_privado, "modificado": m.modificado}
            for m in mems
        ]
    }

@app.delete('/api/universal/memory/{mem_id}')
def memory_delete(mem_id: str, usuario_id: str = 'default_user'):
    """Elimina una memoria específica por orden del usuario."""
    from neural_core.smart_memory import get_smart_memory_manager
    sm = get_smart_memory_manager()
    eliminado = sm.eliminar_memoria(mem_id, usuario_id)
    return {"ok": eliminado}

@app.get('/api/universal/memory/export')
def memory_export(usuario_id: str = 'default_user'):
    """Exporta en JSON el conjunto completo de memorias de un usuario."""
    from neural_core.smart_memory import get_smart_memory_manager
    from fastapi.responses import Response
    sm = get_smart_memory_manager()
    json_data = sm.exportar_memorias_json(usuario_id)
    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=sky_memories_{usuario_id}.json"}
    )

@app.get('/api/universal/benchmark')
def universal_benchmark():
    """Ejecuta la suite de evaluación benchmark multidisciplinaria."""
    from neural_core.eval_benchmark import ejecutar_evaluacion_benchmark
    resultados = ejecutar_evaluacion_benchmark()
    return {"ok": True, **resultados}











# SKY Skillpack: adaptadores autenticados (sin reemplazar la API actual).
@app.get('/api/skillpack/catalogue', dependencies=[Depends(require_key)])
def skillpack_catalogue():
    from neural_core.sky_skillpack import catalogue
    return catalogue()


@app.post('/api/skillpack/execute/{skill_id}', dependencies=[Depends(require_key)])
def skillpack_execute(skill_id: str, body: dict, request: Request):
    from neural_core.sky_skillpack import execute, SkillInvalid, SkillUnavailable
    # Cloud deployment and external posting require the owner's additional PIN
    # even when a caller already supplied a valid SKY API key.
    if (skill_id=="aws-workflow-deploy" and body.get("operation")=="deploy") or (
        skill_id=="slack-communicator" and body.get("operation")=="send"):
        from .sentinel import exigir_pin
        exigir_pin(request, "una acción externa irreversible de SKY")
    try:
        return execute(skill_id, body)
    except SkillInvalid as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SkillUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# Unified proof-based catalogues. Reuses the existing private FastAPI and
# SENTINEL authentication; does not introduce another server or exposed port.
@app.get("/api/sky/skills/audit", dependencies=[Depends(require_key)])
def sky_full_skills_audit():
    from neural_core.sky_skills_audit import audit
    return audit()


@app.get("/api/sky/quality/operational", dependencies=[Depends(require_key)])
def sky_quality_operational(period: str = "hoy"):
    from neural_core.sky_operational_quality import report
    try:
        return report(period)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/sky/skills/live-results", dependencies=[Depends(require_key)])
def sky_skill_live_results():
    from neural_core.sky_skill_probe import read
    return read()


@app.post("/api/sky/skills/probe/{skill_id}", dependencies=[Depends(require_key)])
def sky_skill_live_probe(skill_id: str):
    from neural_core.sky_skill_probe import probe
    try:
        return probe(skill_id)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


# Expansión opcional de SKY: sin crear una API nueva ni habilitar proveedores
# externos de forma automática. Todo utiliza la autenticación SKY existente.
class SKYResearchLookup(BaseModel):
    query: str = Field(min_length=3,max_length=220)
    limit: int = Field(default=5,ge=1,le=10)

class SKYZoteroLookup(BaseModel):
    query: str = Field(default="",max_length=160)
    limit: int = Field(default=10,ge=1,le=30)

class SKYWolframLookup(BaseModel):
    question: str = Field(min_length=3,max_length=180)
    units: str = Field(default="metric",pattern="^(metric|imperial)$")

class SKYWorkflowDispatch(BaseModel):
    alias: str = Field(min_length=2,max_length=50,pattern="^[a-z][a-z0-9_-]+$")
    approved: bool = False


@app.get("/api/sky/expansion/readiness",dependencies=[Depends(require_key)])
def sky_expansion_readiness():
    from neural_core.sky_research_connectors import readiness as research_status
    from neural_core.sky_n8n_bridge import readiness as n8n_status
    from neural_core.providers import provider_summary
    return {"ok":True,"research":research_status(),"n8n":n8n_status(),
            "models":[x for x in provider_summary() if x["id"] in ("openrouter","huggingface","ollama")],
            "external_live_verified":False,
            "existing_skills_and_api_preserved":True}


@app.post("/api/sky/expansion/research/semantic-scholar",dependencies=[Depends(require_key)])
def sky_semantic_scholar(body:SKYResearchLookup):
    from neural_core.sky_research_connectors import semantic_scholar,ResearchInputError,ResearchConnectorError
    try:
        return semantic_scholar(body.query,body.limit)
    except ResearchInputError as exc:
        raise HTTPException(422,str(exc)) from exc
    except ResearchConnectorError as exc:
        raise HTTPException(502,str(exc)) from exc


@app.post("/api/sky/expansion/research/zotero",dependencies=[Depends(require_key)])
def sky_zotero_lookup(body:SKYZoteroLookup):
    from neural_core.sky_research_connectors import zotero_items,ResearchInputError,ResearchConnectorError
    try:
        return zotero_items(body.query,body.limit)
    except ResearchInputError as exc:
        raise HTTPException(422,str(exc)) from exc
    except ResearchConnectorError as exc:
        raise HTTPException(503,str(exc)) from exc


@app.post("/api/sky/expansion/research/wolfram",dependencies=[Depends(require_key)])
def sky_wolfram_lookup(body:SKYWolframLookup):
    from neural_core.sky_research_connectors import wolfram_short_answer,ResearchInputError,ResearchConnectorError
    try:
        return wolfram_short_answer(body.question,body.units)
    except ResearchInputError as exc:
        raise HTTPException(422,str(exc)) from exc
    except ResearchConnectorError as exc:
        raise HTTPException(503,str(exc)) from exc


@app.get("/api/sky/expansion/n8n/workflows",dependencies=[Depends(require_key)])
def sky_n8n_workflows():
    from neural_core.sky_n8n_bridge import list_workflows,N8NInvalid,N8NUnavailable
    try:
        return list_workflows()
    except N8NInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except N8NUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc


@app.get("/api/sky/expansion/n8n/executions",dependencies=[Depends(require_key)])
def sky_n8n_executions():
    from neural_core.sky_n8n_bridge import recent_executions,N8NInvalid,N8NUnavailable
    try:
        return recent_executions()
    except N8NInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except N8NUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc


@app.post("/api/sky/expansion/n8n/dispatch",dependencies=[Depends(require_key)])
def sky_n8n_dispatch(body:SKYWorkflowDispatch,request:Request):
    from neural_core.sky_n8n_bridge import dispatch_webhook,N8NInvalid,N8NUnavailable
    from .sentinel import exigir_pin
    if body.approved is not True:
        raise HTTPException(422,"Se requiere aprobación explícita del propietario.")
    exigir_pin(request,"ejecución de automatización externa n8n")
    try:
        return dispatch_webhook(body.alias,approved=True)
    except N8NInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except N8NUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc


# SKY Extension Hub / Experience Learning — use existing SKY API, owner key
# and SENTINEL MFA. No package installation, shell access, auto-run or new ports.
class SKYExperienceCapture(BaseModel):
    cycle_id: str = Field(min_length=20,max_length=60)
    name: str = Field(min_length=3,max_length=60)
    approved: bool = False

class SKYExperiencePlan(BaseModel):
    device: str = Field(default="local",min_length=1,max_length=80)
    origin: str = Field(default="chat",pattern="^(chat|voz)$")

class SKYExperienceDelete(BaseModel):
    approved: bool = False


@app.get("/api/sky/extensions",dependencies=[Depends(require_key)])
def sky_extension_catalogue(category: str = ""):
    from neural_core.sky_extension_hub import catalogue
    try:
        return catalogue(category)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


class SKYExtensionInvoke(BaseModel):
    action: str = Field(min_length=2,max_length=20)
    arguments: dict = Field(default_factory=dict)
    approved: bool = False


@app.get("/api/sky/extensions/actions",dependencies=[Depends(require_key)])
def sky_extension_tool_actions():
    from neural_core.sky_extension_hub import callable_tools
    return {"tools":callable_tools(),"auto_execute":False}


@app.post("/api/sky/extensions/{extension_id}/invoke",dependencies=[Depends(require_key)])
def sky_extension_invoke(extension_id:str,body:SKYExtensionInvoke,request:Request):
    from neural_core.sky_extension_hub import invoke,ExtensionInvalid,ExtensionUnavailable
    from .sentinel import exigir_pin
    if body.approved is not True:
        raise HTTPException(422,"Necesito tu aprobación expresa.")
    # Chargeable models, web extraction and Wolfram require the owner PIN.
    if extension_id in {"openrouter","huggingface","firecrawl","wolfram"}:
        exigir_pin(request,"usar un proveedor externo con posible consumo")
    try:
        return invoke(extension_id,action=body.action,payload=body.arguments,approved=True)
    except ExtensionInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except ExtensionUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc


@app.get("/api/sky/extensions/{extension_id}",dependencies=[Depends(require_key)])
def sky_extension_details(extension_id: str):
    from neural_core.sky_extension_hub import extension
    try:
        item=extension(extension_id)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    if not item:
        raise HTTPException(404,"Extensión desconocida.")
    return item


@app.get("/api/sky/learning/capabilities",dependencies=[Depends(require_key)])
def sky_learning_capabilities():
    from neural_core.sky_extension_hub import learning_architecture
    return learning_architecture()


@app.get("/api/sky/learning/procedures",dependencies=[Depends(require_key)])
def sky_learning_procedures():
    from neural_core.sky_experience_learning import list_procedures
    return list_procedures()


@app.post("/api/sky/learning/capture",dependencies=[Depends(require_key)])
def sky_learning_capture(body:SKYExperienceCapture,request:Request):
    from .sentinel import exigir_pin
    from neural_core.sky_experience_learning import capture_verified,LearningInvalid,LearningUnavailable
    if body.approved is not True:
        raise HTTPException(422,"Debés aprobar expresamente el procedimiento.")
    exigir_pin(request,"guardar un procedimiento verificado de SKY")
    try:
        return capture_verified(body.cycle_id,body.name,approved=True)
    except LearningInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except LearningUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc


@app.post("/api/sky/learning/procedures/{procedure_id}/plan",dependencies=[Depends(require_key)])
def sky_learning_plan(procedure_id:str,body:SKYExperiencePlan):
    from neural_core.sky_experience_learning import plan_replay,LearningInvalid,LearningUnavailable
    try:
        plan=plan_replay(procedure_id,device=body.device,origin=body.origin)
        return {"tipo":"ciclo","ciclo":plan,"requires_confirmation_each_step":True,
                "message":"Procedimiento recuperado: SKY todavía no ejecutó ninguna acción."}
    except LearningInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except LearningUnavailable as exc:
        raise HTTPException(409,str(exc)) from exc


@app.delete("/api/sky/learning/procedures/{procedure_id}",dependencies=[Depends(require_key)])
def sky_learning_delete(procedure_id:str,body:SKYExperienceDelete,request:Request):
    from .sentinel import exigir_pin
    from neural_core.sky_experience_learning import delete,LearningInvalid,LearningUnavailable
    if body.approved is not True:
        raise HTTPException(422,"Confirmá que querés eliminar el procedimiento.")
    exigir_pin(request,"eliminar un procedimiento de SKY")
    try:
        return {"deleted":delete(procedure_id,approved=True)}
    except LearningInvalid as exc:
        raise HTTPException(422,str(exc)) from exc
    except LearningUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc
