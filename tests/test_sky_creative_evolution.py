"""Tests: SKY Creative Evolution (modelos y servicios externos simulados)."""
import io
import json
import wave
import pytest
from neural_core import sky_creative_evolution as c

@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SKY_CREATIVE_EVOLUTION_DB",str(tmp_path/"writing.db"))
    monkeypatch.setenv("SKY_LOCAL_ONLY","0")

@pytest.mark.parametrize("code",["es","en","fr","pt","it","ko","zh","ja","de",
                                  "es-NI","pt-BR","zh-CN"])
def test_languages(code):
    root,name=c.language(code)
    assert name==c.LANGUAGES[root]

def test_unsupported_language():
    with pytest.raises((c.CreativeInvalid,ValueError)):
        c.language("zz")
    with pytest.raises((c.CreativeInvalid,ValueError)):
        c.language("de@server")

def test_create_and_revise_writing_with_history(monkeypatch):
    prompts=[]
    def fake(system,prompt,provider,max_tokens):
        prompts.append(system)
        return "Una historia narrativa original extensa con desarrollo, personajes y desenlace.", "ollama"
    monkeypatch.setattr(c,"_ask",fake)
    work=c.create_writing("cuento","Lago brillante",
        "Una niña descubre el origen de la luz del lago y ayuda a su comunidad",
        "ko","fantasia")
    assert work["version"]==1 and work["locale"]=="ko"
    assert "한국어" in prompts[0]
    revised=c.revise_writing(work["id"],"Incluí un diálogo con sus amigos",1)
    assert revised["version"]==2
    assert [x["version"] for x in c.versions(work["id"])]==[2,1]
    with pytest.raises(c.CreativeInvalid):
        c.revise_writing(work["id"],"Revisa el final narrativo",1)
    assert c.get_work("skywork_nope") is None

@pytest.mark.parametrize("kind",list(c.KINDS))
def test_writing_modes(monkeypatch,kind):
    monkeypatch.setattr(c,"_ask",lambda *a:
        ("Texto creativo suficientemente extenso con personajes y una estructura original.","ollama"))
    result=c.create_writing(kind,"Obra de SKY",
        "Una aventura de exploradores que descubren nuevas experiencias")
    assert result["kind"]==kind

def test_image_prompt_and_local_privacy(monkeypatch):
    monkeypatch.setattr(c,"_ask",lambda *a:("Cinematic forest with blue lighting","ollama"))
    data=c.improve_visual_prompt("Paisaje de montaña misteriosa",locale="ja")
    assert data["provider"]=="ollama" and "Cinematic" in data["enhanced"]
    monkeypatch.setenv("SKY_LOCAL_ONLY","1")
    with pytest.raises(c.CreativeUnavailable):
        c.generate_image("Un bosque iluminado en la noche")

def test_music_wav_is_real_repeatable():
    a=c.music_wav("ambient","calm",8,100,"océano")
    b=c.music_wav("ambient","calm",8,100,"océano")
    d=c.music_wav("pop","happy",8,100,"océano")
    assert a==b and a!=d and a.startswith(b"RIFF")
    with wave.open(io.BytesIO(a),"rb") as stream:
        assert stream.getframerate()==22050
        assert stream.getnchannels()==1
        assert stream.getsampwidth()==2
        assert stream.getnframes()==8*22050

@pytest.mark.parametrize("bad",[{"genre":"inexistente"},{"mood":"nulo"},
                                 {"seconds":31},{"seconds":True},
                                 {"bpm":0},{"bpm":200}])
def test_invalid_music(bad):
    with pytest.raises(c.CreativeInvalid):
        c.music_wav(**bad)

def test_storyboard_is_strict():
    data=json.dumps({"shots":[
        {"visual":"Una ciudad antigua al amanecer bajo cielo brillante","caption":"El inicio"},
        {"visual":"Un bosque en las montañas cubierto de nubes suaves","caption":"El camino"}]})
    assert len(c._shots(data))==2
    assert len(c._shots(chr(96)*3+"json\n"+data+"\n"+chr(96)*3))==2
    with pytest.raises((ValueError,c.CreativeInvalid)):
        c._shots('{"shots":[]}')

