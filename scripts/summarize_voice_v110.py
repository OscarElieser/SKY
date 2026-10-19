"""Read only WER numbers from an offline model trial; never publish transcripts."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def summarize(report: dict) -> dict:
    if not report.get('tested') or report.get('actual_transcriptions', 0) < 2:
        raise ValueError('No hay transcripciones reales verificadas')
    details=report.get('results_without_transcripts') or []
    if len(details) != report['actual_transcriptions']:
        raise ValueError('Informe WER incompleto')
    return {'real_inference': True, 'model_certified': False,
            'accuracy_gate_passed': bool(report.get('all_within_target')),
            'wer_threshold': report['threshold_wer'],
            'language_wer': {item['language']:item['wer'] for item in details},
            'samples':len(details)}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('report',type=Path)
    p.add_argument('--enforce',action='store_true')
    args=p.parse_args(argv)
    if args.report.is_symlink() or args.report.stat().st_size>65536:
        p.error('Informe inválido')
    summary=summarize(json.loads(args.report.read_text(encoding='utf8')))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 2 if args.enforce and not summary['accuracy_gate_passed'] else 0


if __name__=='__main__':raise SystemExit(main())
