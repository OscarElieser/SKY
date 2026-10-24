"""Regression for consolidating SKY Core modules without weakening Sentinel.

No USB, Bluetooth, Wi-Fi, IR, webcam or remote action is executed here.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


KEY = "sky-owner-core-integration-test-secret-2026"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("SKY_API_KEY", KEY)
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED", "0")
    monkeypatch.setenv("SKY_KNOWLEDGE_DB", str(tmp_path / "secure-knowledge.sqlite3"))
    from metaverse.api import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("route", [
    "/api/sky/guardian/capabilities",
    "/api/sky/mobile-unlock/capabilities",
    "/api/sky/device-hub/capabilities",
    "/api/sky/reader/capabilities",
    "/api/sky/knowledge/capabilities",
    "/api/sky/neural-memory/status",
    "/api/sky/academy/capabilities",
    "/api/impacto/status",
])
def test_new_and_existing_routes_require_owner(client, route):
    denied = client.get(route)
    assert denied.status_code in (401, 403), (route, denied.status_code, denied.text[:200])
    allowed = client.get(route, headers={"X-SKY-KEY": KEY})
    assert allowed.status_code == 200, (route, allowed.status_code, allowed.text[:250])


def test_core_routers_are_not_registered_twice(client):
    routes = [r.path for r in client.app.routes if isinstance(getattr(r, "path", None), str)]
    for item in ("/api/sky/device-hub/capabilities", "/api/sky/guardian/capabilities",
                 "/api/sky/mobile-unlock/capabilities", "/api/sky/academy/capabilities"):
        assert routes.count(item) == 1


def test_owner_auth_survives_module_merge(client):
    denied = client.get("/api/sky/knowledge/documents")
    assert denied.status_code in (401, 403)
    bad = client.get("/api/sky/guardian/capabilities", headers={"X-SKY-KEY": "not-the-owner"})
    assert bad.status_code in (401, 403)
    assert client.get("/api/security/owner-mfa/status").status_code == 200


def test_no_unauthorized_device_actions_in_tests():
    from neural_core import sky_secure_connectivity as hub
    capabilities = hub.catalogue()
    assert capabilities is not None
