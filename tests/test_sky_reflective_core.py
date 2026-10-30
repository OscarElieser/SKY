"""Pruebas offline y fail-closed del aprendizaje reflexivo."""
from __future__ import annotations

import json
import sqlite3
import pytest
from neural_core import sky_reflective_core as reflection


@pytest.fixture(autouse=True)
def local_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_REFLECTIVE_DB", str(tmp_path / "reflections.sqlite3"))


def test_storage_never_persists_prompts_code_or_private_error():
    secret = "TOKEN_SUPER_PRIVADO_112233"
    report = {"aprobada": False, "estatica": [],
              "pruebas": [{"entrada": secret, "ok": False, "error": secret}]}
    saved = reflection.record("Traduce " + secret, report)
    assert saved["issue"] == "test_mismatch"
    data = reflection._path().read_bytes()
    assert secret.encode() not in data
    with sqlite3.connect(reflection._path()) as db:
        row = db.execute("SELECT topic,issue,outcome,vector_json FROM reflective_experiences").fetchone()
    assert row[:3] == ("texto", "test_mismatch", "failed_tests")
    assert len(json.loads(row[3])) == 32


def test_recall_is_advisory_and_semantically_honest():
    reflection.record("calcula porcentajes", {"aprobada": False,
                       "estatica": ["Error de sintaxis: token privado"]})
    items = reflection.recall("calcula otro porcentaje")
    assert items and items[0]["issue"] == "syntax"
    assert "token privado" not in str(items)
    assert reflection.capabilities()["semantic_llm_embeddings"]["enabled"] is False
    assert reflection.capabilities()["automatic_install"] is False


def test_success_is_observation_not_model_retraining():
    result = reflection.record("Resume un texto", {"aprobada": True, "pruebas": [{"ok": True}]})
    assert result["outcome"] == "passed_tests"
    assert result["model_weights_updated"] is False
    assert reflection.recall("Resume un texto") == []


def test_issue_classification_cannot_echo_arbitrary_runtime_errors():
    secret = "https://secret.invalid/?token=hidden"
    assert reflection.safe_feedback({"aprobada": False, "error": secret}) == reflection._LESSONS["sandbox_failure"]
    assert secret not in reflection.safe_feedback({"aprobada": False, "error": secret})
    assert reflection.issue_for({"aprobada": False, "error": "Superó el tiempo máximo"}) == "timeout"
    assert reflection.issue_for({"aprobada": False, "estatica": ["Importa os no permitido"]}) == "prohibited_code"
    with pytest.raises(ValueError):
        reflection.recall("texto", limit=100000)


def test_skill_builder_bounded_retries_and_no_private_error_in_prompt(monkeypatch):
    from neural_core import sky_skill_builder as builder
    prompts = []
    codes = []
    secret = "password_NUNCA_DEBE_ENVIARSE"
    def fake_redactar(prompt, provider):
        prompts.append(prompt)
        return {"manifiesto": {}, "codigo": "candidate_" + str(len(prompts))}
    def fake_guardar(manifiesto, codigo, pedido):
        codes.append(codigo)
        return {"reporte": {"aprobada": False, "error": secret}}
    monkeypatch.setattr(builder, "_redactar", fake_redactar)
    monkeypatch.setattr(builder, "guardar_propuesta", fake_guardar)
    monkeypatch.setattr(builder, "_estado", lambda: {"necesidades": {}})
    monkeypatch.setattr(builder, "_guardar", lambda data: None)
    result = builder.proponer("calcula porcentajes", intentos=1000)
    assert result["reporte"]["aprobada"] is False
    assert len(codes) == 3
    assert all(secret not in prompt for prompt in prompts)
    assert "falló" in prompts[1]
    assert reflection.recall("calcula porcentajes")


