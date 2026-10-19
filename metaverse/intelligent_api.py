"""Propietario: chat unificado y generación coordinada sin mostrar módulos internos."""
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .api import require_key
from neural_core import sky_intelligent as intelligent
from .workspace_api import assist, AssistInput

router=APIRouter(prefix='/api/sky/intelligent',dependencies=[Depends(require_key)])

class Message(BaseModel):
    message:str=Field(min_length=2,max_length=5000)
    provider:str='local'
    language:str='es'
    project_id:str|None=None
    share_project_context:bool=False
    share_project_history:bool=False

class PlanRevision(BaseModel):
    instruction:str=Field(min_length=8,max_length=1500)
    expected_fingerprint:str=Field(min_length=64,max_length=64)

class ArtifactRevision(BaseModel):
    source_item_id:str=Field(min_length=8,max_length=96)
    instruction:str=Field(min_length=8,max_length=3000)

class RevisionApproval(BaseModel):
    approve:bool=False
    expected_fingerprint:str=Field(min_length=64,max_length=64)

class Approval(BaseModel):
    approve:bool=False
    expected_fingerprint:str=Field(min_length=64,max_length=64)

@router.post('/message')
def message(body:Message):
    from neural_core.sky_languages import normalize
    try:requested_language=normalize(body.language,strict=True)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    if intelligent.creation_intent(body.message):
        try:
            draft=intelligent.prepare(body.message,body.project_id)
        except KeyError:raise HTTPException(404,'Proyecto no encontrado')
        except ValueError as exc:raise HTTPException(422,str(exc))
        return {'type':'proposal','request':intelligent.status(draft['id']),
                'answer':'Preparé un plan local con etapas y resultados previstos. Revisá la propuesta antes de autorizar la ejecución.'}
    return {'type':'answer',**assist(AssistInput(message=body.message,provider=body.provider,
                       project_id=body.project_id,language=requested_language,share_project_context=body.share_project_context,
                       share_project_history=body.share_project_history,save_to_project=bool(body.project_id)))}

@router.get('/requests')
def requests():
    return [intelligent.status(x['id']) for x in intelligent.recent()]

@router.get('/requests/{ident}')
def request(ident:str):
    try:return intelligent.status(ident)
    except KeyError:raise HTTPException(404,'Solicitud no encontrada')

@router.post('/requests/{ident}/approve')
def approve(ident:str,body:Approval):
    try:return intelligent.approve(ident,body.expected_fingerprint,body.approve)
    except PermissionError as exc:raise HTTPException(403,str(exc))
    except KeyError:raise HTTPException(404,'Solicitud no encontrada')
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@router.get('/requests/{ident}/conversation')
def conversation(ident:str):
    try:return intelligent.conversation(ident)
    except KeyError:raise HTTPException(404,'Solicitud no encontrada')

@router.post('/requests/{ident}/revise-plan')
def revise_plan(ident:str,body:PlanRevision):
    try:return intelligent.revise_plan(ident,body.expected_fingerprint,body.instruction)
    except KeyError:raise HTTPException(404,'Solicitud no encontrada')
    except ValueError as exc:raise HTTPException(422,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))

@router.post('/requests/{ident}/revisions')
def prepare_artifact_revision(ident:str,body:ArtifactRevision):
    try:return intelligent.prepare_revision(ident,body.source_item_id,body.instruction)
    except (KeyError,):raise HTTPException(404,'Entregable o solicitud no encontrado')
    except PermissionError as exc:raise HTTPException(403,str(exc))
    except ValueError as exc:raise HTTPException(422,str(exc))

@router.get('/revisions/{ident}')
def revision_status(ident:str):
    try:return intelligent.revision(ident)
    except KeyError:raise HTTPException(404,'Revisión no encontrada')

@router.post('/revisions/{ident}/approve')
def approve_artifact_revision(ident:str,body:RevisionApproval):
    try:return intelligent.approve_revision(ident,body.expected_fingerprint,body.approve)
    except KeyError:raise HTTPException(404,'Revisión no encontrada')
    except PermissionError as exc:raise HTTPException(403,str(exc))
    except RuntimeError as exc:raise HTTPException(409,str(exc))
