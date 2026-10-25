"""Explicitly approved offline inference of a SKY LoRA adapter, if trained.

Never loads a model from network and never changes SKY's default provider.
A valid training manifest alone does not prove quality: require separate
owner opt-in and improvement on held-out evaluation.
"""
from __future__ import annotations
import json
import os
from functools import lru_cache
from pathlib import Path

class SkyTrainedUnavailable(RuntimeError):pass

def _release():
    raw=os.getenv("SKY_TRAINED_RELEASE_DIR","").strip()
    if not raw:return None
    folder=Path(raw).expanduser().resolve()
    if not folder.is_dir() or not (folder/"sky_training_manifest.json").is_file():
        return None
    try:
        manifest=json.loads((folder/"sky_training_manifest.json").read_text(encoding="utf-8"))
    except (OSError,ValueError):
        return None
    if not isinstance(manifest,dict) or manifest.get("format")!="peft_lora":
        return None
    base=Path(str(manifest.get("base_model",""))).expanduser()
    if not (folder/"adapter"/"adapter_config.json").is_file() or not (base/"config.json").is_file():
        return None
    return folder,base,manifest


def readiness():
    release=_release()
    return {"configured":release is not None,
            "owner_approved":os.getenv("SKY_TRAINED_ENABLED","0")=="1",
            "released_to_sky":bool(release and os.getenv("SKY_TRAINED_ENABLED","0")=="1"
                and release[2].get("evaluation_passed") is True
                and release[2].get("eval_loss_improved") is True),
            "models_downloaded_automatically":False,
            "benchmarked_on_windows":False,
            "type":"Sky local PEFT LoRA specialized base, not foundational"}


@lru_cache(maxsize=1)
def _load(modeldir):
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from peft import PeftModel
    import torch
    if not torch.cuda.is_available():
        raise SkyTrainedUnavailable("Se requiere CUDA compatible para cargar el adaptador SKY en este modo.")
    folder=Path(modeldir)
    manifest=json.loads((folder/"sky_training_manifest.json").read_text(encoding="utf-8"))
    base=str(Path(manifest["base_model"]).expanduser().resolve())
    tokenizer=AutoTokenizer.from_pretrained(str(folder/"tokenizer"),
                                            local_files_only=True,trust_remote_code=False)
    if tokenizer.pad_token is None:tokenizer.pad_token=tokenizer.eos_token
    model=AutoModelForCausalLM.from_pretrained(
        base,local_files_only=True,trust_remote_code=False,
        torch_dtype=torch.float16,use_safetensors=True)
    model=PeftModel.from_pretrained(model,str(folder/"adapter"),
                                  is_trainable=False,local_files_only=True).to("cuda")
    model.eval()
    return tokenizer,model


def reply(messages, model=None, max_tokens=500):
    release=_release()
    info=readiness()
    if not release or not info["released_to_sky"]:
        raise SkyTrainedUnavailable("El adaptador SKY no ha sido evaluado ni aprobado para inferencia.")
    if type(max_tokens) is not int or not 1<=max_tokens<=4096:
        raise ValueError("Límite de tokens no admitido.")
    if not isinstance(messages,list) or not messages:
        raise ValueError("Se necesita conversación de SKY.")
    turns=[]
    for m in messages[-9:]:
        if not isinstance(m,dict) or m.get("role") not in ("system","user","assistant"):
            raise ValueError("Rol de conversación inválido.")
        content=m.get("content")
        if not isinstance(content,str) or len(content)>6000:
            raise ValueError("Contenido de conversación inválido.")
        turns.append(m)
    if turns[-1]["role"]!="user":
        raise ValueError("Falta pregunta del usuario.")
    import torch
    tok,engine=_load(str(release[0]))
    text="\n".join(("Sistema: " if x["role"]=="system" else
                   "Usuario: " if x["role"]=="user" else "SKY: ")+x["content"]
                   for x in turns)+"\nSKY:"
    try:
        inputs=tok(text,return_tensors="pt",truncation=True,max_length=2048).to("cuda")
        with torch.inference_mode():
            tokens=engine.generate(**inputs,max_new_tokens=max_tokens,
                                   do_sample=True,temperature=0.65,top_p=0.9,
                                   pad_token_id=tok.eos_token_id)
        answer=tok.decode(tokens[0][inputs["input_ids"].shape[1]:],
                          skip_special_tokens=True).strip()
        if not answer:
            raise SkyTrainedUnavailable("El adaptador SKY generó una respuesta vacía.")
        return answer
    except SkyTrainedUnavailable:
        raise
    except Exception as exc:
        raise SkyTrainedUnavailable("Inferencia local falló. Verificá VRAM y runtime del modelo.") from exc
