"""Static safety audit for ephemeral and production compose configurations.

Never claims that Docker was executed unless the operator separately ran it.
"""
from __future__ import annotations
import json
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]

def audit() -> dict:
    smoke = yaml.safe_load((ROOT/'deploy/compose.integration.yml').read_text(encoding='utf-8'))
    production = yaml.safe_load((ROOT/'deploy/compose.yml').read_text(encoding='utf-8'))
    problems=[]
    for label,settings in [('integration',smoke),('production',production)]:
        services=settings['services']
        for key in ('api','renderer','redis','proxy'):
            if key not in services: problems.append(f'{label}:{key}:missing')
        for key in ('api','renderer','redis'):
            svc=services[key]
            if 'ports' in svc or 'expose' in svc and svc.get('expose'):
                problems.append(f'{label}:{key}:direct_ports')
            if svc.get('cap_drop')!=['ALL'] or svc.get('read_only') is not True:
                problems.append(f'{label}:{key}:privileged_or_writable')
            if 'no-new-privileges:true' not in svc.get('security_opt',[]):
                problems.append(f'{label}:{key}:new_privileges')
        if services['renderer'].get('network_mode')!='none':problems.append(f'{label}:renderer_network')
        net= 'internal' if label=='integration' else 'backend'
        if not settings['networks'][net].get('internal'):problems.append(f'{label}:redis_network')
        if services['api']['environment'].get('SKY_CREATIVE_WORKER')!='0':
            problems.append(f'{label}:renderer_in_api')
        if 'sky_api_key' not in services['api']['secrets']:
            problems.append(f'{label}:secret_mount')
        if 'sky_redis_password' not in services['api']['secrets']:
            problems.append(f'{label}:redis_password_mount')
    publishers=smoke['services']['proxy']['ports']
    if publishers != ['127.0.0.1:18443:443']:
        problems.append('integration:non_local_proxy')
    if 'tls internal' not in (ROOT/'deploy/Caddy.integration').read_text(encoding='utf8'):
        problems.append('integration:missing_tls')
    return {'static_passed':not problems,'issues':problems,'docker_executed':False,
            'remote_host_tested':False,'production_certified':False}

def main():
    r=audit();print(json.dumps(r,indent=2));return 0 if r['static_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
