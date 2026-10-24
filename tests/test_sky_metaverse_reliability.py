"""Live SKY metaverse API regressions and client interaction contracts.

Uses the real FastAPI application, isolated SQLite storage and WebSocket, not
a claim that a headset, remote browser or large-scale deployment was tested.
"""
from __future__ import annotations

from pathlib import Path
from fastapi import WebSocketDisconnect
import pytest
from test_sky_v9_7_creative import env, H


def test_create_edit_persist_export_and_conflict(env):
    client, _ = env
    assert client.get("/api/worlds").status_code == 401
    created = client.post("/api/worlds", headers=H,
        json={"name": "Laboratorio de innovación", "prompt": "Bosque con laboratorio educativo", "seed": 12})
    assert created.status_code == 201, created.text
    world = created.json()
    assert world["version"] == 1
    assert len(world["scene"]["objects"]) >= 2
    world_id = world["id"]

    edit = client.post(f"/api/worlds/{world_id}/objects", headers=H,
        json={"version": 1, "object": {"name": "Mi pieza real", "kind": "box",
               "position": [1, 0, 1], "rotation": [0, 0, 0],
               "scale": [1, 2, 1], "color": "#34ACDD"}})
    assert edit.status_code == 200, edit.text
    assert edit.json()["version"] == 2
    assert any(o["name"] == "Mi pieza real" for o in
               client.get(f"/api/worlds/{world_id}", headers=H).json()["scene"]["objects"])
    stale = client.put(f"/api/worlds/{world_id}", headers=H,
        json={"version": 1, "scene": edit.json()["scene"]})
    assert stale.status_code == 409
    export = client.get(f"/api/worlds/{world_id}/export.glb", headers=H)
    assert export.status_code == 200, export.text[:200]
    assert export.content[:4] == b"glTF" and len(export.content) > 200


def test_real_one_time_websocket_presence_and_chat(env):
    client, _ = env
    world = client.post("/api/worlds", headers=H,
        json={"name": "Sala interactiva", "prompt": "Laboratorio 3D", "seed": 19}).json()
    assert client.post("/api/ws-ticket").status_code == 401
    ticket = client.post("/api/ws-ticket", headers=H, json={}).json()["ticket"]
    path = f'/api/ws/{world["id"]}?ticket={ticket}'
    with client.websocket_connect(path) as ws:
        received = ws.receive_json()
        assert received["type"] == "peers"
        assert received["you"]
        assert received["peers"]
        # The server also broadcasts our own join.
        assert ws.receive_json()["type"] == "join"
        ws.send_json({"type": "move", "position": [3, 0, 2]})
        moved = ws.receive_json()
        assert moved["type"] == "move"
        assert moved["peer"]["position"] == [3.0, 0.0, 2.0]
        ws.send_json({"type": "say", "text": "Hola desde SKY"})
        sent = ws.receive_json()
        assert sent["type"] == "say" and sent["text"] == "Hola desde SKY"
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(path) as ws:
            ws.receive_json()


def test_real_websocket_blocks_nonexistent_room(env):
    client, _ = env
    ticket = client.post("/api/ws-ticket", headers=H, json={}).json()["ticket"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/ws/does-not-exist?ticket={ticket}") as ws:
            ws.receive_json()


def test_world_client_has_owner_mfa_and_reconnection_support(env):
    client, _ = env
    script = client.get("/static/sky3d.js").text
    html = client.get("/world").text
    stylesheet = client.get("/static/sky.css").text
    assert "SKYOwnerAuth.begin(secret)" in script
    assert "SKYOwnerAuth?.headers()" in script
    assert "SKYOwnerAuth.logout(secret)" in script
    assert "function scheduleReconnect(id,generation)" in script
    assert "function closePresence()" in script
    assert "window.addEventListener('online'" in script
    assert "function moveAvatar(dx,dz)" in script
    assert "startFallbackRenderer(canvas)" in script
    assert "data-sky-move=\"north\"" in html
    assert "data-sky-move=\"south\"" in html
    assert "sky-mobile-move" in stylesheet


def test_world_api_is_restricted_when_owner_mfa_is_enabled(env, monkeypatch):
    import base64, time
    from metaverse import owner_mfa
    secret = base64.b32encode(b"01234567890123456789012345678901").decode().rstrip("=")
    monkeypatch.setenv("SKY_OWNER_MFA_SECRET", secret)
    owner_mfa.SESSIONS.clear()
    owner_mfa.FAILURES.clear()
    owner_mfa.LAST_TOTP_STEP = -1
    client, _ = env
    assert client.get("/api/worlds", headers=H).status_code == 401
    response = client.post("/api/security/owner-mfa/session", headers=H,
        json={"code": owner_mfa.code_at(time.time())})
    assert response.status_code == 200, response.text
    headers = {**H, "X-SKY-SESSION": response.json()["session"]}
    assert client.get("/api/worlds", headers=headers).status_code == 200
    owner_mfa.SESSIONS.clear()
    owner_mfa.FAILURES.clear()
    owner_mfa.LAST_TOTP_STEP = -1
