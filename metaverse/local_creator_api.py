"""API de generación local real ComfyUI; hereda clave y SENTINEL de SKY."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_comfyui_local as comfy

router = APIRouter(prefix="/api/creative/local", dependencies=[Depends(require_key)])


class LocalPrompt(BaseModel):
    kind: str = Field(pattern="^(image|video)$")
    prompt: str = Field(min_length=8,max_length=2000)


class DiffusersPrompt(BaseModel):
    prompt:str=Field(min_length=8,max_length=2000)
    width:int=Field(default=512)
    height:int=Field(default=512)
    steps:int=Field(default=22,ge=10,le=35)
    local_authorized:bool=False


@router.get("/diffusers/capabilities")
def diffusers_capabilities():
    from neural_core.sky_diffusers_local import capabilities
    return capabilities()


@router.post("/diffusers/image",status_code=201)
def diffusers_image(body:DiffusersPrompt):
    from neural_core.sky_diffusers_local import image,DiffusersUnavailable
    if not body.local_authorized:
        raise HTTPException(403,"Confirmá que querés ejecutar un modelo local con recursos del equipo.")
    try:
        return image(body.prompt,body.width,body.height,body.steps)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except DiffusersUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc


@router.get("/capabilities")
def capabilities():
    return comfy.capabilities()


@router.get("/check")
def check():
    try:
        return comfy.check()
    except (comfy.LocalMediaError, comfy.LocalMediaUnavailable) as ex:
        raise HTTPException(503,str(ex)) from ex


@router.post("/submit", status_code=202)
def submit(body: LocalPrompt):
    try:
        return comfy.submit(body.kind,body.prompt)
    except comfy.LocalMediaError as ex:
        raise HTTPException(422,str(ex)) from ex
    except comfy.LocalMediaUnavailable as ex:
        raise HTTPException(503,str(ex)) from ex


@router.get("/jobs/{ident}")
def job(ident: str):
    try:
        return comfy.status(ident)
    except comfy.LocalMediaError as ex:
        raise HTTPException(404,str(ex)) from ex
    except comfy.LocalMediaUnavailable as ex:
        raise HTTPException(503,str(ex)) from ex
    except Exception as ex:
        # No exponer rutas privadas del equipo ni detalles del workflow.
        raise HTTPException(503,"No se pudo importar el resultado local. Revisá el diagnóstico privado.") from ex
