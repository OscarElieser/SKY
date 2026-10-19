"""Check SKY container baseline, and optionally run a Docker-only smoke test.

No automatic port exposure and no claim of executed containers when Docker is
missing. A production compose 'up' is NEVER performed by this script.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def static_audit() -> dict:
    config=yaml.safe_load((ROOT/'deploy/compose.yml').read_text(encoding='utf-8'))
    services=config['services']; issues=[]
    for name in ('api','renderer','redis'):
        item=services.get(name,{})
        if item.get('read_only') is not True: issues.append(f'{name}: read_only faltante')
        if item.get('cap_drop') != ['ALL']: issues.append(f'{name}: capacidades adicionales')
        if 'ports' in item: issues.append(f'{name}: puerto publicado')
        if 'no-new-privileges:true' not in item.get('security_opt',[]):issues.append(f'{name}: privilegios sin restricción')
    renderer=services.get('renderer',{})
    if renderer.get('network_mode') != 'none':issues.append('renderer con red habilitada')
    if not config.get('networks',{}).get('backend',{}).get('internal'):
        issues.append('red de Redis no es privada')
    api=services.get('api',{})
    if api.get('environment',{}).get('SKY_WORKFLOWS_ENABLED')!='0':issues.append('workflows públicos activos')
    if not (ROOT/'.dockerignore').is_file():issues.append('falta .dockerignore')
    if (ROOT/'deploy/secrets/sky_api_key.txt').exists():issues.append('secreto real dentro del proyecto')
    return {'static_passed':not issues, 'static_issues':issues,
            'docker_available': bool(shutil.which('docker')),
            'docker_executed':False, 'production_certified':False}


def docker_smoke(*, runtime:bool=False) -> dict:
    report=static_audit()
    if not report['static_passed']:return report
    if not runtime:return report
    binary=shutil.which('docker')
    if not binary:
        report['runtime_status']='not_run_docker_missing'
        return report
    # Only inspect tool availability and run a NO-NETWORK ephemeral container.
    try:
        version=subprocess.run([binary,'compose','version'],capture_output=True,text=True,timeout=10,check=False)
        if version.returncode:
            report['runtime_status']='not_run_compose_unavailable';return report
        # The operator must build a trusted image in advance. No pull/build/up here.
        image=os.environ.get('SKY_SMOKE_IMAGE','').strip()
        if not image or any(c.isspace() for c in image):
            report['runtime_status']='not_run_image_not_provided';return report
        args=[binary,'run','--rm','--network','none','--read-only',
              '--security-opt','no-new-privileges','--cap-drop','ALL',
              '--pids-limit','64','--memory','512m','--cpus','1',
              '--tmpfs','/tmp:rw,noexec,nosuid,size=32m',
              '--entrypoint','python',image,
              '-c','from metaverse.api import app; print("sky-offline-import-ok")']
        run=subprocess.run(args,capture_output=True,text=True,timeout=120,check=False)
        report['docker_executed']=True
        report['runtime_status']='passed' if run.returncode==0 and 'sky-offline-import-ok' in run.stdout else 'failed'
        report['container_no_network']=True
    except (subprocess.TimeoutExpired,OSError):
        report['runtime_status']='failed_or_timeout'
    return report


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--runtime',action='store_true');args=p.parse_args(argv)
    report=docker_smoke(runtime=args.runtime)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report['static_passed']:return 1
    if args.runtime and report.get('runtime_status')!='passed':return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
