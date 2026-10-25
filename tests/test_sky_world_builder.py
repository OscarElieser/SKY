"""Real integration tests for SKY's optional procedural campus builder."""
from __future__ import annotations

from test_sky_v9_7_creative import env, H
from metaverse.world_builder import build_campus, _floors


def test_recognized_prompt_produces_real_validated_editable_geometry():
    description = ("Creá un centro educativo futurista de tres plantas "
                   "con laboratorio de informática, aula interactiva, "
                   "biblioteca y salón de videoconferencias.")
    scene, plan = build_campus(description, seed=42)
    assert plan["floors"] == 3
    assert plan["generated_real_geometry"] is True
    assert scene["theme"] == "estudio"
    assert len(scene["objects"]) == plan["geometry_objects"]
    names = {o["name"] for o in scene["objects"]}
    assert "Edificio principal" in names
    assert "Laboratorio de informática" in names
    assert "Salón de videoconferencias" in names
    assert "Biblioteca" in names
    assert {"Separador nivel 1", "Separador nivel 2", "Separador nivel 3"} <= names
    assert len({o["id"] for o in scene["objects"]}) == len(scene["objects"])
    assert build_campus(description, seed=42)[1] == plan
    assert any("no interiores" in s or "no interiores" in s.lower()
               for s in plan["limitations"])


def test_quantity_parser_boundaries():
    assert _floors("edificio de 5 pisos") == 5
    assert _floors("edificio de seis niveles") == 6
    assert _floors("edificio de cinco plantas") == 5
    assert _floors("centro educativo") == 2


def test_private_campus_api_persists_and_handles_conflicts(env):
    client, _ = env
    created = client.post("/api/worlds", headers=H,
        json={"name": "Campus SKY", "prompt": "Universo SKY", "seed": 3})
    assert created.status_code == 201, created.text
    wid = created.json()["id"]
    path = f"/api/worlds/{wid}/build-campus"
    body = {"prompt": "Centro educativo de 3 plantas con informática y videoconferencias",
            "seed": 21, "version": 1}
    assert client.post(path, json=body).status_code == 401
    result = client.post(path, headers=H, json=body)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["plan"]["floors"] == 3
    assert data["world"]["version"] == 2
    saved = client.get(f"/api/worlds/{wid}", headers=H).json()
    assert saved["version"] == 2
    assert saved["scene"]["objects"] == data["world"]["scene"]["objects"]
    assert client.post(path, headers=H, json=body).status_code == 409
    reject = client.post(path, headers=H,
        json={"prompt": "Dibujame un coche fotorrealista", "seed": 10, "version": 2})
    assert reject.status_code == 422
    assert client.get(f"/api/worlds/{wid}", headers=H).json()["version"] == 2
    assert client.post(path, headers=H, json={**body, "version": 2, "append": True}).status_code == 422
    exported = client.get(f"/api/worlds/{wid}/export.glb", headers=H)
    assert exported.status_code == 200
    assert exported.content[:4] == b"glTF"
    # Legacy generation remains untouched and accessible after new builder.
    old = client.post(f"/api/worlds/{wid}/generate", headers=H,
        json={"prompt": "Bosque con árboles", "seed": 5, "version": 2})
    assert old.status_code == 200, old.text
    assert old.json()["version"] == 3


def test_campus_avatar_color_events_are_validated_and_shared(env):
    client, _ = env
    w = client.post("/api/worlds", headers=H,
        json={"name": "Campus compartido", "prompt": "Campus educativo", "seed": 8}).json()
    def ticket():
        return client.post("/api/ws-ticket", headers=H, json={}).json()["ticket"]
    with client.websocket_connect(f'/api/ws/{w["id"]}?ticket={ticket()}') as a:
        pa = a.receive_json()
        assert pa["type"] == "peers"
        assert a.receive_json()["type"] == "join"
        with client.websocket_connect(f'/api/ws/{w["id"]}?ticket={ticket()}') as b:
            pb = b.receive_json()
            assert pb["type"] == "peers"
            assert len(pb["peers"]) == 2
            assert a.receive_json()["type"] == "join"
            assert b.receive_json()["type"] == "join"
            b.send_json({"type": "customize", "color": "#ab3c9d"})
            event_a = a.receive_json()
            event_b = b.receive_json()
            assert event_a["type"] == "customize" and event_b["type"] == "customize"
            assert event_a["peer"]["color"] == "#AB3C9D"
            assert event_b["peer"]["id"] == pb["you"]
        assert a.receive_json()["type"] == "leave"


def test_build_features_are_bound_to_actual_existing_hud(env):
    client, _ = env
    html = client.get("/world").text
    js = client.get("/static/sky3d.js").text
    assert 'id="build-campus"' in html
    assert 'id="avatar-color"' in html
    assert "/static/sky-world-physics.js" in html
    assert "/build-campus" in js
    assert "SKYWorldPhysics.resolveMovement(" in js
    assert "function drawAvatar(" in js
    assert "drawAvatar(peer.position,peer.color," in js
    assert "for(let ob of [...(world?.scene?.objects||[]),...avatars2d])" in js
