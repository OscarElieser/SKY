"""API del Workbench SKY v9. Todas las rutas privadas requieren clave maestra.

No comparte la clave maestra con el metaverso social; está destinada al propietario.
"""
from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import FileResponse,HTMLResponse,Response
from pydantic import BaseModel,Field
from typing import Any
from .api import require_key,STATIC
from neural_core.sky_roles import ROLES,select_roles,plan_for
from neural_core.sky_workbench import (create_item,list_items,get_item,execute_item,read_file,
      list_notes,forget_note,get_experience,list_experiences,audit_events,ALLOWED_ACTIONS)
from neural_core.sky_experience import make_experience,experience_html,TEMPLATES,PALETTES
from neural_core.sky_telemetry import activity
from neural_core.sky_integrations import integration_status

router=APIRouter()

class PlanInput(BaseModel):
    task:str=Field(min_length=6,max_length=6000)
    action:str=Field(default='plan',max_length=16)
    params:dict[str,Any]=Field(default_factory=dict)

class ExperienceInput(BaseModel):
    prompt:str=Field(min_length=1,max_length=6000)
    options:dict[str,Any]=Field(default_factory=dict)

class Confirmation(BaseModel):
    approve:bool=False

@router.get('/studio')
def studio():return FileResponse(STATIC/'studio.html')

@router.get('/api/sky/roles',dependencies=[Depends(require_key)])
def roles():
    return {'count':len(ROLES),'roles':[{'id':r.id,'title':r.title,'description':r.description,'skills':r.skills} for r in ROLES.values()],
      'role_scope':'Asistencia especializada mediante métodos y herramientas; no son profesionales humanos certificados'}

@router.get('/api/sky/actions',dependencies=[Depends(require_key)])
def actions():return {'actions':ALLOWED_ACTIONS}

@router.post('/api/sky/plan',dependencies=[Depends(require_key)])
def plan(body:PlanInput):
    try:return plan_for(body.task)
    except ValueError as exc:raise HTTPException(422,str(exc))

@router.post('/api/sky/tasks',dependencies=[Depends(require_key)],status_code=201)
def new_task(body:PlanInput):
    try:return create_item(body.task,body.action,body.params)
    except ValueError as exc:raise HTTPException(422,str(exc))

@router.get('/api/sky/tasks',dependencies=[Depends(require_key)])
def tasks():return list_items()

@router.get('/api/sky/tasks/{ident}',dependencies=[Depends(require_key)])
def task(ident:str):
    result=get_item(ident)
    if not result:raise HTTPException(404,'Tarea no encontrada')
    return result

@router.post('/api/sky/tasks/{ident}/execute',dependencies=[Depends(require_key)])
def execute(ident:str,body:Confirmation):
    try:return execute_item(ident,body.approve)
    except PermissionError as exc:raise HTTPException(403,str(exc))
    except KeyError as exc:raise HTTPException(404,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))
    except (ValueError,ImportError) as exc:raise HTTPException(422,str(exc))

@router.get('/api/sky/files/{ident}',dependencies=[Depends(require_key)])
def files(ident:str):
    try:path,mime=read_file(ident)
    except KeyError:raise HTTPException(404,'Archivo no encontrado')
    return FileResponse(path,media_type=mime,filename=path.name.split('_',1)[1])

@router.post('/api/sky/experiences/preview',dependencies=[Depends(require_key)])
def preview(body:ExperienceInput):
    try:spec=make_experience(body.prompt,body.options)
    except ValueError as exc:raise HTTPException(422,str(exc))
    return {'spec':spec,'html':experience_html(spec)}

@router.get('/api/sky/experiences',dependencies=[Depends(require_key)])
def experiences():return list_experiences()

@router.get('/api/sky/experiences/{ident}',dependencies=[Depends(require_key)])
def experience(ident:str):
    result=get_experience(ident)
    if not result:raise HTTPException(404,'Diseño no encontrado')
    return result

@router.get('/api/sky/experiences/{ident}/html',dependencies=[Depends(require_key)])
def experience_file(ident:str):
    result=get_experience(ident)
    if not result:raise HTTPException(404,'Diseño no encontrado')
    return Response(content=experience_html(result),media_type='text/html',headers={
        'Content-Disposition':f'attachment; filename="SKY_Experience_{ident[-8:]}.html"',
        'Content-Security-Policy':"sandbox; default-src 'none'; style-src 'unsafe-inline'"})

