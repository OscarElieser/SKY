"""Inferencia de imágenes dentro de SKY con pesos Diffusers locales preinstalados.

El núcleo de SKY llama al modelo directamente (no Gemini ni ComfyUI).
Nunca descarga checkpoints, ni ejecuta comandos, ni expone paths al usuario.
"""
from __future__ import annotations
import io
import os
from pathlib import Path


class DiffusersUnavailable(RuntimeError):
    pass


def configured() -> bool:
    raw=os.getenv("SKY_DIFFUSERS_IMAGE_MODEL_DIR","").strip()
    if os.getenv("SKY_DIFFUSERS_ENABLED","0")!="1" or not raw:
        return False
    root=Path(raw).expanduser()
    return root.is_dir() and (root/"model_index.json").is_file()


def capabilities() -> dict:
    try:
        from importlib.util import find_spec
        installed=bool(find_spec("diffusers") and find_spec("torch"))
    except (ImportError,ValueError):
        installed=False
    return {"controller":"SKY","mode":"direct_local_diffusion",
            "configured":configured(),"packages_installed":installed,
            "model_validated_live":False,"model_downloads_automatic":False,
            "kind":"image","video_supported":False}


def image(prompt: str, width: int = 512, height: int = 512, steps: int = 22) -> dict:
    if not configured():
        raise DiffusersUnavailable("Configurá SKY_DIFFUSERS_IMAGE_MODEL_DIR con un modelo local válido.")
    if not isinstance(prompt,str) or not 8<=len(prompt.strip())<=2000:
        raise ValueError("Descripción inválida.")
    if type(width) is not int or type(height) is not int or width not in (512,768) or height not in (512,768):
        raise ValueError("Resolución local debe ser 512 o 768 píxeles por dimensión.")
    if type(steps) is not int or not 10<=steps<=35:
        raise ValueError("Pasos de inferencia: 10–35.")
    try:
        import torch
        from diffusers import DiffusionPipeline
        from PIL import Image
    except ImportError as exc:
        raise DiffusersUnavailable("Instalá PyTorch y Diffusers en el entorno de inferencia local.") from exc
    model_dir=str(Path(os.environ["SKY_DIFFUSERS_IMAGE_MODEL_DIR"]).expanduser().resolve())
    device="cuda" if torch.cuda.is_available() else "cpu"
    dtype=torch.float16 if device=="cuda" else torch.float32
    pipe=None
    try:
        # Hugging Face Hub no recibe la petición: ruta local más local_files_only.
        pipe=DiffusionPipeline.from_pretrained(
            model_dir, local_files_only=True, torch_dtype=dtype, use_safetensors=True)
        pipe=pipe.to(device)
        with torch.inference_mode():
            result=pipe(prompt=prompt.strip(),height=height,width=width,
                        num_inference_steps=steps)
        output=getattr(result,"images",[])
        if not output or not isinstance(output[0],Image.Image):
            raise DiffusersUnavailable("El modelo local no generó una imagen.")
        img=output[0]
        if img.size!=(width,height):
            raise DiffusersUnavailable("La imagen obtenida no corresponde a la resolución solicitada.")
        buf=io.BytesIO();img.save(buf,format="PNG")
        from .sky_creative import ingest
        asset=ingest(buf.getvalue(),"SKY_Diffusers_Local.png")
        return {"asset":asset,"provider":"SKY Diffusers local",
                "model_downloads":False,"real_image":True,
                "device":device,"width":width,"height":height}
    except DiffusersUnavailable:
        raise
    except Exception as exc:
        # Nunca incluir excepciones de dependencias que mencionen rutas privadas.
        raise DiffusersUnavailable("El modelo local no pudo terminar la generación; revisá GPU y configuración.") from exc
    finally:
        if pipe is not None:
            del pipe
        if device=="cuda":
            try:torch.cuda.empty_cache()
            except Exception:pass
