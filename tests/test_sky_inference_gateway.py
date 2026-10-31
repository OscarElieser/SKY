"""SKY inference protocol tests: real loopback HTTP, no external API or GPU."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from neural_core import sky_inference_gateway as gateway


class MockOllama(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/tags":
            self.send_error(404)
            return
        self._send({"models": [{"name": "llama3.2:latest"}]})

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size))
        self.server.requests.append(body)
        self._send({"done": True,
                    "message": {"role": "assistant", "content": "Respuesta SKY local comprobada"},
                    "prompt_eval_count": 37, "eval_count": 13})

    def _send(self, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def model_worker(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockOllama)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SKY_INFERENCE_WORKERS",
                       "http://127.0.0.1:" + str(server.server_port))
    monkeypatch.setenv("SKY_INFERENCE_MODEL", "llama3.2")
    with gateway._LOCK:
        gateway._FAILURES.clear()
        gateway._WORKER_CURSOR = 0
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_real_local_http_inference_protocol_without_cloud(model_worker):
    health = gateway.readiness()
    assert health["local_ollama_ready"] is True
    assert health["ready_workers"] == 1
    assert health["model_output_verified"] is False
    messages = [{"role": "system", "content": "Eres SKY IA"},
                {"role": "user", "content": "Redacta un objetivo académico"}]
    outcome = gateway.generate(messages, max_output_tokens=100)
    assert outcome["respuesta"] == "Respuesta SKY local comprobada"
    assert outcome["proveedor"] == "ollama"
    assert outcome["nube"] is False
    assert outcome["acciones_ejecutadas"] is False
    assert len(outcome["operacion"]) == 32
    assert outcome["metricas"]["tokens_entrada"] == 37
    assert outcome["metricas"]["tokens_salida"] == 13
    assert len(model_worker.requests) == 1
    assert model_worker.requests[0]["stream"] is False
    assert model_worker.requests[0]["options"]["num_predict"] == 100
    assert model_worker.requests[0]["messages"][-1]["content"] == messages[-1]["content"]
    assert not any("gemini" in str(item).lower() or "groq" in str(item).lower()
                   for item in model_worker.requests)


@pytest.mark.parametrize("url", [
    "http://0.0.0.0:11434", "http://192.168.1.60:11434",
    "http://example.com:11434", "https://127.0.0.1:11434",
    "http://user:secret@127.0.0.1:11434", "http://127.0.0.1:11434/private",
    "http://127.0.0.1:11434?x=1"
])
def test_worker_configuration_rejects_public_or_untrusted_endpoints(monkeypatch, url):
    monkeypatch.setenv("SKY_INFERENCE_WORKERS", url)
    with pytest.raises(gateway.InferenceUnavailable):
        gateway._workers()


def test_no_fabrication_without_model_and_no_cloud_fallback(monkeypatch):
    monkeypatch.setenv("SKY_INFERENCE_WORKERS", "http://127.0.0.1:11434")
    monkeypatch.setenv("SKY_INFERENCE_MODEL", "invalid model\n")
    with pytest.raises(gateway.InferenceUnavailable):
        gateway._model()


def test_capacity_bound_refuses_extra_requests(model_worker):
    assert gateway._GATE.acquire(blocking=False)
    assert gateway._GATE.acquire(blocking=False)
    try:
        with pytest.raises(gateway.InferenceBusy):
            gateway.generate([{"role": "user", "content": "Prueba"}])
    finally:
        gateway._GATE.release()
        gateway._GATE.release()
    assert len(model_worker.requests) == 0


def test_metrics_never_publish_prompt_text(model_worker):
    gateway.generate([{"role": "user", "content": "DATO PRIVADO DE PRUEBA"}])
    metrics = gateway.metrics_snapshot()
    assert metrics["requests"]["ok"] >= 1
    assert metrics["tokens"]["output"] >= 13
    assert "DATO PRIVADO" not in json.dumps(metrics)
    assert "latencia_p95_ms" in metrics


def test_invalid_turn_is_rejected_before_network(model_worker):
    with pytest.raises(ValueError):
        gateway.generate([{"role": "tool", "content": "ejecutar"}])
    assert len(model_worker.requests) == 0



def test_academic_24k_prompt_and_4096_output_tokens_are_sent_intact(model_worker, monkeypatch):
    monkeypatch.setenv("SKY_INFERENCE_NUM_CTX", "32768")
    prompt = "Investigación educativa: " + "x" * 23975
    assert 16_000 < len(prompt) <= 32_000
    result = gateway.generate([{"role": "system", "content": "Eres SKY"},
                               {"role": "user", "content": prompt}],
                              max_output_tokens=4096)
    payload = model_worker.requests[-1]
    assert payload["messages"][-1]["content"] == prompt
    assert payload["options"] == {"num_predict": 4096, "num_ctx": 32768}
    assert result["metricas"]["contexto_tokens"] == 32768
    assert result["respuesta_incompleta"] is False
    assert result["nube"] is False


def test_large_context_requires_operator_budget_before_http(model_worker, monkeypatch):
    monkeypatch.setenv("SKY_INFERENCE_NUM_CTX", "16384")
    with pytest.raises(ValueError, match="32768"):
        gateway.generate([{"role": "user", "content": "Q" * 20_000}],
                         max_output_tokens=4096)
    assert not model_worker.requests


def test_reject_over_32k_input_and_excess_generation_budget(model_worker, monkeypatch):
    monkeypatch.setenv("SKY_INFERENCE_NUM_CTX", "32768")
    with pytest.raises(ValueError):
        gateway.generate([{"role": "user", "content": "A" * 32001}])
    with pytest.raises(ValueError):
        gateway.generate([{"role": "user", "content": "consulta"}],
                         max_output_tokens=4097)
    assert not model_worker.requests


def test_multibyte_prompt_rejected_when_context_cannot_fit(model_worker, monkeypatch):
    monkeypatch.setenv("SKY_INFERENCE_NUM_CTX", "32768")
    with pytest.raises(ValueError, match="contexto"):
        gateway.generate([{"role": "user", "content": "界" * 32_000}],
                         max_output_tokens=4096)
    assert not model_worker.requests


def test_invalid_context_configuration_is_not_silently_ignored(model_worker, monkeypatch):
    monkeypatch.setenv("SKY_INFERENCE_NUM_CTX", "unbounded")
    with pytest.raises(gateway.InferenceUnavailable):
        gateway.generate([{"role": "user", "content": "consulta"}])
    assert not model_worker.requests
