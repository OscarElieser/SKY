"""Private, bounded subtitle conversion + optional user-approved cloud narration."""
from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response,FileResponse
from starlette.background import BackgroundTask
import os
from pydantic import BaseModel,Field
from .api import require_key,ROOT
from neural_core.sky_languages import normalize
from neural_core.sky_subtitles import to_vtt,burn_subtitles

router=APIRouter(prefix='/api/global-media',dependencies=[Depends(require_key)])

class Captions(BaseModel):
    srt:str=Field(min_length=10,max_length=32000)
    language:str='es'

class Burn(Captions):
    video_asset_id:str=Field(min_length=8,max_length=80)

class Narrate(BaseModel):
    text:str=Field(min_length=1,max_length=2500)
    language:str='es'
    provider:str='none'
    external_consent:bool=False

@router.post('/subtitles/vtt')
def srt_to_vtt(body:Captions):
    try:content=to_vtt(body.srt,body.language)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    return Response(content=content,media_type='text/vtt; charset=utf-8',headers={
        'Content-Disposition':'attachment; filename="SKY_subtitulos.vtt"','Cache-Control':'no-store'})

@router.post('/subtitles/render')
def subtitles_to_mp4(body:Burn):
    if os.getenv('SKY_DEPLOYMENT_MODE','local')=='public':
        raise HTTPException(503,'Render de subtítulos requiere un worker de medios aislado en producción')
    import re
    if not re.fullmatch('[a-zA-Z0-9_-]{8,80}',body.video_asset_id):raise HTTPException(422,'Identificador de recurso inválido')
    try:
        normalize(body.language,strict=True)
        from neural_core import sky_creative
        asset=sky_creative.get_asset(body.video_asset_id)
        if not asset or asset.get('kind')!='video':raise HTTPException(404,'Video no encontrado')
        video,_=sky_creative.asset_path(body.video_asset_id)
        folder=ROOT/'local_data'/'sky_subtitle_renders'
        target=burn_subtitles(Path(video),body.srt,folder)
    except HTTPException:raise
    except (ValueError,RuntimeError,OSError) as exc:
        raise HTTPException(422,str(exc)) from exc
    return FileResponse(target,media_type='video/mp4',filename='SKY_video_subtitulado.mp4',
                        headers={'Cache-Control':'private, no-store'},background=BackgroundTask(target.unlink,missing_ok=True))

@router.post('/narration/mp3')
def narration(body:Narrate):
    # gTTS uses an external service. No automatic transmission or voice cloning.
    if body.provider!='gtts' or not body.external_consent:
        raise HTTPException(409,'Para narración en nube, autorizá expresamente el envío del texto y elegí gtts')
    try:
        locale=normalize(body.language,strict=True)
        from gtts import gTTS
        from gtts.lang import tts_langs
        root=locale.split('-')[0]
        if root not in tts_langs():raise HTTPException(422,'Idioma no compatible con este proveedor de voz')
        import io
        file=io.BytesIO()
        gTTS(text=body.text,lang=root,slow=False).write_to_fp(file)
        data=file.getvalue()
        if len(data)>3_000_000 or not data:raise RuntimeError('Narración inválida')
        return Response(content=data,media_type='audio/mpeg',headers={
            'Content-Disposition':'attachment; filename="SKY_narracion.mp3"','Cache-Control':'no-store'})
    except HTTPException:raise
    except Exception as exc:raise HTTPException(503,'No se pudo conectar con el servicio de voz autorizado') from exc
