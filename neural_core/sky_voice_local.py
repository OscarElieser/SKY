"""SKY 10.3 local voiceover. No network, shell, AI voice cloning or downloads.

The local eSpeak voice set is queried from the installed binary. Supported languages
vary by installation; never promise that every SKY UI locale has a voice.
"""
from __future__ import annotations
import os,re,shutil,subprocess,tempfile,uuid,wave
from pathlib import Path

MAX_CHARS=800
MAX_VIDEO_BYTES=85*1024*1024
MAX_DURATION=60
_LANG=re.compile(r'^[a-z]{2,3}(?:-[a-z0-9]{2,8})?$')


def _espeak()->str:
    binary=shutil.which('espeak-ng') or shutil.which('espeak')
    if not binary:
        raise RuntimeError('El motor eSpeak no está instalado en este equipo')
    return binary


def voices()->list[str]:
    result=subprocess.run([_espeak(),'--voices'],capture_output=True,text=True,timeout=10,check=True)
    result_codes=set()
    for line in result.stdout.splitlines()[1:]:
        parts=line.split()
        if len(parts)>1 and _LANG.fullmatch(parts[1].lower()):
            result_codes.add(parts[1].lower())
    return sorted(result_codes)


def select_voice(locale:str)->str:
    from neural_core.sky_languages import normalize
    code=normalize(locale,strict=True)
    available=set(voices())
    if code in available:return code
    root=code.split('-')[0]
    if root in available:return root
    for alias in ({'fr':'fr-fr','en':'en-gb','es':'es-la','zh':'zh','pt':'pt-br'}.get(root),):
        if alias in available:return alias
    raise ValueError('El motor de voz local no dispone de una voz para ese idioma')


def synthesize(text:str,locale:str='es')->bytes:
    if not isinstance(text,str) or not text.strip() or len(text)>MAX_CHARS:
        raise ValueError('Texto de voz inválido o demasiado largo')
    if any(ord(ch)<32 and ch not in '\n\t' for ch in text):
        raise ValueError('Caracteres de control no permitidos')
    selected=select_voice(locale)
    with tempfile.TemporaryDirectory(prefix='sky_voice_') as folder:
        wav=Path(folder)/'voice.wav'
        # stdin prevents positional flag injection; neither a shell nor a file URL is used.
        command=[_espeak(),'-v',selected,'-s','145','-w',str(wav),'--stdin']
        done=subprocess.run(command,input=text,encoding='utf-8',capture_output=True,
                            timeout=30,check=False)
        if done.returncode!=0 or not wav.exists() or wav.stat().st_size<128:
            raise RuntimeError('No se pudo sintetizar voz local')
        with wave.open(str(wav),'rb') as handle:
            if handle.getnframes()/handle.getframerate()>MAX_DURATION:
                raise ValueError('La narración supera el límite de duración')
        return wav.read_bytes()


def dub_video(video:Path,text:str,locale:str,folder:Path)->Path:
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise RuntimeError('La mezcla de video requiere FFmpeg y FFprobe')
    if not video.is_file() or video.stat().st_size>MAX_VIDEO_BYTES:
        raise ValueError('El recurso de video no es válido')
    folder.mkdir(parents=True,exist_ok=True)
    duration=subprocess.run([ffprobe,'-v','error','-select_streams','v:0',
        '-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(video)],
        capture_output=True,text=True,timeout=15,check=False)
    try:seconds=float(duration.stdout.strip())
    except ValueError as exc:raise ValueError('Duración de video inválida') from exc
    if duration.returncode!=0 or not 0<seconds<=MAX_DURATION:
        raise ValueError('Video fuera del límite de 60 segundos')
    name=uuid.uuid4().hex
    output=folder/(name+'.mp4')
    with tempfile.TemporaryDirectory(prefix='sky_dubbing_') as scratch:
        voice=Path(scratch)/'speech.wav'
        voice.write_bytes(synthesize(text,locale))
        # Replaces source audio; original media remains untouched.
        args=[ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y',
              '-i',str(video),'-i',str(voice),'-map','0:v:0','-map','1:a:0',
              '-c:v','copy','-c:a','aac','-af','apad','-t',f'{seconds:.3f}',
              '-movflags','+faststart',str(output)]
        try:result=subprocess.run(args,capture_output=True,timeout=90,check=False)
        except subprocess.TimeoutExpired as exc:
            output.unlink(missing_ok=True)
            raise RuntimeError('Tiempo de render agotado') from exc
        if result.returncode or not output.is_file() or output.stat().st_size<1000:
            output.unlink(missing_ok=True)
            raise RuntimeError('No se pudo mezclar la narración con el MP4')
    return output
