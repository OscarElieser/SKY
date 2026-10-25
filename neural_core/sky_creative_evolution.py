"""SKY Creative Evolution: narrativa multilingue, imagenes IA y multimedia real.
SKY conserva su API, providers, Creative Studio, Gemini y la cola FFmpeg.
Las peliculas son montajes de fotogramas IA; no video de movimiento generado.
La musica es instrumental algorítmica WAV, no un modelo de audio vocal.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import os
import random
import re
import sqlite3
import struct
import uuid
import wave
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

LANGUAGES = {
    "es": "español", "en": "English", "fr": "français",
    "pt": "português", "it": "italiano", "ko": "한국어",
    "zh": "中文", "ja": "日本語", "de": "Deutsch"
}
KINDS = {
    "cuento": "cuento completo con inicio, nudo y desenlace",
    "historia": "historia con personajes, conflictos y resolución",
    "novela": "sinopsis, personajes, estructura de capítulos y un primer capítulo",
    "guion": "guion audiovisual con escenas, acciones y diálogos",
    "pelicula": "tratamiento, secuencias, planos y guion de apertura",
    "cancion": "letra original con versos, estribillo y puente"
}
GENRES = ("aventura","fantasia","romance","drama","comedia","ciencia_ficcion",
          "misterio","educativo","documental","epico")
MUSIC_STYLES = ("cinematic","ambient","folk","electronic","pop")
MUSIC_MOODS = ("hopeful","calm","dramatic","happy","mysterious")
ROOT = Path(__file__).resolve().parents[1]


class CreativeInvalid(ValueError):
    pass


class CreativeUnavailable(RuntimeError):
    pass


def language(tag: str):
    from .sky_languages import normalize
    code = normalize(tag, strict=True).split("-")[0]
    if code not in LANGUAGES:
        raise CreativeInvalid("El estudio admite los nueve idiomas solicitados.")
    return code, LANGUAGES[code]


def _clean(value, title, limit, minimum=1):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= limit:
        raise CreativeInvalid(title + " inválido.")
    text = value.strip()
    if any(ord(c) < 32 and c not in "\n\t" for c in text):
        raise CreativeInvalid("Caracteres no permitidos.")
    return text


def _ask(system, prompt, provider="auto", max_tokens=2500):
    from .providers import choose_provider, reply
    name, model = choose_provider(provider, "escritura creativa")
    result = reply([{"role":"system","content":system},
                    {"role":"user","content":prompt}],
                   name, model, max_output_tokens=max_tokens)
    return _clean(result, "Respuesta de IA", 38000, 20), name


@contextmanager
def _db():
    path = Path(os.getenv("SKY_CREATIVE_EVOLUTION_DB") or
                ROOT / "local_data" / "sky_creative_evolution.sqlite3")
    path.parent.mkdir(parents=True,exist_ok=True)
    db = sqlite3.connect(path,timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript("""CREATE TABLE IF NOT EXISTS works(
        id TEXT PRIMARY KEY, kind TEXT NOT NULL,locale TEXT NOT NULL,
        title TEXT NOT NULL,premise TEXT NOT NULL,
        text TEXT NOT NULL,version INTEGER NOT NULL,
        provider TEXT NOT NULL,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS work_versions(
        id TEXT NOT NULL,version INTEGER NOT NULL,text TEXT NOT NULL,
        recorded TEXT NOT NULL,PRIMARY KEY(id,version));""")
    try:
        yield db
        if db.in_transaction:
            db.commit()
    except BaseException:
        if db.in_transaction:
            db.rollback()
        raise
    finally:
        db.close()


def get_work(ident):
    if not isinstance(ident,str) or not re.fullmatch(r"skywork_[0-9a-f]{32}",ident):
        return None
    with _db() as db:
        item=db.execute("SELECT * FROM works WHERE id=?",(ident,)).fetchone()
    return dict(item) if item else None


def list_works():
    with _db() as db:
        rows=db.execute("SELECT id,kind,locale,title,version,provider,created "
                        "FROM works ORDER BY created DESC LIMIT 60").fetchall()
    return [dict(x) for x in rows]


def versions(ident):
    if get_work(ident) is None:
        raise CreativeInvalid("Obra no encontrada.")
    with _db() as db:
        return [dict(x) for x in db.execute(
            "SELECT version,recorded FROM work_versions WHERE id=? ORDER BY version DESC",(ident,))]


def create_writing(kind,title,premise,locale="es",genre="aventura",provider="auto"):
    if kind not in KINDS or genre not in GENRES:
        raise CreativeInvalid("Tipo o género no permitido.")
    code,lang=language(locale)
    title=_clean(title,"Título",120,3)
    premise=_clean(premise,"Idea",2500,12)
    system=(f"Sos SKY, creadora literaria. Redactá en {lang}, género {genre}. "
            f"Entregá {KINDS[kind]}. Creá personajes, coherencia y evolución "
            "dramática originales. No reutilices letra ni textos de terceros. "
            "No redactés frases genéricas; respetá el tono, contexto y edad. "
            "Una novela larga no cabe en una respuesta: da su estructura y primer "
            "capítulo, sin fingir que escribiste el libro entero. No declares "
            "que generaste imágenes, audio ni una película reproducible.")
    body,engine=_ask(system,json.dumps({"title":title,"premise":premise},ensure_ascii=False),
                     provider,3100)
    ident="skywork_"+uuid.uuid4().hex
    now=datetime.now(timezone.utc).isoformat()
    with _db() as db:
        db.execute("INSERT INTO works VALUES (?,?,?,?,?,?,?,?,?)",
                   (ident,kind,code,title,premise,body,1,engine,now))
        db.execute("INSERT INTO work_versions VALUES(?,?,?,?)",(ident,1,body,now))
    return get_work(ident)


def revise_writing(ident,instruction,version,provider="auto"):
    instruction=_clean(instruction,"Edición",1000,8)
    if type(version) is not int or version < 1:
        raise CreativeInvalid("Versión inválida.")
    original=get_work(ident)
    if original is None or original["version"]!=version:
        raise CreativeInvalid("La obra no existe o su versión ya cambió.")
    body,engine=_ask(
        f"Sos SKY editora. Revisá el texto íntegro en {LANGUAGES[original['locale']]}. "
        "Respetá personajes, trama, continuidad y derechos de autor. "
        "Si el material es demasiado largo, informá revisión parcial.",
        json.dumps({"original":original["text"][:14000],"changes":instruction},ensure_ascii=False),
        provider,3400)
    now=datetime.now(timezone.utc).isoformat()
    with _db() as db:
        result=db.execute("UPDATE works SET text=?,version=version+1,provider=? "
                          "WHERE id=? AND version=?",(body,engine,ident,version))
        if result.rowcount!=1:
            raise CreativeInvalid("Conflicto de versiones.")
        db.execute("INSERT INTO work_versions VALUES(?,?,?,?)",(ident,version+1,body,now))
    return get_work(ident)


def continue_writing(ident,instruction,version,provider="auto"):
    """Extiende novelas y guiones con un capítulo o escena cada vez."""
    instruction=_clean(instruction,"Continuación",1000,8)
    if type(version) is not int or version < 1:
        raise CreativeInvalid("Versión inválida.")
    work=get_work(ident)
    if not work or work["version"]!=version:
        raise CreativeInvalid("La obra no existe o su versión ya cambió.")
    if work["kind"] not in ("novela","historia","guion","pelicula","cuento"):
        raise CreativeInvalid("Este tipo de obra no admite capítulos adicionales.")
    if len(work["text"]) > 24000:
        raise CreativeInvalid("Este volumen está completo; creá un volumen nuevo para continuar.")
    addition,engine=_ask(
        f"Sos SKY escritora y supervisora de continuidad. Escribí la siguiente parte de "
        f"la obra en {LANGUAGES[work['locale']]}. Respetá personajes, hechos, "
        "identidad, cronología y estilo. Generá material NUEVO, no repitas capítulos. "
        "Entregá SOLO la nueva escena o capítulo con un título propio. "
        "No copies material ajeno.",
        json.dumps({"title":work["title"],"previous":work["text"][-12500:],
                    "direction":instruction},ensure_ascii=False),provider,2700)
    combined=work["text"].rstrip()+"\n\n"+addition
    if len(combined)>38000:
        raise CreativeInvalid("Se alcanzó el límite de este volumen.")
    now=datetime.now(timezone.utc).isoformat()
    with _db() as db:
        result=db.execute("UPDATE works SET text=?,version=version+1,provider=? "
                          "WHERE id=? AND version=?",(combined,engine,ident,version))
        if result.rowcount!=1:
            raise CreativeInvalid("Conflicto de versiones.")
        db.execute("INSERT INTO work_versions VALUES(?,?,?,?)",
                   (ident,version+1,combined,now))
    return get_work(ident)


def improve_visual_prompt(prompt,mode="image",locale="es",provider="auto"):
    if mode not in ("image","video"):
        raise CreativeInvalid("Modo visual desconocido.")
    _,lang=language(locale)
    original=_clean(prompt,"Descripción",2000,8)
    text,engine=_ask(
        f"Sos SKY, directora de arte. Mejorá un prompt para {mode} en {lang}, "
        "con composición, iluminación, ambiente, estilo, plano y continuidad "
        "sin cambiar su objetivo ni inventar marcas. Devolvé SOLO el prompt.",
        original,provider,650)
    return {"original":original,"enhanced":_clean(text,"Prompt",3500),
            "provider":engine,"mode":mode}


def generate_image(prompt,locale="es",improve=False,provider="auto"):
    from .providers import local_only
    if local_only():
        raise CreativeUnavailable("SKY_LOCAL_ONLY impide solicitudes Gemini.")
    language(locale)
    text=_clean(prompt,"Prompt de imagen",2500,8)
    if improve:
        text=improve_visual_prompt(text,locale=locale,provider=provider)["enhanced"]
    from .gemini_provider import generar_imagen
    from . import sky_creative as cr
    data,mime=generar_imagen(text)
    ext={"image/png":".png","image/jpeg":".jpg","image/webp":".webp"}.get(mime)
    if not ext:
        raise CreativeUnavailable("El modelo no produjo una imagen válida.")
    return {"asset":cr.ingest(data,"SKY_Imagen_IA"+ext),"provider":"gemini",
            "prompt_used":text,"real_image":True}


def _shots(raw):
    text=raw.strip()
    if text.startswith(chr(96)*3):
        text=re.sub(r"^"+chr(96)*3+r"(?:json)?\s*|\s*"+chr(96)*3+r"$","",text,flags=re.I)
    parsed=json.loads(text)
    shots=parsed.get("shots") if isinstance(parsed,dict) else None
    if not isinstance(shots,list) or not 2 <= len(shots) <= 4:
        raise CreativeInvalid("Se requieren entre 2 y 4 planos.")
    out=[]
    for shot in shots:
        if not isinstance(shot,dict):
            raise CreativeInvalid("Plano inválido.")
        out.append({"visual":_clean(shot.get("visual"),"Imagen del plano",500,24),
                    "caption":_clean(shot.get("caption"),"Subtítulo",160)})
    return out


def music_wav(genre="cinematic",mood="hopeful",seconds=12,bpm=100,seed_text="SKY"):
    """Instrumental WAV original por síntesis y motivo pseudoaleatorio estable."""
    if genre not in MUSIC_STYLES or mood not in MUSIC_MOODS:
        raise CreativeInvalid("Estilo musical inválido.")
    if type(seconds) is not int or not 8 <= seconds <= 30:
        raise CreativeInvalid("Duración: 8 a 30 segundos.")
    if type(bpm) is not int or not 60 <= bpm <= 160:
        raise CreativeInvalid("BPM fuera de rango.")
    seed_text=_clean(seed_text,"Inspiración",150,1)
    rng=random.Random(int.from_bytes(hashlib.sha256(
        f"{genre}/{mood}/{seed_text}/{bpm}".encode()).digest()[:8],"big"))
    scale=(0,2,3,5,7,8,10) if mood in ("dramatic","mysterious") else (0,2,4,5,7,9,11)
    progression=(0,5,3,4) if mood in ("hopeful","happy") else (0,3,5,4)
    motif=[rng.choice((0,1,2,3,4,5,6)) for _ in range(8)]
    rate=22050; beatlength=60/bpm
    data=bytearray()
    for i in range(rate*seconds):
        t=i/rate; beat=int(t/beatlength); onset=t%beatlength
        root=progression[(beat//4)%4]
        bass=440*2**((48+scale[root]-69)/12)
        note=440*2**((60+scale[(root+motif[beat%8])%7]-69)/12)
        envelope=min(1,onset*30)*math.exp(-2.4*onset/beatlength)
        signal=(0.16*math.sin(2*math.pi*bass*t)+
                0.19*envelope*math.sin(2*math.pi*note*t)+
                0.036*envelope*math.sin(2*math.pi*note*2*t))
        if genre in ("pop","electronic"):
            signal+=0.08*math.exp(-onset*25)*math.sin(2*math.pi*85*onset)
        fade=max(0,min(1,t/0.13,(seconds-t)/0.35))
        sample=max(-1,min(1,signal*fade))
        data.extend(struct.pack("<h",round(sample*30000)))
    out=io.BytesIO()
    with wave.open(out,"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(data)
    return out.getvalue()


def save_music(**kwargs):
    from . import sky_creative as cr
    wav=music_wav(**kwargs)
    asset=cr.ingest(wav,"SKY_Musica_Original.wav")
    return {"asset":asset,"composer":"SKY procedural","audio_generated":True,
            "vocal_generation":False,"format":"wav"}


def movie_from_prompt(title,idea,locale="es",provider="auto",soundtrack=False):
    """Crea storyboard e imágenes IA; entrega trabajo de render a FFmpeg de SKY."""
    from .providers import local_only
    if local_only():
        raise CreativeUnavailable("Montaje IA requiere Gemini; no permitido en modo local.")
    _,lang=language(locale)
    title=_clean(title,"Título",120,3)
    idea=_clean(idea,"Argumento",1300,12)
    storyboard,planner=_ask(
        "Sos SKY directora cinematográfica. Devolvé SOLO JSON: "
        '{"shots":[{"visual":"descripción de escena sin texto","caption":"línea narrativa"}]}. '
        f"De 2 a 4 planos coherentes, leyendas en {lang}, personajes consistentes, "
        "descripciones precisas para generar imágenes. No prometas movimiento real.",
        json.dumps({"title":title,"idea":idea},ensure_ascii=False),provider,1300)
    try:
        scenes=_shots(storyboard)
    except (ValueError,TypeError) as exc:
        raise CreativeInvalid("SKY no obtuvo un storyboard JSON válido.") from exc
    from .gemini_provider import generar_imagen
    from . import sky_creative as cr
    ids=[]
    for shot in scenes:
        binary,mime=generar_imagen(shot["visual"])
        ext={"image/png":".png","image/jpeg":".jpg","image/webp":".webp"}.get(mime)
        if not ext:
            raise CreativeUnavailable("No se recibieron todos los fotogramas.")
        ids.append(cr.ingest(binary,"SKY_Escena_IA"+ext)["id"])
    spec={"width":1280,"height":720,"fps":24,
          "clips":[{"asset_id":aid,"start":0,"end":5,"speed":1,
                    "caption":shot["caption"]} for aid,shot in zip(ids,scenes)]}
    if soundtrack:
        music=cr.ingest(music_wav(seconds=len(ids)*5,seed_text=title),
                        "SKY_Banda_Sonora.wav")
        spec.update({"music_asset_id":music["id"],"music_volume":0.2})
    cr.validate_spec("video",spec)
    project=cr.create_project("video",title,spec)
    queued=cr.queue_video(project["id"])
    return {"controller":"SKY","project_id":project["id"],"job":queued,
            "scene_assets":ids,"scenes":len(ids),"real_motion_generation":False,
            "type":"AI_illustrated_montage","ready_to_download":False,
            "job_check":"/api/creative/jobs","planner":planner}


def capabilities():
    from .providers import provider_summary,local_only
    from .gemini_provider import disponible
    import shutil
    return {"controller":"SKY CORE","languages":dict(LANGUAGES),
            "writing_kinds":list(KINDS),"writing_requires_model":True,
            "image":{"provider":"gemini","configured":disponible() and not local_only(),
                     "checked_live":False},
            "video":{"format":"MP4","type":"AI image montage",
                     "real_motion_generation":False,
                     "ffmpeg_available":bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))},
            "music":{"mode":"original_instrumental_WAV","sung_vocals":False,
                     "duration_seconds":[8,30]},
            "voices_depend_on_installed_engine":True,
            "text_providers_configured":provider_summary()}