@router.get('/api/sky/memory',dependencies=[Depends(require_key)])
def memories():return list_notes()

@router.delete('/api/sky/memory/{ident}',dependencies=[Depends(require_key)])
def delete_memory(ident:str):
    if not forget_note(ident):raise HTTPException(404,'Nota no encontrada')
    return {'deleted':ident}

@router.get('/api/sky/activity',dependencies=[Depends(require_key)])
def get_activity():return activity()

@router.get('/api/sky/integrations',dependencies=[Depends(require_key)])
def get_integrations():
    return integration_status()

@router.get('/api/sky/audit',dependencies=[Depends(require_key)])
def audit():return audit_events()

@router.get('/api/sky/creator/options',dependencies=[Depends(require_key)])
def creative_options():return {'templates':{k:v['label'] for k,v in TEMPLATES.items()},'palettes':list(PALETTES)}

class AssistInput(BaseModel):
    message:str=Field(min_length=2,max_length=6000)
    provider:str=Field(default='local',max_length=30)
    include_memory:bool=False
    project_id:str|None=None
    share_project_context:bool=False
    save_to_project:bool=False
    share_project_history:bool=False

@router.post('/api/sky/assist',dependencies=[Depends(require_key)])
def assist(body:AssistInput):
    """Asistente orientado a roles. Nunca invoca herramientas sin confirmación.

    Los roles y planes operan sin nube. Un proveedor externo se usa solo si fue
    seleccionado; la memoria opt-in debe activarse para compartirla.
    """
    selected=select_roles(body.message)
    from neural_core import sky_projects as ph
    brief_text=''
    if body.project_id:
        if not ph.project(body.project_id):raise HTTPException(404,'Proyecto no encontrado')
        if body.share_project_context:brief_text=ph.context(body.project_id)
    if body.provider=='local':
        answer=('SKY preparó un plan verificable para tu solicitud. '
                'Podés generar un diseño, crear un mundo o preparar documentos desde este proyecto.')
        if brief_text:answer+='\n\nContexto del proyecto (local):\n'+brief_text
        if body.project_id and body.save_to_project:
            ph.add_exchange(body.project_id,body.message,answer,'local')
        return {'provider':'sky-local','roles':selected,'plan':plan_for(body.message,selected),'answer':answer}
    if body.provider not in {'gemini','openai','anthropic','ollama','mistral','groq','deepseek'}:
        raise HTTPException(422,'Proveedor no permitido')
    system=('Sos SKY IA, asistente personal especializado. Adaptate a los siguientes roles: '
            +', '.join(r['title'] for r in selected)+'. Respondé en español con soluciones precisas y accionables. '
            'No afirmés haber creado archivos, desplegado software ni consultado datos en vivo si no lo hiciste. '
            'Si el pedido implica tareas sensibles, explicá qué autorizaciones necesitarías. '
            'No se ejecutan acciones mediante esta ruta. ')
    if body.include_memory:
        notes=list_notes()[:8]
        if notes:
            memory='; '.join(n['label']+': '+n['content'][:300] for n in notes)
            system+='Notas privadas que el usuario autorizó compartir: '+memory[:2400]
    if brief_text:
        system+='Contexto del proyecto expresamente autorizado para este proveedor: '+brief_text
    messages_for_model=[{'role':'system','content':system}]
    if body.project_id and body.share_project_history:
        for entry in ph.messages(body.project_id,limit=12):
            messages_for_model.append({'role':entry['role'],'content':entry['content'][:1500]})
    messages_for_model.append({'role':'user','content':body.message})
    try:
        from neural_core.providers import reply
        answer=reply(messages_for_model,body.provider)
    except Exception as exc:
        raise HTTPException(503,'El proveedor no está disponible ('+type(exc).__name__+').') from exc
    if body.project_id and body.save_to_project:
        ph.add_exchange(body.project_id,body.message,answer,body.provider)
    return {'provider':body.provider,'roles':selected,'answer':answer}

# SKY v9.2 Project Hub: las rutas se agregan al mismo router protegido por API key.
from neural_core import sky_projects as ph

class ProjectInput(BaseModel):
    title:str=Field(min_length=1,max_length=120)
    description:str=Field(default='',max_length=3000)

class ProjectUpdate(ProjectInput):
    expected_version:int=Field(ge=1)

