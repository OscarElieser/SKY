"""Run *real*, private recognition over operator-provided multilingual WAV files.

No model or reference audio is shipped with SKY. The script never downloads
models, never sends recordings over the network and never logs transcripts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from neural_core.sky_stt_local import capabilities
from scripts.validate_local_voice_v106 import word_error_rate

LANGUAGE = re.compile(r'^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$')


def benchmark(manifest:Path, audio_dir:Path, *, threshold:float=0.35,
              transcriber=None, model_status=None) -> dict:
    if not 0<=threshold<=1:raise ValueError('WER objetivo inválido')
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size>64*1024:
        raise ValueError('Manifiesto inválido')
    if audio_dir.is_symlink() or not audio_dir.is_dir():raise ValueError('Carpeta de audio inválida')
    dataset=json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(dataset,list) or not (2<=len(dataset)<=30):
        raise ValueError('Se requieren entre 2 y 30 pruebas')
    locales=set()
    for item in dataset:
        if not isinstance(item,dict):raise ValueError('Caso inválido')
        language=item.get('language');name=item.get('file');reference=item.get('reference')
        if not isinstance(language,str) or not LANGUAGE.fullmatch(language):raise ValueError('Idioma inválido')
        locales.add(language)
        if (not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,70}\.wav',name)):
            raise ValueError('Solo se admiten archivos WAV locales sin rutas')
        if not isinstance(reference,str) or not reference.strip() or len(reference)>2000:
            raise ValueError('Transcripción de referencia inválida')
        audio=audio_dir/name
        if audio.is_symlink() or not audio.is_file() or not (1024 <= audio.stat().st_size <= 10*1024*1024):
            raise ValueError('Audio ausente, enlazado o demasiado grande')
    if len(locales)<2:raise ValueError('La prueba debe incluir al menos dos idiomas')
    status=model_status if model_status is not None else capabilities()
    if not status.get('available'):
        return {'tested':False,'reason':'modelo_local_no_instalado',
                'languages_requested':sorted(locales),'actual_transcriptions':0,
                'certified':False}
    if transcriber is None:
        from neural_core.sky_stt_isolated_v106 import isolated_transcribe
        transcriber=isolated_transcribe
    details=[]
    for entry in dataset:
        result=transcriber((audio_dir/entry['file']).read_bytes(),filename=entry['file'],language=entry['language'])
        if not isinstance(result,dict) or not isinstance(result.get('text'),str):
            raise ValueError('El motor devolvió una respuesta inválida')
        wer=word_error_rate(entry['reference'],result['text'])
        details.append({'language':entry['language'], 'wer':round(wer,4),
                        'within_target':wer<=threshold,
                        'audio_sha256':hashlib.sha256((audio_dir/entry['file']).read_bytes()).hexdigest()})
    return {'tested':True,'actual_transcriptions':len(details),
            'language_count':len(locales), 'all_within_target':all(item['within_target'] for item in details),
            'threshold_wer':threshold,'results_without_transcripts':details,
            'certified':False}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True,type=Path)
    p.add_argument('--audio-dir',required=True,type=Path)
    p.add_argument('--threshold',type=float,default=0.35)
    p.add_argument('--report-only',action='store_true',help='Success requires real inferences; WER is reported but not approved')
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    result=benchmark(args.manifest,args.audio_dir,threshold=args.threshold)
    if args.out:
        if args.out.exists() or args.out.is_symlink():raise FileExistsError('Informe ya existe')
        with args.out.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result.get('tested') or result.get('actual_transcriptions',0)<2:
        return 2
    return 0 if args.report_only or result.get('all_within_target') else 2

if __name__=='__main__':raise SystemExit(main())
