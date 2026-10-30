"""Regresiones del puente multiagente reflexivo: privacidad, calidad y fallback."""
from __future__ import annotations

import json

import pytest

from neural_core import sky_multiagent_quality as quality
from neural_core import sky_unified_agents as agents
from neural_core import sky_reflective_core as memory

TASK = ("Investiga y analiza las opciones de arquitectura, "
        "compara alternativas para un sistema educativo.")
PLAN = {"agents": [
    {"name": "Arquitectura", "objective": "Analizar opciones técnicas y restricciones del sistema."},
    {"name": "Docencia", "objective": "Evaluar la pertinencia pedagógica de las alternativas."},
]}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_REFLECTIVE_DB", str(tmp_path / "reflexive.sqlite3"))
    monkeypatch.setenv("SKY_REFLECTIVE_SEMANTIC", "0")
    monkeypatch.setenv("SKY_UNIFIED_AGENTS_ENABLED", "1")
    monkeypatch.setenv("SKY_METRICAS", "0")
    monkeypatch.setattr(agents, "_personal_context", lambda: "")
    monkeypatch.setattr(agents, "_backend", lambda preferred="auto": ("ollama", "local-test"))


def _fake_model(monkeypatch, responses):
    replies = iter(responses)
    calls = []
    def ask(provider, model, system, prompt, limit):
        calls.append((system, prompt))
        return next(replies)
    monkeypatch.setattr(agents, "_ask", ask)
    return calls


def test_reflective_learning_only_uses_categorical_provenance():
    private = "TOKEN_PRIVADO_12345"
    record = memory.record("código Python " + private, {
        "aprobada": False, "estatica": ["Error de sintaxis " + private]})
    assert record["topic"] == "programacion"
    assert private.encode() not in memory._path().read_bytes()
    items = quality.advice("Programar un sistema en Python")
    assert len(items) == 1
    assert items[0]["category"] == "syntax"
    assert items[0]["source"] == "skill_builder_test_failure"
    assert private not in json.dumps(items)


def test_general_request_does_not_read_irrelevant_knowledge():
    memory.record("calcula porcentaje", {"aprobada": False,
                  "estatica": ["Error de sintaxis"]})
    assert quality.advice("quiero algo interesante") == []


@pytest.mark.parametrize("answer", [
    "He instalado la aplicación y todo funciona.",
    "Ya envié un correo a tus contactos.",
    "Acabo de modificar el archivo del sistema.",
    "Investigué la web y comprobé que existe.",
])
def test_claims_of_unperformed_actions_rejected(answer):
    response = quality.assess(answer)
    assert not response["accepted"]
    assert response["reason"] == "unverified_execution_claim"
    assert response["verified_facts"] is False


def test_advisory_does_not_block_normal_responses_or_negations():
    assert quality.assess("No he enviado mensajes; te explico cómo preparar uno.")["accepted"]
    assert quality.assess("Te recomiendo una arquitectura modular.")["accepted"]
    assert not quality.assess("")["accepted"]


def test_multiagent_retries_one_synthesis_and_returns_marked_quality(monkeypatch):
    calls = _fake_model(monkeypatch, [
        json.dumps(PLAN), "Alternativa modular por dominios.",
        "Las clases requieren criterios observables.",
        "Ya he instalado todo en tu computadora.",
        "Conviene evaluar el diseño antes de instalar; no ejecuté acciones.",
    ])
    result = agents.maybe_answer(TASK)
    assert result["mensaje"].startswith("Conviene evaluar")
    assert result["quality_review"]["synthesis_repair_attempts"] == 1
    assert result["quality_review"]["verified_facts"] is False
    assert result["ejecucion_externa"] is False
    assert len(calls) == 5


def test_multiagent_never_presents_fake_execution_when_both_syntheses_fail(monkeypatch):
    calls = _fake_model(monkeypatch, [
        json.dumps(PLAN), "Arquitectura modular.", "Objetivos pedagógicos.",
        "He borrado los archivos.", "He enviado los mensajes.",
    ])
    assert agents.maybe_answer(TASK) is None
    assert len(calls) == 5


def test_prior_verified_test_failures_inform_subagents_without_raw_content(monkeypatch):
    secret = "CLAVE_SECRETA_6622"
    memory.record("Investigar una tesis " + secret, {"aprobada": False,
                  "estatica": ["Error de sintaxis " + secret]})
    calls = _fake_model(monkeypatch, [
        json.dumps(PLAN), "Arquitectura modular.", "Evidencia pedagógica.",
        "Propuesta para evaluar la arquitectura.",
    ])
    result = agents.maybe_answer(TASK)
    assert result["quality_review"]["prior_test_checks_used"] >= 1
    assert "quality_checks_from_prior_builder_tests" in calls[0][1]
    assert all(secret not in json.dumps(row) for row in calls)
    assert len(calls) == 4


def test_unsupported_requests_do_not_consult_specialists(monkeypatch):
    calls = _fake_model(monkeypatch, [])
    assert agents.maybe_answer("Abre Word, analiza y compara documentos.") is None
    assert calls == []


def test_quality_contract_does_not_grant_permissions():
    status = quality.capabilities()
    assert status["device_actions_allowed"] is False
    assert status["repair_attempts_max"] == 1
    assert status["model_training"] is False
    assert status["fact_checker"] is False
    unified = agents.capability_status()
    assert unified["auto_actions"] is False
    assert unified["quality_gate"]["external_research"] is False
