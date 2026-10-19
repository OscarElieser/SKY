"""Authenticated SKY local STT. No outbound transcript transfer."""
from __future__ import annotations
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from .api import require_key
from neural_core.sky_stt_local import capabilities, transcribe, MAX_INPUT_BYTES

router = APIRouter(prefix='/api/global-media/stt', dependencies=[Depends(require_key)])

@router.get('/capabilities')
def status():
    return capabilities()

@router.post('/transcribe')
async def local_transcribe(file: UploadFile = File(...), language: str = Form(default='')):
    # Streaming capped read avoids loading unbounded request bodies.
    body = await file.read(MAX_INPUT_BYTES + 1)
    if len(body) > MAX_INPUT_BYTES:
        raise HTTPException(413, 'Audio supera el límite autorizado')
    try:
        return transcribe(body, filename=file.filename or 'audio.wav', language=language or None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
