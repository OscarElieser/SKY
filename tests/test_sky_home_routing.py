"""Regression: no hidden cloud transfer or unapproved provider fallback."""
import pytest

from neural_core.sky_home_routing import choose_home_route


def route(**kwargs):
    return choose_home_route(configured_cloud=("openai", "gemini"), **kwargs)


def test_no_cloud_without_consent_even_with_keys():
    result = route(local_available=True)
    assert result.provider == "ollama" and not result.remote
    assert route(local_available=False).provider is None


def test_home_prefers_cloud_only_after_explicit_general_consent():
    result = route(local_available=True, private_data=False, cloud_consent=True)
    assert result.provider == "gemini" and result.remote


def test_private_cloud_needs_two_consents():
    result = route(local_available=True, cloud_consent=True)
    assert result.provider == "ollama" and not result.remote
    result = route(local_available=True, cloud_consent=True, private_cloud_consent=True)
    assert result.provider == "gemini" and result.remote


def test_explicit_cloud_request_never_falls_back_silently():
    assert route(requested="openai", local_available=True).provider is None
    assert route(requested="openai", cloud_consent=True, private_data=True).provider is None
    assert route(requested="openai", cloud_consent=True, private_cloud_consent=True).provider == "openai"
    assert route(requested="anthropic", cloud_consent=True, private_cloud_consent=True).provider is None


def test_local_only_is_hard_block_for_cloud():
    assert route(requested="openai", cloud_consent=True, private_cloud_consent=True, local_only=True).provider is None
    assert route(local_available=True, cloud_consent=True, private_cloud_consent=True, local_only=True).provider == "ollama"


def test_no_provider_returns_blocked_not_fake_success():
    assert choose_home_route(local_available=False, cloud_consent=True, private_cloud_consent=True, configured_cloud=()).provider is None


def test_unknown_provider_rejected():
    with pytest.raises(ValueError):
        route(requested="unknown")


def test_local_requested_never_changes_to_cloud():
    assert route(requested="ollama", local_available=False, cloud_consent=True, private_cloud_consent=True).provider is None


@pytest.mark.parametrize("provider", ["openrouter", "cloudflare", "mistral", "groq"])
def test_optional_cloud_provider_needs_explicit_consent_and_configuration(provider):
    config = (provider,)
    result = choose_home_route(requested=provider, configured_cloud=config,
                               local_available=True, private_data=True,
                               cloud_consent=False, private_cloud_consent=False)
    assert result.provider is None
    blocked = choose_home_route(requested=provider, configured_cloud=config,
                                local_available=True, private_data=True,
                                cloud_consent=True, private_cloud_consent=False)
    assert blocked.provider is None
    allowed = choose_home_route(requested=provider, configured_cloud=config,
                                local_available=True, private_data=True,
                                cloud_consent=True, private_cloud_consent=True)
    assert allowed.provider == provider and allowed.remote
    local_only = choose_home_route(requested=provider, configured_cloud=config,
                                   cloud_consent=True, private_cloud_consent=True,
                                   local_only=True)
    assert local_only.provider is None
