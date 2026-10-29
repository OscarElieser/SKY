"""Authenticated SKY API bridge for the real Video Studio production engine.

All source files are resolved through SKY Creative asset IDs, never arbitrary
paths supplied by clients. No unattended model downloads or cloud requests.
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .api import require_key
from neural_core import sky_creative as creative

router = APIRouter(prefix="/api/video-studio", tags=["SKY Video Studio"],
                   dependencies=[Depends(require_key)])


class Scene(BaseModel):
    asset_id: str = Field(pattern=r"^asset_[a-f0-9]{20}$")
    duration: float = Field(ge=0.5, le=30)


class Caption(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(min_length=1, max_length=200)


class Production(BaseModel):
    scenes: list[Scene] = Field(min_length=1, max_length=12)
    format: str = Field(default="vertical", pattern="^(vertical|horizontal|square)$")
    fps: int = Field(default=30, ge=24, le=60)
    transition: str = Field(default="fade", pattern="^(cut|fade)$")
    transition_duration: float = Field(default=0.4, ge=0.1, le=1.5)
    title: str | None = Field(default=None, max_length=100)
    captions: list[Caption] = Field(default_factory=list, max_length=50)
    narration: str | None = Field(default=None, max_length=4000)
    narration_engine: str = Field(default="espeak", pattern="^espeak$")
    music_asset_id: str | None = Field(default=None, pattern=r"^asset_[a-f0-9]{20}$")
    music_volume: float = Field(default=0.18, ge=0, le=1)


@router.get("/capabilities")
def capabilities():
    import shutil
    return {
        "video_render": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
        "offline_narration": bool(shutil.which("espeak-ng")),
        "neural_voice": False,
        "ai_scene_generation": False,
        "formats": ["vertical", "horizontal", "square"],
        "requires_owner_auth": True,
    }


@router.post("/produce", status_code=201)
def produce_video(body: Production):
    from scripts.sky_video_production import produce
    total = sum(scene.duration for scene in body.scenes)
    if total > 90:
        raise HTTPException(422, "Máximo 90 segundos por trabajo en esta API")
    project = body.model_dump(exclude_none=True)
    scenes = []
    for scene in body.scenes:
        try:
            path, asset = creative.asset_path(scene.asset_id)
        except (KeyError, FileNotFoundError):
            raise HTTPException(404, f"Escena no disponible: {scene.asset_id}")
        if asset["kind"] not in {"image", "video"}:
            raise HTTPException(422, "Las escenas deben ser imágenes o videos")
        scenes.append({"file": str(path), "duration": scene.duration})
    project["scenes"] = scenes
    if body.music_asset_id:
        try:
            path, asset = creative.asset_path(body.music_asset_id)
        except (KeyError, FileNotFoundError):
            raise HTTPException(404, "Música no disponible")
        if asset["kind"] != "audio":
            raise HTTPException(422, "El fondo musical debe ser un archivo de audio")
        project["audio"] = str(path)
    project.pop("music_asset_id", None)
    with tempfile.TemporaryDirectory(prefix="sky-api-video-") as folder:
        folder = Path(folder)
        project_path = folder / "project.json"
        project_path.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
        output = produce(project_path, folder / "produced.mp4")
        if output.stat().st_size > creative.MAX_IMPORT:
            raise HTTPException(413, "El video supera el tamaño admitido por SKY Creative")
        return creative.ingest(output.read_bytes(), "sky_video_studio.mp4")
