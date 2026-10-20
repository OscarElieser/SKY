"""Non-destructive DAST assertions against the fixed local hardened endpoint."""
from __future__ import annotations
import json
import httpx

BASE='https://127.0.0.1:8443'

def main():
    checks={}
    with httpx.Client(base_url=BASE,verify=False,timeout=10,trust_env=False) as client:
        page=client.get('/sky')
        checks['https_page']=page.status_code==200
        checks['hsts']='max-age=' in page.headers.get('strict-transport-security','')
        checks['anti_frame']=page.headers.get('x-frame-options')=='DENY'
        checks['nosniff']=page.headers.get('x-content-type-options')=='nosniff'
        checks['secret_blocked']=client.get('/.env').status_code==404
        checks['trace_blocked']=client.request('TRACE','/sky').status_code==405
        hostile_host=client.get('/sky',headers={'Host':'evil.example'})
        checks['host_isolated']=(hostile_host.status_code in (400,403,421) or not hostile_host.content)
        checks['origin_blocked']=client.post('/api/i18n/script-hint',headers={'Origin':'https://evil.example'},json={'text':'test'}).status_code==403
        checks['private_auth']=client.get('/api/sky/roles').status_code==401
    print(json.dumps(checks,indent=2))
    return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(main())
