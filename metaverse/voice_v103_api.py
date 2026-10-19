"""Opt-in, authenticated local-only speech. No credentials or files sent to cloud."""
from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response,FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel,Field
from pathlib import Path
import os,re
from .api import require_key,ROOT
from neural_core.sky_languages import normalize
from neural_core.sky_voice_local import voices,synthesize,dub_video

router=APIRouter(prefix='/api/global-media/voice',dependencies=[Depends(require_key)])

class SpeechRequest(BaseModel):
    text:str=Field(min_length=1,max_length=800)
    language:str=Field(default='es',max_length=32)

class DubRequest(SpeechRequest):
    video_asset_id:str=Field(min_length=8,max_length=80)

@router.get('/local-capabilities')
def capabilities():
    try:return {'available':True,'engine':'espeak','languages':voices(),'no_network':True,
                'quality':'synthetic','not_all_sky_locales_supported':True}
    except (RuntimeError,OSError,Exception):
        return {'available':False,'engine':'espeak','languages':[],'no_network':True}

@router.post('/local-wav')
def local_wav(body:SpeechRequest):
    try:audio=synthesize(body.text,body.language)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
    return Response(content=audio,media_type='audio/wav',headers={
        'Content-Disposition':'attachment; filename="SKY_voz_local.wav"',
        'Cache-Control':'private, no-store'})

@router.post('/dub-mp4')
def local_dub(body:DubRequest):
    # Dedicated media worker required for public deployments.
    if os.getenv('SKY_DEPLOYMENT_MODE','local')=='public':
        raise HTTPException(503,'El doblaje requiere un worker aislado en producción')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}',body.video_asset_id):
        raise HTTPException(422,'Identificador inválido')
    try:
        from neural_core import sky_creative
        asset=sky_creative.get_asset(body.video_asset_id)
        if not asset or asset.get('kind')!='video':raise HTTPException(404,'Video no encontrado')
        path,_=sky_creative.asset_path(body.video_asset_id)
        result=dub_video(Path(path),body.text,body.language,ROOT/'local_data'/'sky_dubbing_renders')
    except HTTPException:raise
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(422,str(exc)) from exc
    return FileResponse(result,media_type='video/mp4',filename='SKY_video_narrado.mp4',
             headers={'Cache-Control':'private, no-store'},background=BackgroundTask(result.unlink,missing_ok=True))

@router.get('/transcription/availability')
def transcription_available():
    """A local model must be installed by the owner; no automatic model download."""
    try:import faster_whisper  # noqa:F401
    except ImportError:return {'available':False,'reason':'faster-whisper no está instalado'}
    model=os.getenv('SKY_WHISPER_LOCAL_MODEL','').strip()
    if not model or not Path(model).is_dir():
        return {'available':False,'reason':'Configurá una carpeta de modelo local SKY_WHISPER_LOCAL_MODEL'}
    return {'available':True,'provider':'faster-whisper','automatic_download':False}
