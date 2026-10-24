"""Regression: SKY Guardian protects owner's property without mass surveillance."""
import pytest
from fastapi.testclient import TestClient

KEY="sky-guardian-test-owner-auth-key-2026-safe"


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv("SKY_API_KEY",KEY)
    monkeypatch.setenv("SKY_GUARDIAN_DB",str(tmp_path/"guardian.sqlite3"))
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED","0")
    from metaverse.api import app
    with TestClient(app) as instance:
        yield instance


def headers():
    return {"X-SKY-KEY":KEY}


def test_only_owner_can_list_or_create_camera(client):
    assert client.get("/api/sky/guardian/cameras").status_code==401
    assert client.get("/api/sky/guardian/capabilities").status_code==401
    unauthorized=client.post("/api/sky/guardian/cameras",json={
        "name":"Sala","area":"Propiedad autorizada","owner_attested":True})
    assert unauthorized.status_code==401
    no_consent=client.post("/api/sky/guardian/cameras",headers=headers(),json={
        "name":"Sala","area":"Mi propiedad"})
    assert no_consent.status_code==403
    authorized=client.post("/api/sky/guardian/cameras",headers=headers(),json={
        "name":"Entrada","area":"Mi propiedad","owner_attested":True})
    assert authorized.status_code==201,authorized.text
    value=authorized.json()
    assert value["authorized"]
    assert not value["live_video_enabled"]
    assert value["connection_status"]=="not_connected"
    assert not value["biometric_identification_enabled"]
    assert len(client.get("/api/sky/guardian/cameras",headers=headers()).json()["cameras"])==1
    assert client.delete("/api/sky/guardian/cameras/"+value["id"],headers=headers()).json()["removed"]


def test_incidents_are_not_police_reports_or_verified_events(client):
    manual=client.post("/api/sky/guardian/events",headers=headers(),
                       json={"event_type":"smoke_alarm"})
    assert manual.status_code==201,manual.text
    item=manual.json()
    assert item["severity"]=="critical"
    assert item["observation"]=="owner_reported_unverified"
    assert not item["police_contacted"]
    assert not item["alert_dispatched"]
    assert item["requires_human_review"]
    assert client.post(f'/api/sky/guardian/events/{item["id"]}/acknowledge',headers=headers()).json()["acknowledged"]
    listed=client.get("/api/sky/guardian/events",headers=headers()).json()["events"]
    assert listed[0]["acknowledged_at"] is not None
    assert client.post("/api/sky/guardian/events",headers=headers(),
                       json={"event_type":"identify_person_by_face"}).status_code==422


def test_satellite_sources_are_public_links_not_live_tracking(client):
    catalogue=client.get("/api/sky/guardian/capabilities",headers=headers())
    assert catalogue.status_code==200,catalogue.text
    result=catalogue.json()
    assert result["owner"]=="SKY CORE"
    assert not result["camera_streaming_ready"]
    assert not result["satellite_imagery_download_ready"]
    assert not result["police_or_traffic_system_access"]
    assert not result["person_tracking"]
    assert not result["face_or_person_identification"]
    assert not result["auto_report_to_authorities"]
    assert all(x["url"].startswith("https://") and not x["live_street_video"]
               for x in result["satellite_sources"])


def test_events_reject_unknown_camera_and_keep_retention_limit(client,monkeypatch):
    from neural_core import sky_guardian as g
    assert client.post("/api/sky/guardian/events",headers=headers(),json={
        "event_type":"camera_offline","camera_id":"cam_"+"0"*24}).status_code==422
    first=g.report_event("door_open")
    with g._connection() as db:
        db.execute("UPDATE incidents SET created_at=0 WHERE id=?",(first["id"],))
    assert not any(item["id"]==first["id"] for item in g.recent_events())