def test_movie_uses_sky_assets_and_queue(monkeypatch):
    import sys
    from types import ModuleType
    from neural_core import gemini_provider, providers
    monkeypatch.setattr(providers,"local_only",lambda:False)
    images=[]
    def image(prompt):
        images.append(prompt)
        return b"PNG_MOCK","image/png"
    monkeypatch.setattr(gemini_provider,"generar_imagen",image)
    fake=ModuleType("neural_core.sky_creative")
    fake.ingest=lambda content,name:{"id":"asset_"+str(len(images))}
    checked=[]
    fake.validate_spec=lambda kind,spec:checked.append(spec)
    fake.create_project=lambda kind,name,spec:{"id":"skyvideo_1"}
    fake.queue_video=lambda ident:{"id":"job_1","status":"queued"}
    monkeypatch.setitem(sys.modules,"neural_core.sky_creative",fake)
    monkeypatch.setattr(c,"_ask",lambda *a:(json.dumps({"shots":[
        {"visual":"Vista cinematográfica de una ciudad al amanecer","caption":"Nuevo día"},
        {"visual":"Camino natural sobre montañas con árboles verdes","caption":"El viaje"}]}),"ollama"))
    out=c.movie_from_prompt("Aventura de SKY",
         "Dos personas descubren paisajes y construyen una historia maravillosa.")
    assert out["real_motion_generation"] is False
    assert out["ready_to_download"] is False
    assert out["job"]["status"]=="queued"
    assert len(images)==2 and len(checked[0]["clips"])==2

def test_capabilities_are_honest():
    result=c.capabilities()
    assert set(result["languages"])==set(c.LANGUAGES)
    assert result["video"]["real_motion_generation"] is False
    assert result["music"]["sung_vocals"] is False


def test_creative_voice_writing_nine_languages(monkeypatch):
    from neural_core import sky_creative_intent as intent
    request="SKY, redacta una novela en francés sobre un viaje por los mares y montañas de Nicaragua"
    info=intent.parse(request)
    assert info["kind"]=="novela" and info["locale"]=="fr"
    assert "Nicaragua" in info["topic"]
    assert intent.parse("SKY, abre Word") is None
    assert intent.parse("SKY, genera una imagen de mi familia") is None
    monkeypatch.setattr(c,"create_writing",lambda *a,**kw:
        {"text":"Un capítulo original","id":"skywork_abc","version":1,"locale":kw["locale"]})
    result=intent.handle(request)
    assert result["created"] is True
    assert result["creative_locale"]=="fr"
    assert result["generated_media"] is False


def test_music_voice_makes_a_real_asset_when_requested(monkeypatch):
    from neural_core import sky_creative_intent as intent
    assert intent.parse("SKY, crea música instrumental inspirada en Nicaragua")["action"]=="instrumental"
    monkeypatch.setattr(c,"save_music",lambda **kwargs:
        {"asset":{"id":"asset_real_audio"}})
    result=intent.handle("SKY, crea música instrumental inspirada en Nicaragua")
    assert result["creative_asset_id"]=="asset_real_audio"
    assert result["sung_vocals"] is False


def test_do_not_claim_creation_if_provider_fails(monkeypatch):
    from neural_core import sky_creative_intent as intent
    def unavailable(*args,**kwargs):
        raise RuntimeError("Private token secret")
    monkeypatch.setattr(c,"create_writing",unavailable)
    result=intent.handle("SKY, crea un cuento sobre una ciudad misteriosa y el amanecer")
    assert result["tipo"]=="error"
    assert "Private token" not in result["mensaje"]


@pytest.mark.parametrize("sample",[
    "你好世界欢迎来到天空智能助手",
    "こんにちは世界へようこそ物語を始めましょう",
    "안녕하세요 새로운 여행 이야기를 시작합니다"
])
def test_existing_creative_caption_accepts_cjk_text(sample):
    from neural_core import sky_creative as renderer
    image=renderer._caption_png(sample, 380)
    assert image.size[0]==380 and image.size[1]>60
    assert renderer._font(24,sample) is not None
