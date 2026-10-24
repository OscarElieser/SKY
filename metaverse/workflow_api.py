"""Owner-only routes; every action requires the local master key.
Community Bearer tokens do not grant SKY Workflows or BAQUEANO privileges.
"""
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from typing import Any
from .api import require_key
from neural_core import sky_workflows as wf

router=APIRouter(prefix='/api/sky',dependencies=[Depends(require_key)])

class Step(BaseModel):
    agent:str=Field(min_length=3,max_length=30)
    action:str=Field(min_length=3,max_length=30)
    task:str=Field(min_length=6,max_length=3000)
    params:dict[str,Any]=Field(default_factory=dict)

class Workflow(BaseModel):
    name:str=Field(min_length=3,max_length=120)
    project_id:str|None=None
    steps:list[Step]=Field(min_length=1,max_length=8)
    run_at:str|None=None
    interval_minutes:int|None=Field(default=None,ge=1,le=10080)
    max_attempts:int=Field(default=3,ge=1,le=5)

class Approval(BaseModel):
    approve:bool=False
    expected_fingerprint:str|None=None
class Retry(BaseModel):acknowledge_partial_effects:bool=False

from neural_core import sky_subagents as subagents


class SubagentCreate(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    mission: str = Field(min_length=10, max_length=1200)
    role: str = Field(min_length=3, max_length=35)


class SubagentDelegate(BaseModel):
    task: str = Field(min_length=6, max_length=3000)
    params: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None


@router.get('/subagents/catalogue')
def subagent_catalogue():
    return subagents.catalogue()


@router.post('/subagents', status_code=201)
def create_subagent(body: SubagentCreate):
    try:
        return subagents.create(body.name, body.mission, body.role)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('/subagents')
def list_subagents():
    return subagents.list_all()


@router.get('/subagents/{ident}')
def subagent_detail(ident: str):
    item = subagents.get(ident)
    if not item:
        raise HTTPException(404, 'Subagente no encontrado.')
    return item


@router.post('/subagents/{ident}/enable')
def enable_subagent(ident: str):
    try:
        return subagents.set_enabled(ident, True)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post('/subagents/{ident}/disable')
def disable_subagent(ident: str):
    try:
        return {**subagents.set_enabled(ident, False),
                'notice': 'Se bloquean nuevas delegaciones. Revisá y cancelá por separado los flujos ya aprobados.'}
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get('/subagents/{ident}/delegations')
def list_subagent_delegations(ident: str):
    try:
        return subagents.history(ident)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post('/subagents/{ident}/delegate', status_code=201)
def delegate_subagent(ident: str, body: SubagentDelegate):
    try:
        return subagents.delegate(ident, body.task, body.params, body.project_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get('/workflows/catalogue')
def catalogue():
    return {'agents':wf.ROLE_ACTION,'actions':list(wf.SAFE_ACTIONS),
            'sensitive_actions':'BAQUEANO, pagos, despliegues y comandos del sistema no están automatizados'}

@router.get('/workflows/status')
def engine_status():return wf.status()

@router.post('/workflows',status_code=201)
def create(body:Workflow):
    try:return wf.create(body.name,[x.model_dump() for x in body.steps],body.project_id,
                         body.run_at,body.interval_minutes,body.max_attempts)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')
    except ValueError as exc:raise HTTPException(422,str(exc))

@router.get('/workflows')
def listing():return wf.list_all()

@router.get('/workflows/{ident}/preview')
def preview(ident:str):
    try:return wf.preview(ident)
    except KeyError:raise HTTPException(404,'Flujo no encontrado')

@router.get('/workflows/{ident}')
def detail(ident:str):
    value=wf.get(ident)
    if value is None:raise HTTPException(404,'Flujo no encontrado')
    return value

@router.get('/workflows/{ident}/events')
def events(ident:str):
    try:return wf.history(ident)
    except KeyError:raise HTTPException(404,'Flujo no encontrado')

@router.post('/workflows/{ident}/approve')
def approve(ident:str,body:Approval):
    if not body.approve:raise HTTPException(403,'Se requiere una aprobación explícita')
    try:return wf.approve(ident,body.expected_fingerprint)
    except KeyError:raise HTTPException(404,'Flujo no encontrado')
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@router.post('/workflows/{ident}/pause')
def pause(ident:str):
    try:return wf.pause(ident)
    except KeyError:raise HTTPException(404,'Flujo no encontrado')
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@router.post('/workflows/{ident}/resume')
def resume(ident:str):
    try:return wf.resume(ident)
    except KeyError:raise HTTPException(404,'Flujo no encontrado')
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@router.get('/projects/{pid}/continuity')
def continuity(pid:str):
    try:return wf.project_continuity(pid)
    except KeyError:raise HTTPException(404,'Proyecto no encontrado')

@router.post('/workflows/{ident}/cancel')
def cancel(ident:str):
    try:return wf.cancel(ident)
    except KeyError:raise HTTPException(404,'Flujo no encontrado')
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@router.post('/workflows/{ident}/retry')
def retry(ident:str,body:Retry):
    try:return wf.retry(ident,body.acknowledge_partial_effects)
    except KeyError:raise HTTPException(404,'Flujo no encontrado')
    except PermissionError as exc:raise HTTPException(403,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@router.get('/owner/baqueano')
def baqueano_owner():
    # No administrative secret or privileged direct write; only authenticated owner sees this.
    return {'name':'BAQUEANO Control Center','visibility':'creator_only',
            'creator':'Oscar Elieser Chamorro Guzmán',
            'repository':'https://github.com/OscarElieser/APP-BAQUEANO',
            'site':'https://baqueanonicaragua.com/',
            'access':'owner SKY master key','actions':['Abrir web','Revisar código','Preparar cambios en el Workbench'],
            'production_changed':False}
