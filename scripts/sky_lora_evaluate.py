"""Manual evaluation of a genuinely trained SKY LoRA checkpoint.

No implicit training or remote calls. Inputs are a separate blind evaluation
set, not part of the training JSONL. Save outputs only on the owner's disk.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class EvaluationInvalid(ValueError):
    pass


def load_cases(path=None):
    p=Path(path or ROOT/"data/evaluation/sky_holdout_v1.jsonl")
    rows=[]
    seen=set()
    with p.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():continue
            item=json.loads(line)
            if not isinstance(item,dict) or any(
                key not in item for key in ("id","prompt","language","expected_behavior")
            ):
                raise EvaluationInvalid("Caso de evaluación inválido.")
            if item["id"] in seen or not 8<=len(item["prompt"])<=1200:
                raise EvaluationInvalid("Caso duplicado o demasiado largo.")
            seen.add(item["id"])
            rows.append(item)
    if not 15<=len(rows)<=200:
        raise EvaluationInvalid("El banco independiente necesita de 15 a 200 casos.")
    return rows


def evaluate(*, execute=False, destination=None, limit=None):
    """No llama modelo si execute=False; no inventa nota de calidad."""
    cases=load_cases()
    if limit is not None:
        if type(limit) is not int or not 1<=limit<=len(cases):
            raise EvaluationInvalid("Límite de evaluación inválido.")
        cases=cases[:limit]
    report={"controller":"SKY","benchmark":"sky_holdout_v1",
            "available_cases":len(cases),
            "independent_evaluation":True,
            "generation_executed":False,
            "quality_certified":False,
            "human_review_required":True,
            "models_downloaded":False}
    if not execute:
        return report
    if not destination:
        raise EvaluationInvalid("Elegí un archivo local para guardar los resultados.")
    from neural_core.sky_trained_inference import readiness, reply
    if not readiness()["released_to_sky"]:
        raise EvaluationInvalid("No existe un adaptador LoRA real evaluado y activado.")
    output=Path(destination).expanduser().resolve()
    if output.exists():
        raise EvaluationInvalid("No sobrescribo evaluaciones previas.")
    output.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for case in cases:
        answer=reply([{"role":"user","content":case["prompt"]}],max_tokens=380)
        rows.append({"id":case["id"],"domain":case["domain"],
                     "language":case["language"],
                     "prompt":case["prompt"],"answer":answer,
                     "expected_behavior":case["expected_behavior"],
                     "manual_score":None,"verified_receipt":None})
    with output.open("x",encoding="utf-8") as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    report.update(generation_executed=True,answers_saved=len(rows),
                  finished_at_utc=datetime.now(timezone.utc).isoformat(),
                  "evaluation_path":str(output))
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description="Evaluación aislada LoRA SKY")
    parser.add_argument("--execute",action="store_true",help="Generar respuestas reales, solo tras aprobar adaptador")
    parser.add_argument("--output",default=None)
    parser.add_argument("--limit",type=int,default=None)
    args=parser.parse_args(argv)
    print(json.dumps(evaluate(execute=args.execute,destination=args.output,
                              limit=args.limit),indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
