"""SKY Device Hub tests: no rogue pairing, no network scans without consent."""
from __future__ import annotations

import asyncio
import types

import pytest
from fastapi.testclient import TestClient

KEY = "sky-secure-device-hub-test-owner-key-2026"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_API_KEY", KEY)
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED", "0")
    monkeypatch.setenv("SKY_DEVICE_HUB_DB", str(tmp_path/"devices.sqlite3"))
    from metaverse.api import app
    with TestClient(app) as c:
        yield c


def auth():
    return {"X-SKY-KEY": KEY}


def payload(connector="sky_agent", transport="wifi", **other):
    result = {
        "name": "Mi computadora",
        "device_type": "computer",
        "transport": transport,
        "connector": connector,
        "connection_ref": "Oficina SKY" if connector=="sky_agent" else
                          "remote.sala" if connector=="home_assistant" else "",
        "owner_attested": True,
    }
    result.update(other)
    return result


def test_only_sky_owner_can_discover_and_register(client):
    assert client.get("/api/sky/device-hub/capabilities").status_code == 401
    assert client.post("/api/sky/device-hub/devices", json=payload()).status_code == 401
    assert client.post("/api/sky/device-hub/discover/bluetooth", json={
        "owner_network_confirmed": True
    }).status_code == 401
    assert client.post("/api/sky/device-hub/devices", headers=auth(), json={
        **payload(), "owner_attested": False
    }).status_code == 403
    assert client.post("/api/sky/device-hub/discover/wifi", headers=auth(), json={
        "owner_network_confirmed": False
    }).status_code == 403


def test_device_registry_does_not_falsely_claim_pairing(client):
    result = client.post("/api/sky/device-hub/devices", headers=auth(), json=payload())
    assert result.status_code == 201, result.text
    item = result.json()
    assert item["status"] == "registered_unverified"
    assert item["verified_at"] is None
    assert item["control_permission_granted"] is False
    assert len(client.get("/api/sky/device-hub/devices", headers=auth()).json()["devices"]) == 1
    ident = item["id"]
    assert client.delete(f"/api/sky/device-hub/devices/{ident}", headers=auth()).json()["removed"]
    assert not client.delete(f"/api/sky/device-hub/devices/{ident}", headers=auth()).json()["removed"]


@pytest.mark.parametrize("invalid", [
    {"device_type": "surveillance"},
    {"transport": "internet"},
    {"connector": "remote_shell"},
    {"transport": "bluetooth_le"},
    {"connection_ref": "https://example.com?token=secret"},
    {"connection_ref": "../etc/passwd"},
])
def test_disallow_invalid_hardware_or_connection_methods(client, invalid):
    response = client.post("/api/sky/device-hub/devices",
                           headers=auth(), json=payload(**invalid))
    assert response.status_code == 422


def test_agent_connection_requires_real_pre_registered_agent_and_token(client, monkeypatch):
    from neural_core import dispositivos
    logs = []
    item = client.post("/api/sky/device-hub/devices", headers=auth(),
                       json=payload()).json()
    endpoint = f"/api/sky/device-hub/devices/{item['id']}/probe"
    monkeypatch.setattr(dispositivos, "paired_devices", lambda: [])
    assert client.get(endpoint, headers=auth()).json()["status"] == "agent_not_registered"
    monkeypatch.setattr(dispositivos, "paired_devices", lambda: [{
        "name": "Oficina SKY", "url": "https://sky.example.local",
        "revoked": False,
    }])
    assert client.get(endpoint, headers=auth()).status_code == 403
    def fake_call(url, token, action, timeout):
        logs.append((url, token, action, timeout))
        return {"ok": True, "agent": "SKY Desktop Agent"}
    monkeypatch.setattr(dispositivos, "call_device", fake_call)
    secret = "x" * 40
    response = client.get(endpoint, headers={**auth(),"X-SKY-DEVICE-TOKEN": secret})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "authenticated_agent"
    assert response.json()["commands_sent"] == 0
    assert logs == [("https://sky.example.local", secret, "status", 5)]
    assert secret not in str(client.get("/api/sky/device-hub/devices",
                                        headers=auth()).json())


def test_home_assistant_probes_only_exact_authorized_entity(client, monkeypatch):
    from neural_core import sky_home_assistant as ha
    item = client.post("/api/sky/device-hub/devices", headers=auth(),
                       json=payload("home_assistant", "infrared")).json()
    calls = []
    monkeypatch.setattr(ha, "configurado", lambda: True)
    def fake_request(method, route, timeout):
        calls.append((method, route, timeout))
        return {"entity_id": "remote.sala", "state": "on"}
    monkeypatch.setattr(ha, "_peticion", fake_request)
    result = client.get(f"/api/sky/device-hub/devices/{item['id']}/probe",
                        headers=auth()).json()
    assert result["connected"] and result["verified"]
    assert result["commands_sent"] == 0
    assert result["control_permission_granted"] is False
    assert calls == [("GET", "/api/states/remote.sala", 5)]
    assert client.post("/api/sky/device-hub/devices", headers=auth(),json=payload(
        "home_assistant", "infrared", connection_ref="light.sala"
    )).status_code == 422


