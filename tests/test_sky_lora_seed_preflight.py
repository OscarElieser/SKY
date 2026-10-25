"""Tests of LoRA preflight, original SKY seed and truly independent holdout.

No models are downloaded, no GPU work occurs, and no private data is read.
"""
from __future__ import annotations
import json
from pathlib import Path
from neural_core import sky_train_model as model

ROOT=Path(__file__).resolve().parents[1]
SEED=ROOT/"data"/"training"/"sky_seed_v1.jsonl"
HOLDOUT=ROOT/"data"/"evaluation"/"sky_holdout_v1.jsonl"


def test_original_sky_corpus_is_approved_and_not_personal():
    examples=model.validate_dataset(SEED)
    assert len(examples)>=80
    questions=[q for q,_ in examples]
    assert len(questions)==len(set(questions))
    assert all(len(a)>=10 for _,a in examples)
    train,validation=model.split_dataset(examples)
    assert len(train)>len(validation)>=5
    assert set(train).isdisjoint(set(validation))


def test_blind_benchmark_is_distinct_from_training():
    train={question.strip().casefold() for question,_ in model.validate_dataset(SEED)}
    rows=[json.loads(x) for x in HOLDOUT.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)>=20
    assert len({x["id"] for x in rows})==len(rows)
    assert len({x["prompt"] for x in rows})==len(rows)
    assert not any(r["prompt"].strip().casefold() in train for r in rows)
    assert set(x["language"] for x in rows if x["domain"]=="multilingual")>=set(
        ("es","en","fr","pt","it","ko","zh","ja","de"))-{"es"}
    assert all(r["independent_holdout"] is True for r in rows)


def test_training_inference_share_same_multilingual_template():
    prompt=model.format_prompt("Explain in English why SKY verifies outcomes.")
    assert "Responde en el idioma solicitado" in prompt
    assert "Usuario: Explain in English" in prompt
    assert prompt.endswith("\nSKY:")
    continued=model.format_prompt("¿Qué sigue?",history=[
        {"role":"user","content":"Hola SKY"},
        {"role":"assistant","content":"Hola, ¿qué necesitás?"}
    ])
    assert "Usuario: Hola SKY" in continued
    assert "SKY: Hola, ¿qué necesitás?" in continued
    assert continued.endswith("Usuario: ¿Qué sigue?\nSKY:")


def test_preflight_never_trains_or_claims_gpu(tmp_path):
    report=model.preflight(dataset=SEED,base_model=tmp_path/"missing-model",
                           output=tmp_path/"new-training")
    assert report["mode"]=="lora_preflight_only"
    assert report["sample_count"]>=80 and report["data_approved"]
    assert report["base_model_ready"] is False
    assert report["ready_to_train"] is False
    assert report["training_performed"] is False and report["model_trained"] is False
    assert "torch" in report["dependencies"]


def test_seed_has_no_reused_or_external_secret_sources():
    rows=[json.loads(x) for x in SEED.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert {r["source"] for r in rows}=={"sky_authored_seed_v1"}
    assert all(r["approved_for_training"] is True for r in rows)
    assert not any("@" in r["instruction"] for r in rows)
