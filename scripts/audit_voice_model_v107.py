"""Offline verification of a *user-installed* speech model and a local WAV.

No automatic downloads, no API keys, no network. Only counts are reported.
A real recognition test requires --audio plus --reference; without those flags
results explicitly say that quality was NOT tested.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def audit(*, audio: Path | None = None, reference: str | None = None,
          language: str | None = None) -> dict:
    from neural_core.sky_stt_local import capabilities, model_directory
    from neural_core.sky_stt_isolated_v106 import isolated_transcribe
    status=capabilities()
    result={'engine':'faster-whisper','offline':True,'model_available':status['available'],
            'real_transcription_tested':False,'network_requests':0}
    directory=model_directory()
    if directory and (directory/'model.bin').is_file():
        result['model_sha256']=digest(directory/'model.bin')
    if audio is None and reference is None:
        result['reason']='No se proporcionaron audio ni referencia para validar palabras'
        return result
    if audio is None or reference is None or not reference.strip():
        raise ValueError('Se requieren juntos --audio y --reference')
    if not audio.is_file() or audio.is_symlink() or audio.suffix.lower() not in ('.wav','.mp3','.flac'):
        raise ValueError('Audio local inválido')
    if audio.stat().st_size > 10*1024*1024:
        raise ValueError('Audio supera límite')
    if not status['available']:
        result['reason']='Instalá faster-whisper y un modelo CTranslate2 local para la prueba real'
        return result
    from scripts.validate_local_voice_v106 import word_error_rate
    transcript=isolated_transcribe(audio.read_bytes(),filename=audio.name,language=language)
    result.update(real_transcription_tested=True,
                  wer=word_error_rate(reference,transcript['text']),
                  reference_word_count=len(reference.split()),
                  recognized_word_count=len(transcript['text'].split()),
                  detected_language=transcript.get('detected_language'))
    # Never print user speech or the reference transcript in logs or JSON.
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audio', type=Path)
    parser.add_argument('--reference')
    parser.add_argument('--language')
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    result=audit(audio=args.audio, reference=args.reference, language=args.language)
    if args.output:
        if args.output.exists():
            raise FileExistsError('No se sobrescribe un informe existente')
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['real_transcription_tested'] else 2

if __name__=='__main__':
    raise SystemExit(main())
