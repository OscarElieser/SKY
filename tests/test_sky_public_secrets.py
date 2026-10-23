"""Regresión: despliegue seguro mediante secretos montados; sin tocar Docker real."""
import base64
import types
import sys


def test_public_mode_accepts_file_secrets(monkeypatch, tmp_path):
    from metaverse import deployment_v102, distributed_limits
    key_file = tmp_path / "api_key"
    mfa_file = tmp_path / "mfa"
    key_file.write_text("test-public-owner-secret-" + "x" * 48)
    mfa_file.write_text(base64.b32encode(b"01234567890123456789012345678901").decode())
    monkeypatch.delenv("SKY_API_KEY", raising=False)
    monkeypatch.delenv("SKY_OWNER_MFA_SECRET", raising=False)
    monkeypatch.setenv("SKY_API_KEY_FILE", str(key_file))
    monkeypatch.setenv("SKY_OWNER_MFA_SECRET_FILE", str(mfa_file))
    monkeypatch.setenv("SKY_DEPLOYMENT_MODE", "public")
    monkeypatch.setenv("SKY_TRUSTED_HOSTS", "sky.test")
    monkeypatch.setenv("SKY_REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("SKY_BEHIND_TLS_PROXY", "1")
    monkeypatch.setenv("SKY_CREATIVE_WORKER", "0")
    monkeypatch.setattr(distributed_limits, "redis_client", lambda: object())
    assert deployment_v102.validate_environment()["mode"] == "public"


def test_redis_from_url_reads_mounted_password(monkeypatch, tmp_path):
    from metaverse import distributed_limits
    password_file = tmp_path / "redis_password"
    password_file.write_text("test-redis-secret-example\n")
    monkeypatch.delenv("SKY_REDIS_PASSWORD", raising=False)
    monkeypatch.setenv("SKY_REDIS_PASSWORD_FILE", str(password_file))
    monkeypatch.setenv("SKY_REDIS_URL", "redis://redis:6379/0")
    calls = []
    class FakeRedis:
        @staticmethod
        def from_url(url, **kwargs):
            calls.append((url, kwargs))
            return types.SimpleNamespace(ping=lambda: True)
    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(Redis=FakeRedis))
    monkeypatch.setattr(distributed_limits, "_REDIS", None)
    assert distributed_limits.redis_client() is not None
    assert calls[0][1]["password"] == "test-redis-secret-example"
    monkeypatch.setattr(distributed_limits, "_REDIS", None)


def test_public_bootstrap_does_not_reveal_owner_key(monkeypatch):
    from fastapi.testclient import TestClient
    from metaverse import api
    monkeypatch.setattr(api, "api_token", lambda: "should-stay-private-123")
    client = TestClient(api.app)
    monkeypatch.setenv("SKY_DEPLOYMENT_MODE", "public")
    assert client.get("/api/client/bootstrap").json()["key"] == ""
    monkeypatch.setenv("SKY_DEPLOYMENT_MODE", "local")
    assert client.get("/api/client/bootstrap").json()["key"] == "should-stay-private-123"
