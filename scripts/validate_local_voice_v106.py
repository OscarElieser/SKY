"""Run a REAL local-model speech test, without downloading models or uploading audio.

Returns nonzero when the model isn't installed or accuracy misses the threshold.
No positive validation result is generated from a mock or model-less fallback.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from neural_core.sky_stt_isolated_v106 import capabilities, isolated_transcribe


def word_error_rate(reference: str, hypothesis: str) -> float:
    norm = lambda value: re.findall(r'\w+', value.casefold(), re.UNICODE)
    a, b = norm(reference), norm(hypothesis)
    if not a:
        raise ValueError('El texto de referencia no puede estar vacío')
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j-1] + (left != right)))
        previous = current
    return round(previous[-1] / len(a), 4)


def main(argv=None):
    parser = argparse.ArgumentParser(description='SKY: prueba de voz REAL, offline')
    parser.add_argument('--audio', required=True, type=Path)
    parser.add_argument('--expected', required=True)
    parser.add_argument('--language', default=None)
    parser.add_argument('--max-wer', type=float, default=0.40)
    args = parser.parse_args(argv)
    if not 0 <= args.max_wer <= 1:
        parser.error('--max-wer debe estar entre 0 y 1')
    status = capabilities()
    if not status['available']:
        print(json.dumps({'tested': False, 'reason': 'local_model_not_installed'}))
        return 2
    result = isolated_transcribe(args.audio.read_bytes(), filename=args.audio.name,
                                 language=args.language)
    wer = word_error_rate(args.expected, result['text'])
    passed = wer <= args.max_wer
    # Do not print the private audio/transcript, model path or secret values.
    print(json.dumps({'tested': True, 'offline': True, 'wer': wer, 'passed': passed,
                      'language': result.get('detected_language')}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
