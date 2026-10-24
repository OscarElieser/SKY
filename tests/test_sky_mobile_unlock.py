"""SKY Mobile Unlock regression: authorized, read-only USB carrier diagnosis."""
import pytest
from fastapi.testclient import TestClient

KEY = "sky-mobile-unlock-owner-key-for-tests-2026"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SKY_API_KEY", KEY)
    monkeypatch.setenv("SKY_WORKFLOWS_ENABLED", "0")
    from metaverse.api import app
    with TestClient(app) as c:
        yield c


def headers():
    return {"X-SKY-KEY": KEY}


def test_owner_auth_required_and_consent(client):
    assert client.get("/api/sky/mobile-unlock/capabilities").status_code == 401
    assert client.post("/api/sky/mobile-unlock/diagnose-usb",
                       json={"owner_attested": True}).status_code == 401
    assert client.post("/api/sky/mobile-unlock/diagnose-usb",
                       headers=headers(), json={"owner_attested": False}).status_code == 403
    assert client.post("/api/sky/mobile-unlock/plan", headers=headers(),
                       json={"source_carrier":"ATT", "target_carrier":"TIGO_NI"}).status_code == 403


def test_android_usb_diagnosis_is_read_only(monkeypatch):
    from neural_core import sky_mobile_unlock as mobile
    monkeypatch.setattr(mobile, "_adb_binary", lambda: "/local/tools/adb")
    commands = []
    output = {
        "ro.product.manufacturer": "samsung\n",
        "ro.product.model": "Galaxy S22\n",
        "ro.build.version.release": "15\n",
        "ro.product.device": "r0q\n",
        "gsm.sim.state": "READY\n",
    }
    def fake_run(command, *, timeout=7):
        commands.append(command)
        if command[-1] == "devices":
            return "List of devices attached\nABC123\tdevice\n"
        return output[command[-1]]
    monkeypatch.setattr(mobile, "_run_readonly", fake_run)
    result = mobile.diagnose_usb(owner_attested=True)
    assert result["ok"] is True
    assert result["device"]["model"] == "Galaxy S22"
    assert result["carrier_lock_state"] == "unknown"
    assert result["carrier_lock_verified"] is False
    assert result["changes_made"] is False
    assert result["unlock_performed"] is False
    assert "ABC123" not in str(result)
    assert all(cmd[:4] == ["/local/tools/adb", "-s", "ABC123", "shell"]
               and cmd[4] == "getprop" and cmd[5] in mobile._PROPS.values()
               for cmd in commands[1:])
    assert commands[0] == ["/local/tools/adb", "devices"]


@pytest.mark.parametrize("devices,status", [
    ("List of devices attached\n", "one_device_required"),
    ("List of devices attached\nAAAA\tdevice\nBBBB\tdevice\n", "one_device_required"),
    ("List of devices attached\nAAAA\tunauthorized\n", "adb_unauthorized"),
    ("List of devices attached\nAAAA\toffline\n", "adb_offline"),
])
def test_usb_requires_one_authorized_device(monkeypatch, devices, status):
    from neural_core import sky_mobile_unlock as mobile
    monkeypatch.setattr(mobile, "_adb_binary", lambda: "adb")
    monkeypatch.setattr(mobile, "_run_readonly", lambda *args, **kw: devices)
    result=mobile.diagnose_usb(owner_attested=True)
    assert result["status"]==status
    assert result["unlock_performed"] is False


def test_plan_for_tigo_nicaragua_with_official_att_requirements(client):
    result = client.post("/api/sky/mobile-unlock/plan", headers=headers(), json={
        "owner_attested": True,
        "source_carrier": "ATT", "target_carrier": "TIGO_NI",
        "os_family": "iphone", "observed_state": "sim_not_supported",
    })
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["destination"] == "Tigo Nicaragua"
    assert data["official_unlock_url"] == "https://www.att.com/deviceunlock/"
    assert not data["unlock_performed"]
    assert data["needs_original_carrier"]
    assert not data["usb_diagnostics_can_unlock"]
    assert not data["can_bypass_activation_or_pin"]
    assert not data["imei_rewrite_supported"]


def test_unknown_provider_does_not_claim_unlock(client):
    result = client.post("/api/sky/mobile-unlock/plan", headers=headers(), json={
        "owner_attested": True, "source_carrier": "UNKNOWN",
        "target_carrier": "CLARO_NI",
    })
    assert result.status_code == 200, result.text
    assert result.json()["official_unlock_url"] is None
    assert result.json()["carrier_unlock_verified"] is False


def test_catalogue_never_claims_carrier_unlock_or_other_bypasses(client):
    response=client.get("/api/sky/mobile-unlock/capabilities", headers=headers())
    assert response.status_code == 200
    data=response.json()
    assert data["android_usb_readonly"]
    assert data["actual_network_unlock_implemented"] is False
    assert data["carrier_lock_readable_via_adb"] is False
    assert data["no_bypass_pin_frp_icloud_blacklist"] is True
    assert data["no_imei_access"] is True


def test_readonly_subprocess_never_uses_shell(monkeypatch):
    from neural_core import sky_mobile_unlock as mobile
    commands=[]
    class Result:
        returncode=0
        stdout="test\n"
        stderr=""
    def fake_run(command, **kwargs):
        commands.append((command,kwargs))
        return Result()
    monkeypatch.setattr(mobile.subprocess, "run", fake_run)
    assert mobile._run_readonly(["adb", "devices"])=="test\n"
    assert commands[0][1]["shell"] is False
    assert commands[0][1]["timeout"] == 7
    assert commands[0][1]["stdin"] is mobile.subprocess.DEVNULL
