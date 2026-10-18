"""SKY v10 — microbenchmark reproducible de la API local autenticada.

NO es una prueba de carga distribuida ni un SLA de producción.
No utiliza ni solicita API keys reales de proveedores IA.
"""
from __future__ import annotations
import argparse,os,secrets,statistics,tempfile,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description='Prueba local de carga ligera sobre Creative Studio')
    parser.add_argument('--requests',type=int,default=80)
    parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args()
    if not 1<=args.requests<=500 or not 1<=args.workers<=16:
        parser.error('Máximo 500 solicitudes y 16 trabajadores')
    with tempfile.TemporaryDirectory(prefix='sky_bench_') as folder:
        temp=Path(folder)
        token='bench_'+secrets.token_urlsafe(32)
        os.environ['SKY_API_KEY']=token
        os.environ['SKY_CREATIVE_WORKER']='0';os.environ['SKY_WORKFLOWS_ENABLED']='0'
        os.environ['SKY_CREATIVE_DB']=str(temp/'creative.sqlite3')
        os.environ['SKY_CREATIVE_DIR']=str(temp/'store')
        os.environ['SKY_PROJECTS_DB']=str(temp/'projects.sqlite3')
        os.environ['SKY_METAVERSE_DB']=str(temp/'worlds.sqlite3')
        from fastapi.testclient import TestClient
        from metaverse.api import app
        with TestClient(app) as client:
            header={'X-SKY-KEY':token}
            assert client.get('/api/creative/capabilities',headers=header).status_code==200
            def request(_):
                start=time.perf_counter()
                response=client.get('/api/creative/capabilities',headers=header)
                return (time.perf_counter()-start)*1000,response.status_code
            began=time.perf_counter()
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                samples=list(pool.map(request,range(args.requests)))
            elapsed=time.perf_counter()-began
            latencies=sorted(x[0] for x in samples)
            failures=sum(1 for _,code in samples if code!=200)
            output={'requests':args.requests,'workers':args.workers,'errors':failures,
                'seconds':round(elapsed,3),'requests_per_second':round(args.requests/elapsed,2),
                'p50_ms':round(statistics.median(latencies),2),
                'p95_ms':round(latencies[min(len(latencies)-1,int(.95*len(latencies)))],2)}
            print(__import__('json').dumps(output,ensure_ascii=False,indent=2))
            if failures:raise SystemExit(1)
if __name__=='__main__':main()
