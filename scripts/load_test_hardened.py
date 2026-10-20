"""Bounded local load check for the hardened SKY edge; never targets arbitrary hosts."""
from __future__ import annotations
import argparse,concurrent.futures,json,time
import httpx

URL='https://127.0.0.1:8443/sky'

def hit(_:int)->tuple[int,float]:
    started=time.perf_counter()
    with httpx.Client(verify=False,timeout=10,trust_env=False) as client:
        response=client.get(URL)
    return response.status_code,(time.perf_counter()-started)*1000

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--requests',type=int,default=200)
    parser.add_argument('--concurrency',type=int,default=20)
    args=parser.parse_args()
    if not 1<=args.requests<=2000 or not 1<=args.concurrency<=100:
        parser.error('Límites: 1..2000 solicitudes y 1..100 concurrentes')
    start=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results=list(pool.map(hit,range(args.requests)))
    elapsed=time.perf_counter()-start
    times=sorted(ms for _,ms in results)
    report={'url':URL,'requests':args.requests,'concurrency':args.concurrency,
            'success':sum(code==200 for code,_ in results),'errors':sum(code!=200 for code,_ in results),
            'requests_per_second':round(args.requests/elapsed,2),'p50_ms':round(times[len(times)//2],2),
            'p95_ms':round(times[min(len(times)-1,int(len(times)*.95))],2),'elapsed_seconds':round(elapsed,2)}
    print(json.dumps(report,indent=2))
    return 0 if report['errors']==0 else 1

if __name__=='__main__':raise SystemExit(main())
