"""Controlador privado del estudio multimedia. Ninguna ruta entrega archivos sin la clave maestra."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Query
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from .api import require_key,STATIC
from neural_core import sky_creative as cr

router=APIRouter()

class GenerateVisual(BaseModel):
    prompt:str=Field(min_length=4,max_length=3500)
    provider:str=Field(default='gemini',max_length=24)

class Creation(BaseModel):
    kind:str
    name:str=Field(min_length=1,max_length=120)
    spec:dict[str,Any]
    sky_project_id:str|None=None

class EditInstruction(BaseModel):
    instruction:str=Field(min_length=3,max_length=700)
    expected_version:int=Field(ge=1)

class Selection(BaseModel):
    rectangle:list[int]=Field(min_length=4,max_length=4)
    iterations:int=Field(default=4,ge=1,le=7)

class Revision(BaseModel):
    spec:dict[str,Any]
    expected_version:int=Field(ge=1)

@router.get('/creative')
def creative_page():return FileResponse(STATIC/'creative.html')

@router.get('/api/creative/capabilities',dependencies=[Depends(require_key)])
def capabilities():
    import shutil
    return {'image':True,'video':bool(shutil.which('ffmpeg') and shutil.which('ffprobe')),
            'formats':{'image':['png','jpg','webp'],'video':['mp4']},'non_destructive':True,
            'advanced_AI_generation':False,'layer_masks':True,'caption_keyframes':True,'assisted_grabcut':True,'limits':{'upload_bytes':cr.MAX_IMPORT,'video_seconds':600}}

@router.post('/api/creative/generate-image',dependencies=[Depends(require_key)],status_code=201)
def ai_image(body:GenerateVisual):
    if body.provider!='gemini':raise HTTPException(422,'Este motor acepta solo Gemini con permiso explícito')
    from neural_core.gemini_provider import generar_imagen,GeminiError
    try:
        binary,mime=generar_imagen(body.prompt)
        ext={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}.get(mime)
        if not ext:raise HTTPException(422,'Formato de imagen generado no compatible')
        return cr.ingest(binary,'SKY_IA_generada'+ext)
    except GeminiError as ex:raise HTTPException(503,str(ex)[:350]) from ex
    except ValueError as ex:raise HTTPException(422,str(ex)) from ex

@router.post('/api/creative/assets',dependencies=[Depends(require_key)],status_code=201)
async def asset_upload(file:UploadFile=File(...)):
    try:
        payload=await file.read(cr.MAX_IMPORT+1)
        return cr.ingest(payload,file.filename or 'archivo')
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    finally:await file.close()

@router.get('/api/creative/assets',dependencies=[Depends(require_key)])
def assets(kind:str|None=None):
    try:return cr.list_assets(kind)
    except ValueError as exc:raise HTTPException(422,str(exc))

@router.get('/api/creative/assets/{aid}/download',dependencies=[Depends(require_key)])
def download_asset(aid:str):
    try:path,item=cr.asset_path(aid)
    except (KeyError,FileNotFoundError):raise HTTPException(404,'Archivo no disponible')
    return FileResponse(path,filename=item['filename'],media_type=item['mimetype'])

@router.get('/api/creative/assets/{aid}/preview',dependencies=[Depends(require_key)])
def preview_asset(aid:str):
    try:path,item=cr.asset_path(aid)
    except (KeyError,FileNotFoundError):raise HTTPException(404,'Archivo no disponible')
    return FileResponse(path,media_type=item['mimetype'],headers={'Cache-Control':'private,no-store'})

@router.post('/api/creative/assets/{aid}/selection',dependencies=[Depends(require_key)],status_code=201)
def assisted_selection(aid:str,body:Selection):
    from neural_core.sky_advanced_creative import cutout_mask
    try:return cutout_mask(aid,body.rectangle,body.iterations)
    except KeyError:raise HTTPException(404,'Recurso no encontrado')
    except ValueError as ex:raise HTTPException(422,str(ex)) from ex
    except RuntimeError as ex:raise HTTPException(503,str(ex)) from ex

@router.post('/api/creative/projects',dependencies=[Depends(require_key)],status_code=201)
def create(body:Creation):
    try:return cr.create_project(body.kind,body.name,body.spec,body.sky_project_id)
    except KeyError as ex:raise HTTPException(404,str(ex))
    except (ValueError,RuntimeError) as ex:raise HTTPException(422,str(ex))

@router.get('/api/creative/projects',dependencies=[Depends(require_key)])
def projects():return cr.list_projects()

@router.get('/api/creative/projects/{pid}',dependencies=[Depends(require_key)])
def project(pid:str):
    p=cr.get_project(pid)
    if not p:raise HTTPException(404,'Proyecto no encontrado')
    return p

@router.put('/api/creative/projects/{pid}',dependencies=[Depends(require_key)])
def revise(pid:str,body:Revision):
    try:return cr.update_project(pid,body.spec,body.expected_version)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')
    except RuntimeError as ex:raise HTTPException(409,str(ex))
    except ValueError as ex:raise HTTPException(422,str(ex))

@router.post('/api/creative/projects/{pid}/command',dependencies=[Depends(require_key)])
def natural_instruction(pid:str,body:EditInstruction):
    try:return cr.apply_instruction(pid,body.instruction,body.expected_version)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')
    except RuntimeError as ex:raise HTTPException(409,str(ex))
    except ValueError as ex:raise HTTPException(422,str(ex))

@router.get('/api/creative/projects/{pid}/portable',dependencies=[Depends(require_key)])
def portable(pid:str):
    from fastapi.responses import Response
    try:data,name=cr.export_portable(pid)
    except KeyError:raise HTTPException(404,'Proyecto inexistente')
    except ValueError as ex:raise HTTPException(422,str(ex))
    return Response(data,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{name}"'})

@router.post('/api/creative/portable',dependencies=[Depends(require_key)],status_code=201)
async def import_project(file:UploadFile=File(...)):
    try:return cr.import_portable(await file.read(120*1024*1024+1))
    except ValueError as ex:raise HTTPException(422,str(ex)) from ex
    finally:await file.close()

@router.get('/api/creative/projects/{pid}/versions',dependencies=[Depends(require_key)])
def revisions(pid:str):
    if not cr.get_project(pid):raise HTTPException(404,'Proyecto inexistente')
    return cr.versions(pid)

@router.post('/api/creative/projects/{pid}/image/render',dependencies=[Depends(require_key)])
def image_render(pid:str,format:str='png'):
    if format not in ('png','jpg','webp'):raise HTTPException(422,'Formato inválido')
    try:return cr.image_export(pid,format)
    except (KeyError,FileNotFoundError):raise HTTPException(404,'Proyecto o archivo inexistente')
    except (RuntimeError,ValueError) as ex:raise HTTPException(422,str(ex))

@router.post('/api/creative/projects/{pid}/video/render',dependencies=[Depends(require_key)])
def video_render(pid:str):
    try:return cr.queue_video(pid)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')
    except ValueError as ex:raise HTTPException(422,str(ex))

@router.get('/api/creative/projects/{pid}/exports',dependencies=[Depends(require_key)])
def export_history(pid:str):
    if not cr.get_project(pid):raise HTTPException(404,'Proyecto inexistente')
    return cr.exports(pid)

@router.get('/api/creative/jobs',dependencies=[Depends(require_key)])
def jobs():return cr.list_jobs()

@router.get('/api/creative/jobs/{jid}',dependencies=[Depends(require_key)])
def job(jid:str):
    v=cr.job_info(jid)
    if not v:raise HTTPException(404,'Trabajo inexistente')
    return v

@router.post('/api/creative/jobs/{jid}/retry',dependencies=[Depends(require_key)])
def retry(jid:str):
    try:return cr.retry_job(jid)
    except RuntimeError as ex:raise HTTPException(409,str(ex))

@router.post('/api/creative/jobs/{jid}/cancel',dependencies=[Depends(require_key)])
def cancel(jid:str):
    if not cr.cancel_job(jid):raise HTTPException(409,'Solo se puede cancelar una tarea en cola')
    return cr.job_info(jid)
