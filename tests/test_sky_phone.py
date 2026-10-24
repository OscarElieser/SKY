"""SKY Teléfono: isolated, provider-mocked security tests.

Offline tests are NOT carrier delivery tests, actual calls, or browser camera
tests. Charges and side-effects must never happen in CI.
"""
import json
from pathlib import Path
import pytest

from neural_core import sky_phone as phone


@pytest.fixture(autouse=True)
def safe_phone(monkeypatch,tmp_path):
    monkeypatch.setattr(phone,"STORE",tmp_path/"sky_phone_test.json")
    monkeypatch.setenv("SKY_PHONE_ENABLED","1")
    monkeypatch.setenv("SKY_PHONE_ALLOW_VERIFY","1")
    monkeypatch.setenv("SKY_PHONE_ALLOW_PAID","1")
    monkeypatch.setenv("SKY_PHONE_ALLOWED_PREFIXES","505")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID","AC"+"a"*32)
    monkeypatch.setenv("TWILIO_AUTH_TOKEN","SECRET_"+"b"*40)
    monkeypatch.setenv("TWILIO_VERIFY_SERVICE_SID","VA"+"c"*32)
    monkeypatch.setenv("TWILIO_PHONE_NUMBER","+15005550006")
    monkeypatch.delenv("SKY_LOCAL_ONLY",raising=False)


def _verified():
    x=phone._load()
    x["verified_phone"]="+50588887777"
    x["verified_at"]="2026-10-24T00:00:00Z"
    phone._save(x)


def test_e164_is_explicit_and_carrier_agnostic():
    assert phone.normalize("+505 8888-7777")=="+50588887777"
    for bad in ("88887777","+0000111122","abc","+505","0012345678","+50588887777;drop"):
        with pytest.raises(phone.PhoneInvalid):
            phone.normalize(bad)
    assert phone._country_permission("+50588887777")
    with pytest.raises(phone.PhoneInvalid):
        phone._country_permission("+14155552671")


def test_verified_owner_requires_real_provider_approval(monkeypatch):
    captured=[]
    def mock_provider(host,path,fields,sid,token):
        captured.append((host,path,dict(fields)))
        return {"status":"pending"} if path.endswith("/Verifications") else {"status":"approved"}
    monkeypatch.setattr(phone,"_post",mock_provider)
    with pytest.raises(phone.PhoneInvalid):
        phone.begin_verify("+50588887777",approved=False)
    r=phone.begin_verify("+50588887777",approved=True)
    assert not r["verified"] and phone.readiness()["owner_phone_verified"] is False
    with pytest.raises(phone.PhoneInvalid):
        phone.finish_verify("+50588887777","oops")
    result=phone.finish_verify("+50588887777","123456")
    assert result["verified"] and phone.readiness()["owner_phone_verified"]
    assert r["phone_masked"]=="••••7777"
    text=json.dumps(phone._load())
    assert "123456" not in text and "SECRET_" not in text
    assert captured[0][0]=="verify.twilio.com"
    assert captured[1][2]["Code"]=="123456"


def test_verification_rejected_does_not_register_number(monkeypatch):
    monkeypatch.setattr(phone,"_post",lambda *a,**k:
                        {"status":"pending"} if a[1].endswith("/Verifications")
                        else {"status":"failed"})
    phone.begin_verify("+50588887777",approved=True)
    result=phone.finish_verify("+50588887777","123456")
    assert result["verified"] is False and not phone.readiness()["owner_phone_verified"]


def test_block_and_unblock_are_only_in_sky_and_privately_masked():
    _verified()
    with pytest.raises(phone.PhoneInvalid):
        phone.set_block("+50577776666",blocked=True,approved=False)
    x=phone.set_block("+50577776666",blocked=True,approved=True)
    assert x["scope"]=="sky_only"
    assert phone.blocked_list()["total"]==1
    assert "+50577776666" not in json.dumps(phone.blocked_list())
    blocked_id=phone.blocked_list()["numbers"][0]["id"]
    with pytest.raises(phone.PhoneInvalid):
        phone.set_block("+50588887777",blocked=True,approved=True)
    with pytest.raises(phone.PhoneInvalid):
        phone.unblock_by_id(blocked_id,approved=False)
    assert not phone.unblock_by_id(blocked_id,approved=True)["blocked"]


def test_no_sms_without_permission_and_verified_owner(monkeypatch):
    called=[]
    monkeypatch.setattr(phone,"_post",lambda *a,**k:called.append(1) or {"sid":"SM"+"a"*32})
    with pytest.raises(phone.PhoneInvalid):
        phone.send_sms("+50577776666","hola",approved=False,recipient_consented=True)
    with pytest.raises(phone.PhoneInvalid):
        phone.send_sms("+50577776666","hola",approved=True,recipient_consented=True)
    _verified()
    with pytest.raises(phone.PhoneInvalid):
        phone.send_sms("+50577776666","hola",approved=True,recipient_consented=False)
    assert not called


