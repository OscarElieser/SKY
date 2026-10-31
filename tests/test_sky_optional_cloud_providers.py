"""No-network tests for optional cloud connectors in SKY's private SERVER API."""
import io
import json
from unittest.mock import patch
from urllib import error

import pytest
from neural_core import sky_optional_cloud_providers as cloud


class FakeResponse:
    def __init__(self, body):
        self.stream = io.BytesIO(json.dumps(body).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, amount):
        return self.stream.read(amount)


class FakeOpener:
    def __init__(self, body=None, exception=None):
        self.calls = []
        self.body = body or {
            "choices": [{"message": {"content": "Respuesta controlada de SKY"}}]}
        self.exception = exception

    def open(self, req, timeout):
        self.calls.append((req, timeout))
        if self.exception:
            raise self.exception
        return FakeResponse(self.body)


@pytest.fixture
def api_keys(monkeypatch):
    for name in ("OPENROUTER_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY",
                 "CLOUDFLARE_API_TOKEN"):
        monkeypatch.setenv(name, "test_server_side_only_key_not_for_distribution")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a" * 32)
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/free")
    monkeypatch.setenv("CLOUDFLARE_AI_MODEL", "@cf/meta/llama-3.1-8b-instruct")


def _prompt():
    return [{"role": "system", "content": "Eres SKY IA."},
            {"role": "user", "content": "Define un objetivo de investigación."}]


@pytest.mark.parametrize("provider,domain", [
    ("openrouter", "https://openrouter.ai/api/v1/chat/completions"),
    ("mistral", "https://api.mistral.ai/v1/chat/completions"),
    ("groq", "https://api.groq.com/openai/v1/chat/completions"),
    ("cloudflare", "https://api.cloudflare.com/client/v4/accounts/"),
])
def test_explicit_provider_real_request_shape_never_uses_dynamic_host(
        api_keys, provider, domain):
    opener = FakeOpener()
    with patch.object(cloud.request, "build_opener", return_value=opener):
        text = cloud.reply(provider, _prompt(), max_output_tokens=150)
    assert text == "Respuesta controlada de SKY"
    assert len(opener.calls) == 1
    request, timeout = opener.calls[0]
    assert request.full_url.startswith(domain)
    assert request.full_url.startswith("https://")
    assert timeout == 45
    assert request.get_method() == "POST"
    request_json = json.loads(request.data)
    assert request_json["messages"] == _prompt()
    assert request_json["stream"] is False
    assert request_json["max_tokens"] == 150
    assert "authorization" in [k.lower() for k in request.headers]
    assert "test_server_side_only" not in request.data.decode()


def test_only_optional_configured_accounts_are_offered(api_keys, monkeypatch):
    assert set(cloud.ready_names()) == set(cloud.OPTIONAL_PROVIDERS)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN")
    monkeypatch.delenv("MISTRAL_API_KEY")
    assert set(cloud.ready_names()) == {"openrouter", "groq"}


def test_openrouter_free_router_default_never_bills_paid_models(api_keys, monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "premium-large")
    with pytest.raises(cloud.CloudProviderUnavailable, match=":free"):
        cloud.configuration("openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-free:free")
    assert cloud.configuration("openrouter").model == "test-free:free"
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/free")
    assert cloud.configuration("openrouter").model == "openrouter/free"


def test_cloudflare_requires_workers_ai_account_and_model(api_keys, monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "https://attacker.example")
    with pytest.raises(cloud.CloudProviderUnavailable):
        cloud.configuration("cloudflare")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "b" * 32)
    monkeypatch.setenv("CLOUDFLARE_AI_MODEL", "openai/gpt-paid")
    with pytest.raises(cloud.CloudProviderUnavailable):
        cloud.configuration("cloudflare")


def test_quota_error_preserves_provider_choice_no_hidden_retry(api_keys):
    opener = FakeOpener(exception=error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=429, msg="Too Many Requests", hdrs={}, fp=None))
    with patch.object(cloud.request, "build_opener", return_value=opener):
        with pytest.raises(cloud.CloudProviderRateLimited):
            cloud.reply("openrouter", _prompt())
    assert len(opener.calls) == 1


def test_reject_redirects_and_tool_call_outputs(api_keys):
    opener = FakeOpener(exception=error.HTTPError(
        url="https://api.mistral.ai/v1/chat/completions",
        code=302, msg="redirect", hdrs={}, fp=None))
    with patch.object(cloud.request, "build_opener", return_value=opener):
        with pytest.raises(cloud.CloudProviderUnavailable):
            cloud.reply("mistral", _prompt())
    assert len(opener.calls) == 1
    opener = FakeOpener(body={"choices": [{"message": {
        "content": None, "tool_calls": [{"id": "not-allowed"}]}}]})
    with patch.object(cloud.request, "build_opener", return_value=opener):
        with pytest.raises(cloud.CloudProviderUnavailable):
            cloud.reply("groq", _prompt())


def test_reject_unknown_provider_and_invalid_message_before_network(api_keys):
    with pytest.raises(cloud.CloudProviderUnavailable):
        cloud.configuration("arbitrary-host")
    with pytest.raises(ValueError):
        cloud.reply("groq", [{"role": "tool", "content": "open secrets"}])
    with pytest.raises(ValueError):
        cloud.reply("groq", [{"role": "user", "content": "x" * 4001}])
