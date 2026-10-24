"""Functional GLB, interactive classrooms and scene-state integration tests."""
from __future__ import annotations

import json
import struct
from fastapi.testclient import TestClient

from metaverse.avatar_glb import build_avatar_glb
from metaverse.engine import validate_object
from metaverse.world_builder import build_campus
from test_sky_v9_7_creative import env, H


PROMPT = ("Centro educativo de tres plantas con laboratorio de informática, "
          "aula interactiva, biblioteca y videoconferencias")


def _decode_glb(glb):
    assert glb[:4] == b"glTF"
    magic, version, length = struct.unpack_from("<4sII", glb)
    assert magic == b"glTF" and version == 2 and length == len(glb)
    size, kind = struct.unpack_from("<I4s", glb, 12)
    assert kind == b"JSON"
    obj = json.loads(glb[20:20+size])
    binary_length, binary_kind = struct.unpack_from("<I4s", glb, 20+size)
    assert binary_kind == b"BIN\x00"
    assert 12+8+size+8+binary_length == len(glb)
    assert obj["buffers"][0]["byteLength"] <= binary_length
    return obj


def test_original_avatar_is_real_self_contained_glb_with_walk_tracks():
    glb=build_avatar_glb()
    asset=_decode_glb(glb)
    assert glb is build_avatar_glb()   # cached deterministic offline asset
    assert len(glb)<2000000
    assert asset["asset"]["version"]=="2.0"
    assert len(asset["meshes"])==1
    assert len(asset["nodes"])>=10
    walk=next(a for a in asset["animations"] if a["name"]=="walk")
    assert len(walk["channels"])>=4
    assert {x["target"]["path"] for x in walk["channels"]}=={"rotation"}
    assert not asset.get("skins")
    assert not asset["buffers"][0].get("uri")


def test_avatar_endpoint_is_private_and_returns_glb(env):
    client,_=env
    url="/api/metaverse/avatars/default.glb"
    assert client.get(url).status_code==401
    r=client.get(url,headers=H)
    assert r.status_code==200,r.text[:100]
    assert r.headers["content-type"].startswith("model/gltf-binary")
    _decode_glb(r.content)


def test_campus_has_walkable_entrances_and_real_reversible_objects():
    scene,report=build_campus(PROMPT,seed=29)
    objects=scene["objects"]
    assert report["interactive_objects"]>=10
    names={o["name"] for o in objects}
    assert "Laboratorio de informática" in names
    assert "Aula interactiva" in names
    assert any(n.startswith("Mesa ") for n in names)
    assert any(n.startswith("Computadora ") for n in names)
    assert any(n.startswith("Pizarra ") for n in names)
    assert any(n.startswith("Puerta ") for n in names)
    doors=[o for o in objects if o.get("interaction",{}).get("type")=="door"]
    assert all(o["interaction"]["active"] for o in doors)
    assert len(objects)<180
    assert len({o["id"] for o in objects})==len(objects)
    for o in objects:assert validate_object(o)==o


def test_persistent_light_board_and_door_toggles_with_version_conflicts(env):
    client,_=env
    world=client.post("/api/worlds",headers=H,
        json={"name":"Aula real SKY","prompt":"Laboratorio","seed":41}).json()
    wid=world["id"]
    scene=client.post(f"/api/worlds/{wid}/build-campus",headers=H,
        json={"prompt":PROMPT,"seed":41,"version":1}).json()["world"]
    initial=scene["version"]
    devices={o["interaction"]["type"]:o for o in scene["scene"]["objects"]
             if "interaction" in o}
    for kind in ("door","light","terminal","whiteboard"):
        device=devices[kind]
        path=f"/api/worlds/{wid}/interact"
        payload={"object_id":device["id"],"version":initial}
        assert client.post(path,json=payload).status_code==401
        updated=client.post(path,headers=H,json=payload)
        assert updated.status_code==200,updated.text
        assert updated.json()["world"]["version"]==initial+1
        state=next(o for o in updated.json()["world"]["scene"]["objects"]
                   if o["id"]==device["id"])["interaction"]["active"]
        assert state is not device["interaction"]["active"]
        assert client.post(path,headers=H,json=payload).status_code==409
        persisted=client.get(f"/api/worlds/{wid}",headers=H).json()
        assert persisted["version"]==initial+1
        assert next(o for o in persisted["scene"]["objects"]
                    if o["id"]==device["id"])["interaction"]["active"]==state
        revert=client.post(path,headers=H,json={**payload,"version":initial+1})
        assert revert.status_code==200
        initial+=2


