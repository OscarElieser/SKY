"""API propia de SKY. Local, autenticada y explícitamente extensible.

Inicia con: python -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
"""
from __future__ import annotations
import os,secrets,time,asyncio,json,math
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException,Depends,WebSocket,WebSocketDisconnect,Request,Query
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
    val=os.getenv('SKY_API_KEY','').strip()
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
def require_key(token:Optional[str]=Depends(scheme)):
    if not token or not secrets.compare_digest(token,api_token()):
        raise HTTPException(401,detail='Clave SKY incorrecta',headers={'WWW-Authenticate':'APIKey'})
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

async def _creative_pump():
    from neural_core.sky_creative import run_next_job
    while True:
        try:await asyncio.to_thread(run_next_job)
        except Exception:pass
        await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app):
    api_token()
    demo_world()
    from neural_core.sky_creative import mark_interrupted
    mark_interrupted()
    pump=None
    creative_pump=asyncio.create_task(_creative_pump()) if os.getenv('SKY_CREATIVE_WORKER','1')=='1' else None
    if os.getenv('SKY_WORKFLOWS_ENABLED','1')=='1':
        pump=asyncio.create_task(_workflow_pump())
    try:
        yield
    finally:
        if creative_pump:
            creative_pump.cancel()
            try:await creative_pump
            except asyncio.CancelledError:pass
        if pump:
            pump.cancel()
            try:await pump
            except asyncio.CancelledError:pass

app=FastAPI(title='SKY Engine API',version='9.7.0',description='Interfaz local de SKY: mundos 3D, herramientas y motores autorizados.',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=STATIC),name='static')

@app.get('/office')
def office_home():return FileResponse(STATIC/'office.html')

class OfficeRequest(BaseModel):
    kind: str=Field(default='docx',max_length=5)
    title: str=Field(default='Mi creación SKY',max_length=160)
    prompt: str=Field(default='',max_length=6000)
    content: str=Field(default='',max_length=50000)
    csv: str=Field(default='',max_length=30000)
    headers: list=Field(default_factory=list,max_length=40)
    rows: list=Field(default_factory=list,max_length=300)
    template: str='general'
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
    provider=request.ai_provider.lower()
    if provider!='none':
        if provider not in ('gemini','openai','anthropic','ollama','mistral','groq','deepseek'):
            raise HTTPException(422,'Proveedor no disponible.')
        if not request.prompt.strip():raise HTTPException(422,'Añadí un tema para redactar con IA.')
        try:
            from neural_core.assistant import responder
            instructions=(f'Redactá un borrador estructurado en español para un documento tipo {request.kind} titulado '
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
    message:str=Field(min_length=1,max_length=6000)
    provider:str='local'
    area:str='Metaverso'

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
def index():return FileResponse(STATIC/'sky.html')

@app.get('/sky')
def sky_home():return FileResponse(STATIC/'sky.html')

@app.get('/flows')
def workflows_page():return FileResponse(STATIC/'flows.html')

@app.get('/owner/baqueano')
def baqueano_owner_page():return FileResponse(STATIC/'baqueano-owner.html')

@app.get('/world')
def metaverse_world():return FileResponse(STATIC/'index.html')

@app.get('/api/health')
def health():return {'service':'SKY Engine API','status':'ok','version':'9.7.0','private':'key required for data'}

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

@app.post('/api/chat',dependencies=[Depends(require_key)])
def chat(body:ChatRequest):
    from neural_core.sky_agent import interpret_local_command
    local=interpret_local_command(body.message)
    if local is not None:return {'provider':'sky-local','answer':local}
    if body.provider=='local':
        return {'provider':'sky-local','answer':'SKY local puede generar mundos por descripción, guardar escenarios, exportar GLB y usar /sky calcula, /sky metas o /sky hora. Para diálogo abierto, configurá Ollama, Gemini, OpenAI u otro motor en SKY y elegilo aquí.'}
    try:
        from neural_core.assistant import responder
        answer,_=responder(body.message,body.area,proveedor=body.provider)
        return {'provider':body.provider,'answer':answer}
    except Exception as exc:
        # No leaked credentials or SDK tracebacks
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
        record(request.url.path,(time.perf_counter()-start)*1000,response.status_code)
        return response
    except Exception:
        record(request.url.path,(time.perf_counter()-start)*1000,500)
        raise

# v9.3: flujos autónomos locales, privilegios exclusivos del creador.
from .workflow_api import router as workflow_router
app.include_router(workflow_router)
from .intelligent_api import router as sky_intelligent_router
app.include_router(sky_intelligent_router)

# SKY v9.7: editor profesional por capas + renders multimedia, propietario solamente.
from .creative_api import router as creative_router
app.include_router(creative_router)
