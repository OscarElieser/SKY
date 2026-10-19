"""Bounded SRT/WebVTT subtitles and optional MP4 hard-burn, without shell commands.

Transcription is not inferred from audio: captions must be supplied by the user
or by a separately configured speech-to-text provider. Keeps source unmodified.
"""
from __future__ import annotations
import os,re,subprocess,tempfile,uuid
from pathlib import Path
from neural_core.sky_languages import normalize

LIMIT_CUES=160
MAX_SECONDS=300
TIMESTAMP=re.compile(r'^(\d{1,2}):([0-5]\d):([0-5]\d)[,.](\d{3})$')


def seconds(stamp: str) -> float:
    match=TIMESTAMP.fullmatch(stamp.strip())
    if not match:raise ValueError('Marca temporal no válida (HH:MM:SS,mmm)')
    hh,mm,ss,ms=map(int,match.groups())
    return hh*3600+mm*60+ss+ms/1000


def vtt_stamp(value: float)->str:
    ms=round(value*1000)
    h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'


def parse_srt(srt: str) -> list[tuple[float,float,str]]:
    if not isinstance(srt,str) or len(srt)>32000:raise ValueError('Subtítulos demasiado largos')
    normalized=srt.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff').strip()
    parts=re.split(r'\n\s*\n',normalized)
    if not 1<=len(parts)<=LIMIT_CUES:raise ValueError('Cantidad de subtítulos fuera de límites')
    cues=[]
    for item in parts:
        lines=[line.strip() for line in item.split('\n') if line.strip()]
        if lines and lines[0].isdigit():lines=lines[1:]
        if len(lines)<2 or '-->' not in lines[0]:raise ValueError('Cada subtítulo necesita intervalo y texto')
        first,second=map(str.strip,lines[0].split('-->',1))
        start,end=seconds(first),seconds(second)
        text='\n'.join(lines[1:])
        if not 0<=start<end<=MAX_SECONDS or end-start>25:raise ValueError('Duración o intervalo de subtítulo inválido')
        if not text or len(text)>900 or any(ord(x)<32 and x not in '\n\t' for x in text):raise ValueError('Texto de subtítulo inválido')
        # Strip formatting markers to prevent HTML/script markup in WebVTT.
        text=text.replace('<','&lt;').replace('>','&gt;')
        cues.append((start,end,text))
    if cues!=sorted(cues,key=lambda x:x[0]):raise ValueError('Los subtítulos deben estar ordenados')
    return cues


def to_vtt(srt:str, language:str='es')->str:
    normalize(language,strict=True)
    cues=parse_srt(srt)
    return 'WEBVTT\n\n'+'\n\n'.join(f'{vtt_stamp(a)} --> {vtt_stamp(b)}\n{text}' for a,b,text in cues)+'\n'


def burn_subtitles(source:Path, srt:str, folder:Path, *,timeout:int=120)->Path:
    """Render an MP4 in a private directory from an ingested asset path."""
    import shutil
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('Se requieren FFmpeg y FFprobe')
    cues=parse_srt(srt)
    if source.stat().st_size > 85*1024*1024:
        raise ValueError('Video de origen demasiado grande para subtítulos locales')
    folder.mkdir(parents=True,exist_ok=True)
    try:folder.chmod(0o700)
    except OSError:pass
    # Relative safe ASCII file names prevent filter-path injection on Windows/Unix.
    name=uuid.uuid4().hex
    subtitle=folder/(name+'.srt')
    target=folder/(name+'.mp4')
    safe_srt='\n\n'.join(f'{i}\n{vtt_stamp(a).replace(".",",")} --> {vtt_stamp(b).replace(".",",")}\n{text}' for i,(a,b,text) in enumerate(cues,1))+'\n'
    # Subtitle HTML escaped for VTT is not required; preserve user-facing literals.
    subtitle.write_text(safe_srt,encoding='utf-8')
    try:
        # Prevent external subtitle URLs and shell interpretation; filter refers only to UUID filename.
        command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(source),
                 '-vf',f'subtitles={subtitle.name}', '-c:v','libx264','-preset','veryfast',
                 '-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart','-t',str(MAX_SECONDS),str(target)]
        result=subprocess.run(command,cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              timeout=timeout,check=False)
        if result.returncode!=0 or not target.exists() or target.stat().st_size<800:
            raise RuntimeError('FFmpeg no pudo aplicar los subtítulos (comprobá soporte libass)')
        return target
    finally:
        subtitle.unlink(missing_ok=True)