def test_repeated_candidate_stops_without_installation(monkeypatch):
    from neural_core import sky_skill_builder as builder
    prompts = []
    monkeypatch.setattr(builder, "_redactar", lambda prompt, provider: prompts.append(prompt) or
                        {"manifiesto": {}, "codigo": "same"})
    calls = []
    monkeypatch.setattr(builder, "guardar_propuesta",
                        lambda *args: calls.append(args) or {"reporte": {"aprobada": False, "estatica": []}})
    monkeypatch.setattr(builder, "_estado", lambda: {"necesidades": {}})
    monkeypatch.setattr(builder, "_guardar", lambda data: None)
    builder.proponer("redacta resumen", intentos=3)
    assert len(calls) == 1
    assert len(prompts) == 2


def test_optional_semantic_topic_retrieval_is_owner_opt_in(monkeypatch):
    from neural_core import sky_reflective_embeddings as sem
    assert sem.related_topics("texto") is None
    monkeypatch.setenv("SKY_REFLECTIVE_SEMANTIC", "1")
    monkeypatch.setattr(sem, "_vectors", lambda endpoint, model: {
        name: ([1.0, 0.0] if name == "texto" else [0.0, 1.0])
        for name in sem.TOPIC_DESCRIPTIONS
    })
    similarities = sem.related_topics("texto")
    assert similarities["texto"] == 1.0
    assert similarities["calculo"] == 0.0
    assert sem.capabilities()["raw_user_text_sent"] is False


def test_semantic_failure_returns_to_deterministic_retrieval(monkeypatch):
    from neural_core import sky_reflective_embeddings as sem
    reflection.record("calcula porcentaje", {"aprobada": False,
                      "estatica": ["Error de sintaxis"]})
    monkeypatch.setenv("SKY_REFLECTIVE_SEMANTIC", "1")
    monkeypatch.setattr(sem, "_vectors", lambda endpoint, model: (_ for _ in ()).throw(OSError("down")))
    items = reflection.recall("calcula promedio")
    assert items and items[0]["issue"] == "syntax"


def test_ollama_endpoint_fails_closed(monkeypatch):
    from neural_core import sky_reflective_embeddings as sem
    monkeypatch.setenv("SKY_REFLECTIVE_OLLAMA_URL", "https://api.example.org")
    with pytest.raises(ValueError):
        sem._endpoint()
    monkeypatch.setenv("SKY_REFLECTIVE_OLLAMA_URL", "http://127.0.0.1:11434/other")
    with pytest.raises(ValueError):
        sem._endpoint()
    monkeypatch.setenv("SKY_REFLECTIVE_OLLAMA_URL", "http://127.0.0.1:11434")
    assert sem._endpoint() == "http://127.0.0.1:11434"


def test_only_fixed_descriptions_are_submitted_for_embeddings(monkeypatch):
    from neural_core import sky_reflective_embeddings as sem
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, count):
            raw = {"embeddings": [[float(i == j) for j in range(8)]
                                  for i in range(len(sem.TOPIC_DESCRIPTIONS))]}
            return json.dumps(raw).encode()
    requests = []
    class Opener:
        def open(self, request, timeout):
            requests.append(json.loads(request.data.decode()))
            assert timeout <= 2.5
            assert request.full_url == "http://127.0.0.1:11434/api/embed"
            return Response()
    monkeypatch.setattr(sem.urllib.request, "build_opener", lambda *handlers: Opener())
    sem._vectors.cache_clear()
    sem._vectors("http://127.0.0.1:11434", "nomic-embed-text")
    assert requests[0]["input"] == list(sem.TOPIC_DESCRIPTIONS.values())
    assert "secret" not in json.dumps(requests).lower()
    sem._vectors.cache_clear()


def test_reflection_quality_report_counts_only_tests():
    reflection.record("calcula suma", {"aprobada": True})
    reflection.record("calcula porcentajes", {"aprobada": False, "estatica": ["Error de sintaxis"]})
    data = reflection.report()
    assert data["total_observations"] == 2
    assert data["by_topic"]["calculo"]["pass_rate"] == 0.5
    assert data["by_topic"]["calculo"]["failure_categories"]["syntax"] == 1
    assert data["records_are_tests_not_hardware_actions"]