def test_sms_response_is_queued_not_fake_delivery(monkeypatch):
    _verified()
    fields=[]
    monkeypatch.setattr(phone,"_post",lambda host,path,params,*a:
                        fields.append((host,path,params)) or {"sid":"SM"+"a"*32,
                                                              "status":"queued"})
    out=phone.send_sms("+50577776666","Hola desde SKY",approved=True,recipient_consented=True)
    assert out["status"]=="queued_unverified"
    assert out["delivered_to_phone_verified"] is False
    assert fields[0][0]=="api.twilio.com"
    assert fields[0][2]["To"]=="+50577776666"
    assert fields[0][2]["Body"]=="Hola desde SKY"
    assert "Hola desde SKY" not in json.dumps(phone._load())
    for _ in range(9):
        phone.send_sms("+50577776666","Hola",approved=True,recipient_consented=True)
    with pytest.raises(phone.PhoneUnavailable):
        phone.send_sms("+50577776666","Hola",approved=True,recipient_consented=True)


def test_block_prevents_sms_and_calls_without_provider_dispatch(monkeypatch):
    _verified()
    phone.set_block("+50577776666",blocked=True,approved=True)
    called=[]
    monkeypatch.setattr(phone,"_post",lambda *a,**k:called.append(1))
    with pytest.raises(phone.PhoneInvalid):
        phone.send_sms("+50577776666","Hola",approved=True,recipient_consented=True)
    with pytest.raises(phone.PhoneInvalid):
        phone.call_bridge("+50577776666",approved=True,recipient_consented=True)
    assert not called


def test_real_callback_spec_calls_owner_first_two_leg_no_recording(monkeypatch):
    _verified()
    captured=[]
    monkeypatch.setattr(phone,"_post",lambda host,path,form,*a:
                        captured.append((path,form)) or {"sid":"CA"+"a"*32,
                                                         "status":"queued"})
    r=phone.call_bridge("+50577776666",approved=True,recipient_consented=True)
    assert r["mode"]=="callback_to_verified_handset"
    assert r["call_completed"] is False and not r["browser_microphone_call"]
    form=captured[0][1]
    assert form["To"]=="+50588887777" and form["From"]=="+15005550006"
    assert "<Number>+50577776666</Number>" in form["Twiml"]
    assert 'record="do-not-record"' in form["Twiml"]
    assert form["Record"]=="false"
    assert "CA"+"a"*32 == r["call_sid"]


def test_video_room_is_private_random_and_not_joined(monkeypatch):
    with pytest.raises(phone.PhoneInvalid):
        phone.meeting(approved=True)
    _verified()
    with pytest.raises(phone.PhoneInvalid):
        phone.meeting(approved=False)
    a=phone.meeting(approved=True)
    b=phone.meeting(approved=True)
    assert a["meeting_url"].startswith("https://meet.jit.si/SKY-")
    assert a["meeting_url"]!=b["meeting_url"]
    assert not a["room_server_verified"]
    assert a["status"]=="invitation_ready_not_joined"
    assert a["native_cellular_video_call"] is False
    monkeypatch.setenv("SKY_VIDEO_CONFERENCE_HOST","evil.example")
    with pytest.raises(phone.PhoneInvalid):
        phone.meeting(approved=True)


def test_local_only_and_opt_in_guard_both_paid_channels(monkeypatch):
    _verified()
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    with pytest.raises(phone.PhoneUnavailable):phone.meeting(approved=True)
    with pytest.raises(phone.PhoneUnavailable):phone.call_bridge("+50577776666",approved=True,recipient_consented=True)
    monkeypatch.delenv("SKY_LOCAL_ONLY",raising=False)
    monkeypatch.setenv("SKY_PHONE_ALLOW_PAID","0")
    with pytest.raises(phone.PhoneUnavailable):phone.send_sms("+50577776666","hola",approved=True,recipient_consented=True)


def test_custom_global_prefixes_require_explicit_config(monkeypatch):
    monkeypatch.setenv("SKY_PHONE_ALLOWED_PREFIXES","505,1,34,52")
    assert phone._country_permission("+14155552671")
    assert phone._country_permission("+34911112222")
    assert phone._country_permission("+525512345678")
    with pytest.raises(phone.PhoneInvalid):phone._country_permission("+447700900123")
    monkeypatch.setenv("SKY_PHONE_ALLOWED_PREFIXES","*,505")
    with pytest.raises(phone.PhoneInvalid):phone._country_permission("+50588887777")


def test_existing_private_api_and_hud_are_extended_not_replaced():
    api=Path("metaverse/api.py").read_text(encoding="utf-8")
    assert "app.include_router(sky_phone_router)" in api
    phone_api=Path("metaverse/phone_api.py").read_text(encoding="utf-8")
    assert 'prefix="/api/sky/phone"' in phone_api
    assert "dependencies=[Depends(require_key)]" in phone_api
    assert 'exigir_pin(request,purpose)' in phone_api
    hud=Path("metaverse/static/hud.js").read_text(encoding="utf-8")
    assert "t: 'Teléfono'" in hud
    assert "function abrirTelefono()" in hud
    assert "JitsiMeetExternalAPI" in hud
    assert "recipient_consented:true" in hud
    assert "SKY Aula existente" in hud
    assert "abrirAula()" in hud
