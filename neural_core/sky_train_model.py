"""Local supervised fine-tuning for a SKY specialized language model (LoRA).

User-opt-in only; loads weights and dataset ONLY from local paths.
No telemetry, no online model download, no auto-training at startup, no
existing SKY model replacement. Checkpoint must pass evaluation to be
eligible for manual activation.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import platform
import json
import math
import os
import random
import re
from datetime import datetime,timezone
from pathlib import Path

MAX_SAMPLES=150000
MAX_TEXT=9000
MIN_SAMPLES=20
SKY_SYSTEM_PROMPT=('Eres SKY, asistente personal que coordina modelos y herramientas autorizadas. '
                   'Responde en el idioma solicitado y distingue resultados confirmados de acciones pendientes. '
                   'No inventes ejecuciones ni datos. Respeta privacidad, permisos y seguridad.')


def format_prompt(question, history=None):
    """Plantilla única para entrenamiento e inferencia, con el mismo rol SKY."""
    if not isinstance(question,str) or not question.strip():
        raise SkyTrainingError('La consulta del modelo está vacía.')
    lines=[SKY_SYSTEM_PROMPT]
    for turn in history or []:
        if turn.get('role')=='user':lines.append('Usuario: '+turn['content'])
        elif turn.get('role')=='assistant':lines.append('SKY: '+turn['content'])
    lines.extend(('Usuario: '+question,'SKY:'))
    return '\n'.join(lines)

class SkyTrainingError(ValueError):pass

def validate_dataset(path,limit=MAX_SAMPLES):
    p=Path(path).expanduser().resolve(strict=True)
    if not p.is_file() or p.suffix.lower()!=".jsonl":
        raise SkyTrainingError("Datos deben ser un archivo JSONL local.")
    if p.stat().st_size>80_000_000:
        raise SkyTrainingError("El archivo supera el límite de 80 MB.")
    items=[]
    with p.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():continue
            if len(items)>=limit:raise SkyTrainingError("Dataset supera el límite autorizado.")
            try:row=json.loads(line)
            except ValueError as exc:raise SkyTrainingError("Fila JSONL no válida.") from exc
            if not isinstance(row,dict) or row.get("approved_for_training") is not True:
                raise SkyTrainingError("Cada ejemplo necesita approved_for_training=true.")
            prompt=row.get("instruction")
            answer=row.get("response")
            if (not isinstance(prompt,str) or not isinstance(answer,str)
                or not 5<=len(prompt.strip())<=MAX_TEXT
                or not 5<=len(answer.strip())<=MAX_TEXT):
                raise SkyTrainingError("Instrucción o respuesta incompleta.")
            if any(x in (prompt+answer).lower() for x in (
                "-----begin private key-----","authorization: bearer ",
                "sk-proj-","x-sky-key:","password=")):
                raise SkyTrainingError("Se detectó posible credencial: anonimizá antes de entrenar.")
            items.append((prompt.strip(),answer.strip()))
    if len(items)<MIN_SAMPLES:
        raise SkyTrainingError("Se requieren al menos 20 pares revisados y autorizados.")
    return items


def split_dataset(items,seed=42):
    ids=list(range(len(items)));random.Random(seed).shuffle(ids)
    cutoff=max(1,len(items)//10)
    val_ids=set(ids[:cutoff])
    return ([x for i,x in enumerate(items) if i not in val_ids],
            [x for i,x in enumerate(items) if i in val_ids])


def build_training_examples(pairs,tokenizer,max_length):
    import torch
    class Records(torch.utils.data.Dataset):
        def __init__(self):
            self.items=[]
            for question,answer in pairs:
                prefix=format_prompt(question)
                ids_prefix=tokenizer(prefix,add_special_tokens=False)["input_ids"]
                ids_answer=tokenizer(" "+answer+tokenizer.eos_token,add_special_tokens=False)["input_ids"]
                ids=(ids_prefix+ids_answer)[:max_length]
                labels=([-100]*len(ids_prefix)+ids_answer)[:max_length]
                if any(t!=-100 for t in labels):
                    self.items.append((ids,labels))
            if not self.items:raise SkyTrainingError("No quedan ejemplos de respuesta tras truncar.")
        def __len__(self):return len(self.items)
        def __getitem__(self,index):
            ids,labels=self.items[index]
            pad=max_length-len(ids)
            return {"input_ids":torch.tensor(ids+[tokenizer.pad_token_id]*pad),
                    "attention_mask":torch.tensor([1]*len(ids)+[0]*pad),
                    "labels":torch.tensor(labels+[-100]*pad)}
    return Records()


def train(*,dataset,base_model,output,confirm_rights=False,
          epochs=1,steps=100,max_length=512,seed=42):
    if confirm_rights is not True:
        raise SkyTrainingError("Confirmá explícitamente la licencia del modelo y los derechos de todos los datos.")
    if type(epochs) is not int or not 1<=epochs<=10:
        raise SkyTrainingError("epochs debe estar entre 1 y 10.")
    if type(steps) is not int or not 1<=steps<=50000:
        raise SkyTrainingError("steps fuera del límite.")
    if type(max_length) is not int or not 128<=max_length<=4096:
        raise SkyTrainingError("longitud de contexto inválida.")
    base=Path(base_model).expanduser().resolve(strict=True)
    if not base.is_dir() or not (base/"config.json").is_file():
        raise SkyTrainingError("La base debe ser un modelo Transformer ya descargado en carpeta local.")
    destination=Path(output).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise SkyTrainingError("Destino existente: no sobrescribo checkpoints previos.")
    examples=validate_dataset(dataset)
    train_set,val_set=split_dataset(examples,seed)
    dataset_hash=hashlib.sha256(Path(dataset).expanduser().read_bytes()).hexdigest()
    try:
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments
        from peft import LoraConfig,TaskType,get_peft_model
    except ImportError as exc:
        raise SkyTrainingError("Instalá dependencias opcionales PyTorch, Transformers, PEFT y Accelerate.") from exc
    if not torch.cuda.is_available():
        raise SkyTrainingError("SKY requiere una GPU CUDA compatible para este entrenamiento; no se inició el proceso.")
    torch.manual_seed(seed)
    tok=AutoTokenizer.from_pretrained(str(base),local_files_only=True,trust_remote_code=False)
    if not tok.eos_token:
        raise SkyTrainingError("El tokenizer base no define EOS.")
    if tok.pad_token is None:tok.pad_token=tok.eos_token
    model=AutoModelForCausalLM.from_pretrained(
        str(base),local_files_only=True,trust_remote_code=False,
        torch_dtype=torch.float16,use_safetensors=True)
    model.config.use_cache=False
    adapter=get_peft_model(model,LoraConfig(
        task_type=TaskType.CAUSAL_LM,r=8,lora_alpha=16,lora_dropout=0.05,
        bias="none"))
    ds_train=build_training_examples(train_set,tok,max_length)
    ds_val=build_training_examples(val_set,tok,max_length)
    args=TrainingArguments(
        output_dir=str(destination),overwrite_output_dir=False,
        num_train_epochs=epochs,max_steps=steps,learning_rate=0.0001,
        per_device_train_batch_size=1,gradient_accumulation_steps=4,
        per_device_eval_batch_size=1,logging_steps=10,eval_strategy="steps",
        eval_steps=max(1,min(25,steps)),save_strategy="no",
        fp16=True,report_to="none",dataloader_num_workers=0,seed=seed)
    trainer=Trainer(model=adapter,args=args,
                    train_dataset=ds_train,eval_dataset=ds_val,
                    processing_class=tok)
    metrics_before=trainer.evaluate()
    training=trainer.train()
    metrics_after=trainer.evaluate()
    before=float(metrics_before.get("eval_loss",float("nan")))
    after=float(metrics_after.get("eval_loss",float("nan")))
    if not all(math.isfinite(v) for v in (before,after)):
        raise SkyTrainingError("Evaluación inválida; no se habilitará ningún checkpoint.")
    # No sobreescribir modelo SKY actual. Guardar adaptador únicamente.
    adapter_path=destination/"adapter"
    adapter.save_pretrained(adapter_path,safe_serialization=True)
    tok.save_pretrained(destination/"tokenizer")
    manifest={"name":"SKY LoRA experimental","base_model":str(base),
              "format":"peft_lora","training_examples":len(train_set),
              "heldout_examples":len(val_set),"steps":training.global_step,
              "eval_loss_before":before,"eval_loss_after":after,
              "eval_loss_improved":after<before,
              "trained_at_utc":datetime.now(timezone.utc).isoformat(),
              "activated":False,"evaluation_passed":math.isfinite(after),
              "not_foundational_model":True,"dataset_sha256":dataset_hash,
              "model_family":"SKY LoRA specialized","training_seed":seed,
              "base_weights_unchanged":True,"language_policy":"requested_language"}
    (destination/"sky_training_manifest.json").write_text(
        json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    return manifest


def preflight(*, dataset, base_model=None, output=None):
    """Comprobación NO invasiva y sin red: cero entrenamiento o descargas."""
    p=Path(dataset).expanduser()
    report={"controller":"SKY","mode":"lora_preflight_only",
            "os":platform.system(),"dataset_exists":p.is_file(),
            "sample_count":0,"data_approved":False,"base_model_ready":False,
            "output_available":False,"cuda_available":False,"cuda_device":None,
            "dependencies":{},"ready_to_train":False,
            "training_performed":False,"model_trained":False}
    if p.is_file():
        try:
            data=validate_dataset(p)
            report.update(sample_count=len(data),data_approved=True,
                          train_count=len(split_dataset(data)[0]),
                          validation_count=len(split_dataset(data)[1]))
        except (SkyTrainingError,OSError,ValueError) as exc:
            report["dataset_error"]=str(exc)[:180]
    if base_model:
        b=Path(base_model).expanduser()
        report["base_model_ready"]=b.is_dir() and (b/"config.json").is_file()
    if output:
        d=Path(output).expanduser()
        report["output_available"]=(not d.exists() or (d.is_dir() and not any(d.iterdir())))
    for package in ("torch","transformers","peft","accelerate","safetensors"):
        report["dependencies"][package]=importlib.util.find_spec(package) is not None
    if report["dependencies"]["torch"]:
        try:
            import torch
            report["cuda_available"]=bool(torch.cuda.is_available())
            if report["cuda_available"]:
                report["cuda_device"]=torch.cuda.get_device_name(0)
        except (ImportError,RuntimeError,OSError):
            pass
    report["ready_to_train"]=all([
        report["data_approved"],report["base_model_ready"],report["output_available"],
        report["cuda_available"],all(report["dependencies"].values())])
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description="SKY LoRA: entrenamiento local explícito, no autoinstalación")
    parser.add_argument("--dataset",required=True)
    parser.add_argument("--base-model",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--confirm-rights",action="store_true")
    parser.add_argument("--preflight",action="store_true",help="Solo comprobar, sin entrenar ni bajar modelos")
    parser.add_argument("--epochs",type=int,default=1)
    parser.add_argument("--steps",type=int,default=100)
    parser.add_argument("--max-length",type=int,default=512)
    args=parser.parse_args(argv)
    if args.preflight:
        print(json.dumps(preflight(dataset=args.dataset,base_model=args.base_model,
                                   output=args.output),indent=2,ensure_ascii=False))
        return
    result=train(dataset=args.dataset,base_model=args.base_model,
                 output=args.output,confirm_rights=args.confirm_rights,
                 epochs=args.epochs,steps=args.steps,max_length=args.max_length)
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=="__main__":main()
