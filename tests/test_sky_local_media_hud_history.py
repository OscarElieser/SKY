"""SKY ComfyUI/LM Studio/HUD history: offline contracts and preservation tests."""
import json
import uuid
import pytest
from neural_core import sky_comfyui_local as comfy
from neural_core import sky_lmstudio as lm
from neural_core import sky_hud_history as history
from neural_core import sky_runtime_inventory as inventory


@pytest.fixture(autouse=True)
def sandbox(tmp_path,monkeypatch):
    monkeypatch.setenv("SKY_COMFYUI_DB",str(tmp_path/"media.sqlite3"))
    monkeypatch.setenv("SKY_HUD_HISTORY_DB",str(tmp_path/"conversations.sqlite3"))
    monkeypatch.setenv("SKY_COMFYUI_ENABLED","1")
    monkeypatch.setenv("SKY_COMFYUI_PORT","8188")
    monkeypatch.setenv("SKY_LMSTUDIO_ENABLED","1")
    monkeypatch.setenv("SKY_LMSTUDIO_MODEL","local-test")


def test_history_is_persistent_paginated_and_searchable():
    for i in range(125):
        history.append("user","Pregunta real "+str(i),"voz" if i%2 else "chat")
    assert history.count()==125
    first=history.list_entries(50)
    assert len(first["entries"])==50 and first["has_more"]
    second=history.list_entries(50,before=first["next_before"])
    third=history.list_entries(50,before=second["next_before"])
    assert len(second["entries"])==50 and len(third["entries"])==25
    assert not third["has_more"]
    assert len({a["id"] for page in (first,second,third) for a in page["entries"]})==125
    assert len(history.list_entries(10,query="Pregunta real 12")["entries"])>=2


def test_history_guard_limits():
    with pytest.raises(ValueError):
        history.append("system","Permisos internos secretos")
    with pytest.raises(ValueError):
        history.append("user","x"*4001)
    with pytest.raises(ValueError):
        history.list_entries(201)
    with pytest.raises(ValueError):
        history.list_entries(3,before=-1)


def _prepare_workflow(tmp_path,monkeypatch,kind="image"):
    path=tmp_path/("sky_"+kind+".json")
    data={"6":{"class_type":"CLIPTextEncode","inputs":{"text":"ORIGINAL"}},
          "2":{"class_type":"KSampler","inputs":{"seed":42}}}
    path.write_text(json.dumps(data))
    monkeypatch.setenv("SKY_COMFYUI_WORKFLOW_"+kind.upper(),str(path))
    monkeypatch.setenv("SKY_COMFYUI_PROMPT_NODE_"+kind.upper(),"6")
    return path


def test_workflow_only_changes_prompt_node(tmp_path,monkeypatch):
    path=_prepare_workflow(tmp_path,monkeypatch)
    graph=comfy._workflow("image","Retrato cinematográfico de montaña y río")
    assert graph["6"]["inputs"]["text"]=="Retrato cinematográfico de montaña y río"
    assert graph["2"]["inputs"]["seed"]==42
    assert json.loads(path.read_text())["6"]["inputs"]["text"]=="ORIGINAL"


def test_workflow_rejects_unknown_or_unsafe_config(tmp_path,monkeypatch):
    _prepare_workflow(tmp_path,monkeypatch)
    monkeypatch.setenv("SKY_COMFYUI_PROMPT_NODE_IMAGE","2")
    with pytest.raises(comfy.LocalMediaUnavailable):
        comfy._workflow("image","Una descripción bastante larga")
    for value in ("0","abc","8188/../"):
        monkeypatch.setenv("SKY_COMFYUI_PORT",value)
        with pytest.raises(comfy.LocalMediaError):
            comfy.base_url()


def test_submit_comfyui_is_real_queued_workflow(tmp_path,monkeypatch):
    _prepare_workflow(tmp_path,monkeypatch)
    saved=[]
    uid=str(uuid.uuid4())
    def response(method,path,body=None):
        saved.append((method,path,body))
        return {"prompt_id":uid}
    monkeypatch.setattr(comfy,"_json",response)
    queued=comfy.submit("image","Create original comic-style mountain landscape")
    assert queued["status"]=="queued"
    assert queued["image_or_video_generated"] is False
    assert saved[0][1]=="/prompt"
    assert saved[0][2]["prompt"]["6"]["inputs"]["text"].startswith("Create")


def test_comfy_status_imports_only_real_verified_output(tmp_path,monkeypatch):
    _prepare_workflow(tmp_path,monkeypatch)
    uid=str(uuid.uuid4())
    monkeypatch.setattr(comfy,"_json",lambda method,path,body=None:
        {"prompt_id":uid} if method=="POST" else {
            uid:{"status":{"status_str":"success"},"outputs":{
                "9":{"images":[{"filename":"real.png","subfolder":"","type":"output"}]}}}
        })
    queued=comfy.submit("image","Original picture from my own local model")
    monkeypatch.setattr(comfy,"_call",lambda *args,**kwargs:(b"verified-png-bytes","image/png"))
    import sys
    from types import ModuleType
    module=ModuleType("neural_core.sky_creative")
    files=[]
    module.ingest=lambda data,filename:(files.append((data,filename)) or {"id":"asset_real"})
    monkeypatch.setitem(sys.modules,"neural_core.sky_creative",module)
    result=comfy.status(queued["job_id"])
    assert result["status"]=="completed" and result["asset_id"]=="asset_real"
    assert files==[(b"verified-png-bytes","real.png")]
    assert comfy.status(queued["job_id"])["status"]=="completed"


def test_local_status_never_uses_arbitrary_comfy_path():
    assert comfy._output({"1":{"images":[{"filename":"../secrets.png","type":"output"}]}},"image") is None
    assert comfy._output({"1":{"gifs":[{"filename":"good.mp4","type":"temp"}]}},"video") is None
    assert comfy._output({"1":{"gifs":[{"filename":"good.mp4","type":"output"}]}},"video")["filename"]=="good.mp4"


def test_lmstudio_generates_only_with_local_endpoint(monkeypatch):
    events=[]
    monkeypatch.setattr(lm,"_request",lambda method,endpoint,payload=None:
                        (events.append((method,endpoint,payload)) or {
                            "choices":[{"message":{"content":"Respuesta real del modelo local SKY"}}]}))
    text=lm.chat([{"role":"system","content":"Sos SKY"},
                  {"role":"user","content":"Explicá la lección"}],"local-test")
    assert text.startswith("Respuesta real")
    assert events[0][1]=="/v1/chat/completions"
    assert events[0][2]["messages"][0]["role"]=="system"


def test_lmstudio_local_policy(monkeypatch):
    from neural_core import providers
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    assert providers.choose_provider("lmstudio")[0]=="lmstudio"
    with pytest.raises(providers.ProviderError):
        providers.choose_provider("gemini")
    monkeypatch.setenv("SKY_LMSTUDIO_ENABLED","0")
    assert not lm.configured()


def test_inventory_does_not_claim_optional_agents_installed():
    result=inventory.report()
    assert result["controller"]=="SKY"
    assert result["modules"]["crewai"]["exists_in_repo"] is False
    assert result["modules"]["n8n"]["exists_in_repo"] is True
    assert result["modules"]["make"]["exists_in_repo"] is False
    assert result["modules"]["comfyui"]["configured"] is True
    assert "installed_here" in result["packages"]["pyautogui"]
