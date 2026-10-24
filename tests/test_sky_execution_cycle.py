"""Regression suite: SKY operational cycle and installable mobile shell, offline."""
from __future__ import annotations
from pathlib import Path
import json
import pytest
from neural_core import sky_execution_cycle as cycle


@pytest.fixture(autouse=True)
def fresh_cycle(monkeypatch):
    cycle._PLANS.clear()
    monkeypatch.setattr(cycle.caps, "parada_activa", lambda: None)
    yield
    cycle._PLANS.clear()


def create(*actions):
    return cycle.create([{"action": a, "params": p} for a, p in actions])


def test_owner_requires_confirmation_before_device_actions():
    plan = create(("status", {}))
    invoked = []
    def invoke(action, params, device):
        invoked.append(action)
        return {"ok": True, "status": "VERIFIED"}
    with pytest.raises(cycle.CycleInvalid):
        cycle.execute_next(plan["id"], invoke, approved=False)
    assert invoked == []
    done = cycle.execute_next(plan["id"], invoke, approved=True)
    assert done["state"] == "VERIFIED"
    assert done["complete_verified"] is True
    assert invoked == ["status"]


def test_next_action_waits_until_previous_physically_verified():
    plan = create(("launch_app", {"app": "word"}), ("status", {}))
    seen = []
    def invoke(action, params, device):
        seen.append(action)
        return {"ok": True, "status": "RUNNING", "command_id": "cmd_1234567890_abcd12"}
    first = cycle.execute_next(plan["id"], invoke, approved=True)
    assert first["state"] == "WAITING_VERIFICATION"
    assert first["verified"] == 0 and first["dispatched_unverified"] == 1
    assert seen == ["launch_app"]
    with pytest.raises(cycle.CycleConflict):
        cycle.execute_next(plan["id"], invoke, approved=True)
    assert seen == ["launch_app"]


def test_reconcile_only_matching_agent_ledger_record():
    plan = create(("launch_app", {"app": "word"}), ("status", {}))
    cid = "cmd_1234567890_abcd12"
    cycle.execute_next(plan["id"], lambda a,p,d: {"ok":True,"status":"RUNNING","command_id":cid}, approved=True)
    with pytest.raises(cycle.CycleConflict):
        cycle.reconcile(plan["id"], lambda c,d: {"record":{"command_id":"cmd_1234567890_999999","status":"VERIFIED"}})
    assert cycle.snapshot(plan["id"])["state"] == "WAITING_VERIFICATION"
    answer = cycle.reconcile(plan["id"], lambda c,d: {"record":{"command_id":cid,"status":"VERIFIED"}})
    assert answer["cursor"] == 1 and answer["state"] == "READY" and answer["verified"] == 1
    completed = cycle.execute_next(plan["id"], lambda a,p,d: {"ok":True,"status":"VERIFIED"}, approved=True)
    assert completed["state"] == "VERIFIED" and completed["verified"] == 2


def test_sent_does_not_mean_verified():
    plan = create(("media_key", {"key":"play_pause"}))
    r = cycle.execute_next(plan["id"], lambda a,p,d: {"ok":True,"status":"SENT"}, approved=True)
    assert not r["complete_verified"] and r["state"] == "WAITING_VERIFICATION"
    with pytest.raises(cycle.CycleConflict):
        cycle.reconcile(plan["id"], lambda a,d: {"ok":True,"record":{"status":"VERIFIED"}})


def test_failed_action_stops_next_step():
    p=create(("status", {}),("status", {}))
    r=cycle.execute_next(p["id"],lambda a,b,c:{"ok":False,"status":"FAILED"}, approved=True)
    assert r["state"] == "FAILED" and r["cursor"] == 0
    with pytest.raises(cycle.CycleConflict):
        cycle.execute_next(p["id"],lambda a,b,c:{"ok":True,"status":"VERIFIED"},approved=True)


def test_high_risk_action_requires_pin(monkeypatch):
    monkeypatch.setattr(cycle.caps,"nivel_riesgo",lambda a,p:3)
    p=create(("status", {}))
    called=[]
    with pytest.raises(cycle.CycleConflict):
        cycle.execute_next(p["id"],lambda a,b,c:called.append(a),approved=True)
    assert called==[] and cycle.snapshot(p["id"])["state"]=="READY"
    r=cycle.execute_next(p["id"],lambda a,b,c:{"ok":True,"status":"VERIFIED"},
                         approved=True,pin_check=lambda:called.append("pin"))
    assert r["complete_verified"] and called==["pin"]


