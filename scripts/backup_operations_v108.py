"""Run SKY encrypted backups under a trusted operator; never an HTTP route."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from neural_core.sky_backup_schedule_v108 import run_once, rehearse_latest


def main(argv=None):
    parser = argparse.ArgumentParser(description='SKY v10.8: programación externa de respaldo y ensayo local')
    parser.add_argument('operation', choices=('once','rehearse'))
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--keep',type=int,default=7)
    parser.add_argument('--rpo-hours',type=float,default=48.0)
    args=parser.parse_args(argv)
    result = run_once(args.directory, keep=args.keep) if args.operation=='once' else rehearse_latest(args.directory,max_rpo_hours=args.rpo_hours)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if (result.get('rehearsal_passed', result.get('verified',False)) and result.get('rpo_age_within_target',True)) else 2

if __name__=='__main__':raise SystemExit(main())
