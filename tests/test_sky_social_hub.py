"""SKY Social Hub: pruebas offline, sin cuentas ni llamadas externas reales."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import pytest
from neural_core import sky_social_hub as hub
from neural_core import sky_social_intent


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_SOCIAL_HUB_DB", str(tmp_path / "social.sqlite3"))
    monkeypatch.setenv("SKY_METRICAS", "0")
    monkeypatch.delenv("SKY_SOCIAL_WORKER_ENABLED", raising=False)
    for env in hub.ENV.values():
        monkeypatch.delenv(env, raising=False)


def test_capabilities_no_se_finge_conexion():
    caps = hub.capabilities()
    assert caps["controller"] == "SKY"
    assert caps["autolikes"] is False
    assert caps["autofollows"] is False
    assert not any(x["account_connected"] for x in caps["platforms"])
    for platform in ("instagram", "tiktok", "snapchat"):
        match = next(x for x in caps["platforms"] if x["platform"] == platform)
        assert match["mode"] == "draft_only" and not match["text_publish_supported"]


def test_create_draft_no_posts_without_approval():
    post = hub.draft("x", "Contenido original desde SKY.")
    assert post["status"] == "draft" and post["external_id"] is None
    assert hub.publish_approved(post["id"]) is None
    with pytest.raises(PermissionError):
        hub.approve(post["id"], owner_approved=False)
    assert hub.list_items()[0]["status"] == "draft"


def test_single_approved_x_post(monkeypatch):
    created = hub.draft("x", "Una publicación original sobre enseñanza.")
    approved = hub.approve(created["id"], owner_approved=True)
    assert approved["status"] == "approved"
    monkeypatch.setenv("SKY_SOCIAL_X_ACCESS_TOKEN", "authorized-oauth-user-token")
    calls = []
    def fake_http(url, token, data):
        calls.append((url, token, data))
        return {"data": {"id": "123456789"}}
    monkeypatch.setattr(hub, "_http", fake_http)
    published = hub.publish_approved(created["id"])
    assert published["status"] == "published" and published["external_id"] == "123456789"
    assert calls[0][0] == "https://api.x.com/2/tweets"
    assert calls[0][2]["text"] == created["body"]
    assert hub.publish_approved(created["id"]) is None
    assert len(calls) == 1


def test_failed_publish_is_not_retried_or_falsely_reported(monkeypatch):
    item = hub.draft("facebook", "Información institucional validada.")
    hub.approve(item["id"], owner_approved=True)
    monkeypatch.setenv("SKY_SOCIAL_FACEBOOK_PAGE_TOKEN", "authorized-page-access-token")
    monkeypatch.setenv("SKY_SOCIAL_FACEBOOK_PAGE_ID", "12345678900")
    attempts = []
    def fail(*args, **kwargs):
        attempts.append(1)
        raise TimeoutError("User token data private")
    monkeypatch.setattr(hub, "_http", fail)
    result = hub.publish_approved(item["id"])
    assert result["status"] == "needs_review" and result["attempts"] == 1
    assert result["error_class"] == "TimeoutError"
    assert "User token" not in repr(result)
    assert hub.publish_approved(item["id"]) is None
    assert len(attempts) == 1


def test_threads_two_step_confirmation(monkeypatch):
    item = hub.draft("threads", "Aprendamos tecnología responsable.")
    hub.approve(item["id"], owner_approved=True)
    monkeypatch.setenv("SKY_SOCIAL_THREADS_ACCESS_TOKEN", "authorized-threads-token")
    calls = []
    def fake(url, token, payload):
        calls.append((url, payload))
        return {"id": "container12345"} if url.endswith("/threads") else {"id": "post999"}
    monkeypatch.setattr(hub, "_http", fake)
    result = hub.publish_approved(item["id"])
    assert result["status"] == "published"
    assert result["container_id"] == "container12345"
    assert result["external_id"] == "post999"
    assert calls[1][1] == {"creation_id": "container12345"}


def test_unsupported_platform_requires_real_media_integration():
    post = hub.draft("tiktok", "Un tema para un video original.")
    with pytest.raises(hub.SocialUnavailable):
        hub.approve(post["id"], owner_approved=True)
    assert hub.get(post["id"])["status"] == "draft"


def test_schedule_only_after_time(monkeypatch):
    item = hub.draft("x", "Una publicación programada.")
    later = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    hub.approve(item["id"], owner_approved=True, scheduled_at=later)
    monkeypatch.setenv("SKY_SOCIAL_X_ACCESS_TOKEN", "authorized-oauth-user-token")
    monkeypatch.setattr(hub, "_http", lambda *args: pytest.fail("No debe publicar antes de tiempo"))
    assert hub.publish_approved(item["id"]) is None
    assert hub.get(item["id"])["status"] == "approved"


def test_worker_requires_flag_and_approvals(monkeypatch):
    post = hub.draft("x", "Este es un post del propietario.")
    assert hub.worker_tick()["active"] is False
    monkeypatch.setenv("SKY_SOCIAL_WORKER_ENABLED", "1")
    assert hub.worker_tick()["processed"] == 0
    hub.approve(post["id"], owner_approved=True)
    monkeypatch.setenv("SKY_SOCIAL_X_ACCESS_TOKEN", "authorized-oauth-user-token")
    monkeypatch.setattr(hub, "_http", lambda *args: {"data": {"id": "post-one"}})
    tick = hub.worker_tick()
    assert tick["processed"] == 1 and tick["status"] == "published"
    assert hub.worker_tick()["processed"] == 0


def test_engagement_only_manual_never_worker(monkeypatch):
    action = hub.engagement_x("like", "135791357913579")
    hub.approve(action["id"], owner_approved=True)
    monkeypatch.setenv("SKY_SOCIAL_WORKER_ENABLED", "1")
    assert hub.worker_tick()["processed"] == 0
    monkeypatch.setenv("SKY_SOCIAL_X_ACCESS_TOKEN", "authorized-oauth-user-token")
    monkeypatch.setenv("SKY_SOCIAL_X_USER_ID", "123456789")
    records = []
    def fake(url, token, payload):
        records.append((url, payload))
        return {"data": {"liked": True}}
    monkeypatch.setattr(hub, "_http", fake)
    result = hub.publish_approved(action["id"])
    assert result["status"] == "published"
    assert "/123456789/likes" in records[0][0]


def test_reply_x_is_not_automatic(monkeypatch):
    action = hub.draft("x", "Gracias por tu mensaje.", "reply", "135791357913579")
    hub.approve(action["id"], owner_approved=True)
    monkeypatch.setenv("SKY_SOCIAL_X_ACCESS_TOKEN", "authorized-oauth-user-token")
    recorded = []
    monkeypatch.setattr(hub, "_http", lambda url, token, payload:
                        (recorded.append(payload) or {"data": {"id": "answer123"}}))
    result = hub.publish_approved(action["id"])
    assert result["status"] == "published"
    assert recorded[0]["reply"] == {"in_reply_to_tweet_id": "135791357913579"}


def test_kpi_are_honestly_tagged_as_owner_entered():
    post = hub.draft("facebook", "Resultados sin inventar.")
    with hub._db() as conn:
        conn.execute("UPDATE outbound SET status='published' WHERE id=?", (post["id"],))
    result = hub.record_metrics(post["id"], views=100, likes=8, comments=2)
    assert result["source"] == "manual_unverified"
    report = hub.insights()
    assert report["source"] == "owner_entered_unverified"
    assert report["sample_engagement"]["facebook"]["average_engagement_pct"] == 10
    assert report["sample_engagement"]["facebook"]["sufficient_data"] is False
    assert report["growth_guaranteed"] is False


def test_never_save_secrets_or_engagement_farm_commands(monkeypatch):
    with pytest.raises(hub.SocialError):
        hub.draft("x", "No.", "like", "123456789")
    with pytest.raises(hub.SocialError):
        hub.engagement_x("like", "")
    with pytest.raises(hub.SocialError):
        hub.draft("youtube", "Texto")
    with pytest.raises(hub.SocialError):
        hub.draft("x", "L" * 281)


def test_voice_intent_prepares_only_a_draft(monkeypatch):
    import sys
    from types import ModuleType
    social_hub_api = ModuleType("metaverse.social_hub_api")
    monkeypatch.setitem(sys.modules, "metaverse.social_hub_api", social_hub_api)
    parsed = sky_social_intent.parse("SKY, redacta una publicación para Threads sobre innovación educativa")
    assert parsed["platform"] == "threads"
    assert "innovación educativa" in parsed["topic"]
    assert sky_social_intent.parse("SKY publica esto en Threads inmediatamente") is None
    monkeypatch.setattr(social_hub_api, "generate_draft", lambda *args, **kw:
                        {"id": "soc_test", "body": "Texto único preparado por IA."})
    result = sky_social_intent.prepare("SKY redacta una publicación para Threads sobre innovación educativa")
    assert result["publicado"] is False and result["requiere_aprobacion"] is True
    assert "Texto único" in result["mensaje"]