def test_ble_discovery_does_not_expose_mac_or_pair(monkeypatch):
    import sys
    from neural_core import sky_secure_connectivity as hub
    class Device:
        def __init__(self, name, address):
            self.name, self.address = name, address
    class Scanner:
        @staticmethod
        async def discover(timeout):
            assert 2 <= timeout <= 6
            return [Device("Mi altavoz", "AA:BB:CC:DD:EE:FF"),
                    Device(None, "00:11:22:33:44:55")]
    monkeypatch.setitem(sys.modules, "bleak", types.SimpleNamespace(BleakScanner=Scanner))
    result = asyncio.run(hub.discover_ble(owner_network_confirmed=True, seconds=2))
    assert result["detected"] == 1
    assert result["devices"] == [{"advertised_name":"Mi altavoz",
                                  "paired":False,"control_available":False}]
    assert "AA:BB" not in str(result)
    assert result["commands_sent"] == 0


def test_wifi_discovery_opt_in_is_advertisements_only(monkeypatch):
    from neural_core import sky_secure_connectivity as hub
    monkeypatch.setattr(hub.importlib.util, "find_spec",
                        lambda name: object() if name == "zeroconf" else None)
    monkeypatch.setattr(hub, "_mdns_scan", lambda duration: [
        {"advertised_name":"Sala TV",
         "service_type":"_googlecast._tcp.local.",
         "connected":False}
    ])
    with pytest.raises(PermissionError):
        asyncio.run(hub.discover_wifi(owner_network_confirmed=False, seconds=2))
    value = asyncio.run(hub.discover_wifi(owner_network_confirmed=True, seconds=2))
    assert value["detected"] == 1
    assert not value["connected"]
    assert value["status"] == "advertisements_only"


def test_defensive_assessment_is_plan_not_unapproved_exploitation(client):
    without = client.post("/api/sky/device-hub/security/audit-plan", headers=auth(),
                          json={"asset_type":"website", "owner_attested":False})
    assert without.status_code == 403
    done = client.post("/api/sky/device-hub/security/audit-plan", headers=auth(),
                       json={"asset_type":"computer", "owner_attested":True})
    assert done.status_code == 200
    report = done.json()
    assert report["owner"] == "SKY"
    assert not report["network_probes_performed"]
    assert not report["vulnerabilities_verified"]
    assert not report["changes_made"]


def test_capabilities_do_not_overstate_smart_home_or_ble(client):
    data = client.get("/api/sky/device-hub/capabilities", headers=auth()).json()
    assert data["owner"] == "SKY CORE"
    assert data["modes"]["infrared"]["requires_physical_emitter_or_bridge"]
    assert not data["modes"]["infrared"]["direct_ir_emitter_implemented"]
    assert not data["modes"]["matter"]["commissioning_implemented_in_sky"]
    assert data["no_auto_commands"] and data["no_auto_pairing"]



def test_ir_tv_command_is_approved_one_use_and_reports_sent_not_verified(client, monkeypatch):
    from neural_core import sky_home_assistant as ha
    from neural_core import sky_secure_connectivity as hub
    device = client.post("/api/sky/device-hub/devices", headers=auth(),
                         json=payload("home_assistant", "infrared",
                                      name="TV principal", device_type="television")).json()
    ident = device["id"]
    monkeypatch.setattr(ha, "configurado", lambda: True)
    actions = []
    def fake_home(method, route, body=None, timeout=6):
        actions.append((method, route, body))
        if method == "GET":
            return {"entity_id": "remote.sala", "state": "on"}
        assert method == "POST"
        return [{"entity_id": "remote.sala", "state": "on"}]
    monkeypatch.setattr(ha, "_peticion", fake_home)

    data = {"hub_id": ident, "command": "volume_up"}
    assert client.post("/api/sky/device-hub/ir/prepare", json=data).status_code == 401
    proposal = client.post("/api/sky/device-hub/ir/prepare", headers=auth(), json=data)
    assert proposal.status_code == 200, proposal.text
    info = proposal.json()
    assert info["status"] == "NEEDS_CONFIRMATION"
    assert info["target_name"] == "TV principal"
    approval = info["approval_token"]
    denied = client.post("/api/sky/device-hub/ir/execute", headers=auth(),
                         json={**data, "command":"mute", "approval_token": approval})
    assert denied.status_code == 403
    assert actions == []
    sent = client.post("/api/sky/device-hub/ir/execute", headers=auth(),
                       json={**data, "approval_token": approval})
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "SENT"
    assert sent.json()["verified"] is False
    assert actions == [
        ("GET", "/api/states/remote.sala", None),
        ("POST", "/api/services/remote/send_command",
         {"entity_id":"remote.sala", "device":"television", "command":"volume_up"})
    ]
    assert client.post("/api/sky/device-hub/ir/execute",headers=auth(),
                       json={**data, "approval_token":approval}).status_code == 403
    assert len(actions) == 2


def test_ir_adapter_does_not_accept_unapproved_targets_or_arbitrary_codes(client):
    non_tv = client.post("/api/sky/device-hub/devices",headers=auth(),
                         json=payload("home_assistant","infrared",name="Puente IR")).json()
    assert client.post("/api/sky/device-hub/ir/prepare",headers=auth(),
                       json={"hub_id":non_tv["id"],"command":"power"}).status_code == 403
    tv = client.post("/api/sky/device-hub/devices",headers=auth(),json=payload(
        "home_assistant","infrared",name="TV privada",device_type="television"
    )).json()
    assert client.post("/api/sky/device-hub/ir/prepare",headers=auth(),
                       json={"hub_id":tv["id"],"command":"factory_reset"}).status_code == 422