class ProjectLink(BaseModel):
    kind:str=Field(max_length=30)
    ref:str=Field(max_length=96)
    label:str=Field(min_length=1,max_length=160)

class ProjectNote(BaseModel):
    title:str=Field(min_length=1,max_length=120)
    content:str=Field(min_length=1,max_length=6000)

@router.post('/api/sky/projects',dependencies=[Depends(require_key)],status_code=201)
def create_sky_project(body:ProjectInput):
    try:return ph.create_project(body.title,body.description)
    except ValueError as e:raise HTTPException(422,str(e))

@router.get('/api/sky/projects',dependencies=[Depends(require_key)])
def projects():return ph.list_projects()

@router.get('/api/sky/projects/{pid}',dependencies=[Depends(require_key)])
def project_detail(pid:str):
    try:return ph.brief(pid)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')

@router.put('/api/sky/projects/{pid}',dependencies=[Depends(require_key)])
def project_update(pid:str,body:ProjectUpdate):
    try:return ph.update_project(pid,body.title,body.description,body.expected_version)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')
    except RuntimeError as e:raise HTTPException(409,str(e))
    except ValueError as e:raise HTTPException(422,str(e))

@router.post('/api/sky/projects/{pid}/tasks',dependencies=[Depends(require_key)],status_code=201)
def create_project_task(pid:str,body:PlanInput):
    if not ph.project(pid):raise HTTPException(404,'Proyecto no encontrado')
    try:
        task=create_item(body.task,body.action,body.params)
        ph.link(pid,'task',task['id'],body.params.get('title') or body.task[:120])
        return task
    except ValueError as e:raise HTTPException(422,str(e))

@router.post('/api/sky/projects/{pid}/links',dependencies=[Depends(require_key)],status_code=201)
def project_link(pid:str,body:ProjectLink):
    from neural_core.sky_workbench import get_item,get_experience
    from metaverse.store import get_world
    check={'task':get_item,'experience':get_experience,'world':get_world}
    if body.kind not in check:raise HTTPException(422,'Tipo de enlace no permitido')
    if not ph.project(pid):raise HTTPException(404,'Proyecto no encontrado')
    if not check[body.kind](body.ref):raise HTTPException(404,'El entregable no existe')
    try:return ph.link(pid,body.kind,body.ref,body.label)
    except ValueError as e:raise HTTPException(422,str(e))

@router.delete('/api/sky/projects/{pid}/links/{lid}',dependencies=[Depends(require_key)])
def unlink_project_item(pid:str,lid:str):
    if not ph.unlink(pid,lid):raise HTTPException(404,'Enlace no encontrado')
    return {'removed':lid}

@router.post('/api/sky/projects/{pid}/notes',dependencies=[Depends(require_key)],status_code=201)
def project_note(pid:str,body:ProjectNote):
    try:return ph.add_note(pid,body.title,body.content)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')
    except ValueError as e:raise HTTPException(422,str(e))

@router.get('/api/sky/projects/{pid}/notes',dependencies=[Depends(require_key)])
def project_notes(pid:str):
    if not ph.project(pid):raise HTTPException(404,'Proyecto no encontrado')
    return ph.notes(pid)

@router.delete('/api/sky/projects/{pid}/notes/{nid}',dependencies=[Depends(require_key)])
def project_note_delete(pid:str,nid:str):
    if not ph.delete_note(pid,nid):raise HTTPException(404,'Nota no encontrada')
    return {'removed':nid}

@router.get('/api/sky/projects/{pid}/messages',dependencies=[Depends(require_key)])
def project_messages(pid:str):
    if not ph.project(pid):raise HTTPException(404,'Proyecto no encontrado')
    return ph.messages(pid)

@router.delete('/api/sky/projects/{pid}/messages',dependencies=[Depends(require_key)])
def delete_project_messages(pid:str):
    if not ph.project(pid):raise HTTPException(404,'Proyecto no encontrado')
    return {'removed':ph.clear_messages(pid)}

@router.get('/api/sky/projects/{pid}/export.zip',dependencies=[Depends(require_key)])
def export_project(pid:str):
    try:data,name=ph.export_zip(pid)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')
    except ValueError as e:raise HTTPException(422,str(e))
    return Response(content=data,media_type='application/zip',headers={
        'Content-Disposition':f'attachment; filename="{name}"',
        'Cache-Control':'no-store'})
