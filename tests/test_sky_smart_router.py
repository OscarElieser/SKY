"""SKY Automatic regression: no hidden cloud transfer and local-first failover."""
import pytest
from neural_core import sky_smart_router as router
from neural_core import sky_inference_gateway as inference
from neural_core import sky_optional_cloud_providers as optional


@pytest.fixture(autouse=True)
def reset_router(monkeypatch):
    monkeypatch.delenv("SKY_AUTO_CLOUD_ORDER", raising=False)
    with router._LOCK:
        router._COOLDOWN.clear()


def messages():
    return [{"role": "system", "content": "Eres SKY"},
            {"role": "user", "content": "Explica el pensamiento lógico"}]


def test_local_model_is_always_first_even_if_cloud_authorized(monkeypatch):
    local_calls = []
    cloud_calls = []
    def local_reply(msg, max_output_tokens):
        local_calls.append(msg[-1]["content"])
        return {"respuesta": "Responde SKY", "proveedor": "ollama",
                "nube": False, "acciones_ejecutadas": False}
    monkeypatch.setattr(inference, "generate", local_reply)
    monkeypatch.setattr(optional, "reply", lambda *a, **kw: cloud_calls.append(a))
    monkeypatch.setenv("SKY_AUTO_CLOUD_ORDER", "groq,openrouter")
    out = router.generate(messages(), cloud_consent=True, private_cloud_consent=True)
    assert out["respuesta"] == "Responde SKY"
    assert out["ruta"] == "SKY_AUTO_LOCAL"
    assert out["nube"] is False and not out["alternativa"]
    assert local_calls == ["Explica el pensamiento lógico"]
    assert cloud_calls == []


def test_no_external_calls_when_local_missing_and_consent_absent(monkeypatch):
    monkeypatch.setattr(inference, "generate",
                        lambda *a, **k: (_ for _ in ()).throw(
                            inference.InferenceUnavailable("offline")))
    cloud_calls = []
    monkeypatch.setattr(router, "_configured", lambda name: True)
    monkeypatch.setattr(router, "_try_cloud", lambda *a: cloud_calls.append(a))
    monkeypatch.setenv("SKY_AUTO_CLOUD_ORDER", "groq,openrouter")
    for consent, private in [(False, False), (True, False)]:
        with pytest.raises(router.AutoRouteUnavailable):
            router.generate(messages(), cloud_consent=consent,
                            private_cloud_consent=private)
    assert cloud_calls == []


def test_approved_cloud_can_be_selected_automatically_after_local_failure(monkeypatch):
    monkeypatch.setattr(inference, "generate",
                        lambda *a, **k: (_ for _ in ()).throw(
                            inference.InferenceUnavailable("offline")))
    monkeypatch.setattr(router, "_configured", lambda name: True)
    monkeypatch.setenv("SKY_AUTO_CLOUD_ORDER", "groq,openrouter")
    called = []
    def cloud_reply(name, msgs):
        called.append(name)
        return "Respuesta autorizada"
    monkeypatch.setattr(router, "_try_cloud", cloud_reply)
    result = router.generate(messages(), cloud_consent=True,
                             private_cloud_consent=True)
    assert called == ["groq"] and result["proveedor"] == "groq"
    assert result["ruta"] == "SKY_AUTO_EXTERNO_AUTORIZADO"
    assert result["nube"] is True
    assert result["acciones_ejecutadas"] is False


def test_quota_cools_down_first_provider_and_tries_next_at_most_twice(monkeypatch):
    monkeypatch.setattr(inference, "generate",
                        lambda *a, **k: (_ for _ in ()).throw(
                            inference.InferenceBusy("full")))
    monkeypatch.setattr(router, "_configured", lambda name: True)
    monkeypatch.setenv("SKY_AUTO_CLOUD_ORDER", "groq,openrouter,mistral")
    calls = []
    def candidate(name, _messages):
        calls.append(name)
        if name == "groq":
            raise optional.CloudProviderRateLimited("429")
        return "Otra respuesta autorizada"
    monkeypatch.setattr(router, "_try_cloud", candidate)
    out = router.generate(messages(), cloud_consent=True,
                          private_cloud_consent=True)
    assert calls == ["groq", "openrouter"]
    assert out["proveedor"] == "openrouter"
    calls.clear()
    out = router.generate(messages(), cloud_consent=True,
                          private_cloud_consent=True)
    assert calls == ["openrouter"]
    assert out["proveedor"] == "openrouter"


def test_server_allowlist_is_explicit_and_sanitized(monkeypatch):
    monkeypatch.setenv("SKY_AUTO_CLOUD_ORDER", "groq,openrouter,groq")
    assert router.approved_cloud_order() == ("groq", "openrouter")
    monkeypatch.setenv("SKY_AUTO_CLOUD_ORDER", "https://bad.example")
    with pytest.raises(router.AutoRouteUnavailable):
        router.approved_cloud_order()
    monkeypatch.delenv("SKY_AUTO_CLOUD_ORDER")
    assert router.approved_cloud_order() == ()


def test_busy_without_permission_is_429_not_a_hidden_cloud_request(monkeypatch):
    monkeypatch.setattr(inference, "generate",
                        lambda *a, **k: (_ for _ in ()).throw(
                            inference.InferenceBusy("full")))
    with pytest.raises(router.AutoRouteBusy):
        router.generate(messages())


def test_local_only_is_never_overridden_by_cloud_permission(monkeypatch):
    monkeypatch.setattr(inference, "generate",
                        lambda *a, **k: (_ for _ in ()).throw(
                            inference.InferenceUnavailable("offline")))
    monkeypatch.setenv("SKY_AUTO_CLOUD_ORDER", "mistral")
    monkeypatch.setattr(router, "_configured", lambda name: True)
    def never(*args):
        raise AssertionError("Cloud was called in local-only")
    monkeypatch.setattr(router, "_try_cloud", never)
    with pytest.raises(router.AutoRouteUnavailable):
        router.generate(messages(), cloud_consent=True,
                        private_cloud_consent=True, local_only=True)


def test_reject_invalid_turn_before_any_model(monkeypatch):
    monkeypatch.setattr(inference, "generate", lambda *a, **k:
                        (_ for _ in ()).throw(AssertionError("unexpected")))
    with pytest.raises(ValueError):
        router.generate([{"role": "tool", "content": "run"}])
