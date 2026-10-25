"""SKY Creative Evolution API — rutas privadas en la API existente de SKY."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .api import require_key
from neural_core import sky_creative_evolution as studio

router=APIRouter(prefix="/api/creative/evolution",dependencies=[Depends(require_key)])


class Writing(BaseModel):
    kind:str=Field(max_length=20)
    title:str=Field(min_length=3,max_length=120)
    premise:str=Field(min_length=12,max_length=2500)
    locale:str=Field(default="es",max_length=24)
    genre:str=Field(default="aventura",max_length=25)
    provider:str=Field(default="auto",max_length=25)


class Revision(BaseModel):
    instruction:str=Field(min_length=8,max_length=1000)
    expected_version:int=Field(ge=1)
    provider:str=Field(default="auto",max_length=25)


class VisualPrompt(BaseModel):
    prompt:str=Field(min_length=8,max_length=2000)
    locale:str=Field(default="es",max_length=24)
    provider:str=Field(default="auto",max_length=25)
    mode:str=Field(default="image",max_length=10)


class ImageRequest(VisualPrompt):
    improve:bool=False
    cloud_authorized:bool=False


class MusicRequest(BaseModel):
    genre:str=Field(default="cinematic",max_length=20)
    mood:str=Field(default="hopeful",max_length=20)
    seconds:int=Field(default=12,ge=8,le=30)
    bpm:int=Field(default=100,ge=60,le=160)
    seed_text:str=Field(default="SKY",min_length=1,max_length=150)


class MovieRequest(BaseModel):
    title:str=Field(min_length=3,max_length=120)
    idea:str=Field(min_length=12,max_length=1300)
    locale:str=Field(default="es",max_length=24)
    provider:str=Field(default="auto",max_length=25)
    soundtrack:bool=False
    cloud_authorized:bool=False


def execute(operation):
    try:
        return operation()
    except (studio.CreativeInvalid,ValueError) as exc:
        raise HTTPException(422,detail=str(exc)[:180]) from exc
    except (studio.CreativeUnavailable,RuntimeError) as exc:
        raise HTTPException(503,detail=str(exc)[:180]) from exc
    except Exception as exc:
        # SDK errors can leak prompt/credentials: report generic failure.
        raise HTTPException(503,"El motor creativo no respondió. Verificá la configuración privada.") from exc


@router.get("/capabilities")
def capabilities():
    return studio.capabilities()


@router.get("/languages")
def languages():
    return {"languages":[{"code":k,"name":v,"writing":True,
                          "speech":"depends_on_installed_voice"} for k,v in studio.LANGUAGES.items()]}


@router.post("/writing",status_code=201)
def writing(body:Writing):
    return execute(lambda:studio.create_writing(**body.model_dump()))


@router.get("/writing")
def writing_list():
    return {"works":studio.list_works()}


@router.get("/writing/{ident}")
def writing_one(ident:str):
    result=studio.get_work(ident)
    if not result:
        raise HTTPException(404,"Obra no encontrada.")
    return result


@router.get("/writing/{ident}/versions")
def version_list(ident:str):
    return execute(lambda:{"versions":studio.versions(ident)})


@router.post("/writing/{ident}/revise")
def revise(ident:str,body:Revision):
    return execute(lambda:studio.revise_writing(
        ident,body.instruction,body.expected_version,provider=body.provider))


@router.post("/writing/{ident}/continue")
def continue_writing(ident:str,body:Revision):
    return execute(lambda:studio.continue_writing(
        ident,body.instruction,body.expected_version,provider=body.provider))


@router.post("/images/improve-prompt")
def improve_prompt(body:VisualPrompt):
    return execute(lambda:studio.improve_visual_prompt(**body.model_dump()))


@router.post("/images/generate",status_code=201)
def generate_image(body:ImageRequest):
    if body.cloud_authorized is not True:
        raise HTTPException(403,"Confirmá el uso de Gemini antes de enviar la descripción.")
    return execute(lambda:studio.generate_image(body.prompt,locale=body.locale,
                                                improve=body.improve,provider=body.provider))


@router.post("/music/generate",status_code=201)
def generate_music(body:MusicRequest):
    return execute(lambda:studio.save_music(**body.model_dump()))


@router.post("/movies/generate",status_code=202)
def movie(body:MovieRequest):
    if body.cloud_authorized is not True:
        raise HTTPException(403,"Confirmá Gemini para generar los fotogramas del montaje.")
    return execute(lambda:studio.movie_from_prompt(body.title,body.idea,locale=body.locale,
                              provider=body.provider,soundtrack=body.soundtrack))