def test_emergency_stop_halts_plan(monkeypatch):
    p=create(("status", {}))
    monkeypatch.setattr(cycle.caps,"parada_activa",lambda:{"activo":True})
    with pytest.raises(cycle.CycleConflict):
        cycle.execute_next(p["id"],lambda a,b,c:pytest.fail("Must not execute"),approved=True)
    assert cycle.snapshot(p["id"])["state"]=="READY"


def test_cannot_run_arbitrary_shell_commands_or_massive_plans():
    with pytest.raises(cycle.CycleInvalid):
        create(("run_shell",{"cmd":"rm -rf /"}))
    with pytest.raises(cycle.CycleInvalid):
        cycle.create([{"action":"status","params":{}}]*7)
    with pytest.raises(cycle.CycleInvalid):
        create(("type_text", {"text":"x"*2001}))


def test_cancel_and_no_reexecution():
    p=create(("status",{}))
    out=cycle.cancel(p["id"])
    assert out["state"]=="CANCELLED"
    with pytest.raises(cycle.CycleConflict):
        cycle.execute_next(p["id"],lambda a,b,c:pytest.fail("no"),approved=True)


def test_sequence_detector_is_explicit_and_parser_reuses_existing_interpreter(monkeypatch):
    assert cycle.is_sequence("SKY, abre Word y luego abre Excel")
    assert not cycle.is_sequence("¿Qué sucede después de la clase?")
    assert not cycle.is_sequence("Abre Word")
    def interpret(text):
        text=text.lower()
        if "word" in text:
            return {"action":"launch_app","params":{"app":"word"},"description":"Abrir Word"}
        if "excel" in text:
            return {"action":"launch_app","params":{"app":"excel"},"description":"Abrir Excel"}
        return None
    monkeypatch.setattr(cycle.assistant,"interpretar",interpret)
    steps=cycle.from_text("SKY, abre Word y luego abre Excel")
    assert [x["params"]["app"] for x in steps]==["word","excel"]
    with pytest.raises(cycle.CycleInvalid):
        cycle.from_text("abre Word y luego destruye Windows")


def test_plan_expires_without_fake_completion(monkeypatch):
    p=create(("status",{}))
    cycle._PLANS[p["id"]]["updated_monotonic"] -= cycle._TTL_SECONDS + 1
    with pytest.raises(cycle.CycleConflict):
        cycle.snapshot(p["id"])


def test_installable_shell_is_present_but_does_not_cache_private_data():
    static=Path("metaverse/static")
    for icon in ["sky-icon-192.png","sky-icon-512.png"]:
        raw=(static/icon).read_bytes()
        assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    html=(static/"hud.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in html and "sky-pwa-install.js" in html
    sw=(static/"sky-sw.js").read_text(encoding="utf-8")
    assert "startsWith('/api/')" in sw and "request.method !== 'GET'" in sw
    assert "event.respondWith" in sw and "CACHE_NAME" in sw
    api=Path("metaverse/api.py").read_text(encoding="utf-8")
    assert "app.include_router(mobile_pwa_router)" in api


def test_existing_api_and_voice_route_remain_connected():
    source=Path("metaverse/asistente_api.py").read_text(encoding="utf-8")
    assert "ciclo.is_sequence(body.texto)" in source
    assert "return _medir_turno(_completar(resultado" in source
    assert "dispositivos.verify_device_action" in source
    hud=Path("metaverse/static/hud.js").read_text(encoding="utf-8")
    assert "data.tipo === 'ciclo'" in hud and "S.pending" in hud


def test_agent_marks_dispatched_separately_from_verified():
    a=Path("agente_dispositivo.py").read_text(encoding="utf-8")
    assert "verificador_acciones.mark_dispatched" in a
    win=Path("neural_core/windows_controller.py").read_text(encoding="utf-8")
    assert win.count("verificador_acciones.mark_dispatched(rec.command_id, result") >= 2
