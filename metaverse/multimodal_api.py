"""Authenticated on-demand multimodal reading. Never memorizes uploads by default."""
from __future__ import annotations
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_multimodal_reader as reader

router = APIRouter(prefix="/api/sky/reader", dependencies=[Depends(require_key)])


@router.get("/capabilities")
def capabilities():
    return {
        "local_text_extraction": sorted(reader.TEXT_EXTS | reader.DOC_EXTS),
        "image_metadata": sorted(reader.IMAGE_EXTS),
        "media_metadata": sorted(reader.VIDEO_EXTS | reader.AUDIO_EXTS),
        "local_image_understanding": "requires SKY_VISION_MODEL + Ollama multimodal model",
        "full_video_understanding": False,
        "video_transcription": False,
        "automatic_memory_ingest": False,
        "no_third_party_calls_without_opt_in": True,
        "max_upload_mb": 80,
    }


async def _bounded_read(file: UploadFile) -> bytes:
    # Strict transport bound: rejects oversized bodies even with no Content-Length.
    max_len = reader.MAX_BYTES
    blocks=[]
    total=0
    while True:
        part=await file.read(min(1024*1024, max_len-total+1))
        if not part: break
        total+=len(part)
        if total>max_len:raise HTTPException(413, "Archivo demasiado grande.")
        blocks.append(part)
    return b"".join(blocks)


@router.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    try:
        return reader.analyze(file.filename or "", await _bounded_read(file))
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:200]) from exc
    finally:
        await file.close()


@router.post("/vision")
async def analyze_image(file: UploadFile = File(...),
                        question: str = Form("Describe la imagen y distingue lo visible de lo incierto.")):
    try:
        data=await _bounded_read(file)
        return reader.analyze_image_local(file.filename or "",data,question)
    except ValueError as exc:
        raise HTTPException(422,str(exc)[:200]) from exc
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)[:200]) from exc
    finally:
        await file.close()