def test_socket_receives_persisted_interaction_after_commit(env):
    client,_=env
    wid=client.post("/api/worlds",headers=H,
        json={"name":"Clase compartida","prompt":"Estudio","seed":14}).json()["id"]
    built=client.post(f"/api/worlds/{wid}/build-campus",headers=H,
        json={"prompt":PROMPT,"seed":14,"version":1}).json()["world"]
    target=next(o for o in built["scene"]["objects"] if
                o.get("interaction",{}).get("type")=="terminal")
    ticket=client.post("/api/ws-ticket",headers=H,json={}).json()["ticket"]
    with client.websocket_connect(f"/api/ws/{wid}?ticket={ticket}") as ws:
        assert ws.receive_json()["type"]=="peers"
        assert ws.receive_json()["type"]=="join"
        changed=client.post(f"/api/worlds/{wid}/interact",headers=H,
            json={"object_id":target["id"],"version":built["version"]})
        assert changed.status_code==200
        event=ws.receive_json()
        assert event["type"]=="interact"
        assert event["object_id"]==target["id"]
        assert event["version"]==built["version"]+1
        assert event["active"] is True


def test_untrusted_script_interaction_is_rejected(env):
    client,_=env
    existing=client.post("/api/worlds",headers=H,
        json={"name":"Mundo seguro","prompt":"Estudio","seed":7}).json()
    bad={"version":existing["version"],"object":{
        "name":"Externo","kind":"box","position":[0,0,0],"rotation":[0,0,0],
        "scale":[1,1,1],"color":"#112233",
        "interaction":{"type":"javascript","active":True,"description":"<script>alert(1)</script>"}}}
    r=client.post(f'/api/worlds/{existing["id"]}/objects',headers=H,json=bad)
    assert r.status_code==422
    assert client.get(f'/api/worlds/{existing["id"]}',headers=H).json()["version"]==1


def test_browser_assets_and_commands_are_actually_wired(env):
    client,_=env
    html=client.get("/world").text
    script=client.get("/static/sky3d.js").text
    assert "/static/sky-avatar-glb.js" in html
    assert 'id="interact"' in html
    assert "api('/api/metaverse/avatars/default.glb')" in script
    assert "SKYAvatarGLB.parse(" in script
    assert "SKYAvatarGLB.pose(" in script
    assert "closestInteractiveObject(" in script
    assert "/interact" in script


def test_teacher_writes_and_reloads_real_whiteboard_notes(env):
    client,_=env
    w=client.post("/api/worlds",headers=H,
        json={"name":"Clase técnica SKY","prompt":"Aula","seed":9}).json()
    wid=w["id"]
    campus=client.post(f"/api/worlds/{wid}/build-campus",headers=H,
        json={"prompt":PROMPT,"seed":9,"version":1}).json()["world"]
    board=next(o for o in campus["scene"]["objects"]
               if o.get("interaction",{}).get("type")=="whiteboard")
    url=f"/api/worlds/{wid}/interact"
    payload={"version":2,"object_id":board["id"],"action":"write",
             "content":"CPU: ejecuta instrucciones. RAM: almacena datos temporales."}
    assert client.post(url,json=payload).status_code==401
    response=client.post(url,headers=H,json=payload)
    assert response.status_code==200,response.text
    assert response.json()["interaction"]["content"]==payload["content"]
    reloaded=client.get(f"/api/worlds/{wid}",headers=H).json()
    stored=next(o for o in reloaded["scene"]["objects"] if o["id"]==board["id"])
    assert stored["interaction"]["content"]==payload["content"]
    assert stored["interaction"]["active"] is True
    assert reloaded["version"]==3
    assert client.post(url,headers=H,json=payload).status_code==409
    bad=client.post(url,headers=H,json={"version":3,"object_id":board["id"],
                                       "action":"write","content":"x"*1300})
    assert bad.status_code==422
    terminal=next(o for o in reloaded["scene"]["objects"]
                  if o.get("interaction",{}).get("type")=="terminal")
    assert client.post(url,headers=H,json={"version":3,"object_id":terminal["id"],
        "action":"write","content":"No permitido"}).status_code==422
    assert client.get(f"/api/worlds/{wid}",headers=H).json()["version"]==3
