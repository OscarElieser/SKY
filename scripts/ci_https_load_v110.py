"""Bounded synthetic HTTPS health load with real hostname/certificate verification.

Only the isolated 127.0.0.1:18443 test stack is accessed. No user content,
credentials, browser cookies or production endpoints are sent by this probe.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import math
from pathlib import Path
import socket
import ssl
import time


def measure(ca:Path, *, requests:int=80, concurrency:int=8) -> dict:
    if ca.is_symlink() or not ca.is_file() or ca.stat().st_size>131072:
        raise ValueError('Certificado CA inválido')
    if not 2 <= requests <= 300 or not 1 <= concurrency <= 20:
        raise ValueError('Carga sintética fuera de límites')
    context=ssl.create_default_context(cafile=str(ca))
    context.check_hostname=True
    context.verify_mode=ssl.CERT_REQUIRED

    def check():
        start=time.perf_counter()
        try:
            # Connect locally but verify SNI / expected certificate name sky.test.
            with socket.create_connection(('127.0.0.1',18443),timeout=8) as raw:
                with context.wrap_socket(raw,server_hostname='sky.test') as connection:
                    connection.settimeout(8)
                    connection.sendall(b'GET /api/health HTTP/1.1\r\nHost: sky.test\r\nConnection: close\r\n\r\n')
                    response=http.client.HTTPResponse(connection)
                    response.begin()
                    if response.status!=200:
                        return (time.perf_counter()-start)*1000, True
                    body=response.read(65537)
                    if len(body)>65536 or not isinstance(json.loads(body),dict):
                        return (time.perf_counter()-start)*1000, True
        except (OSError,ValueError,ssl.SSLError,http.client.HTTPException,json.JSONDecodeError):
            return (time.perf_counter()-start)*1000, True
        return (time.perf_counter()-start)*1000, False

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results=list(pool.map(lambda _:check(),range(requests)))
    ordered=sorted(ms for ms,_ in results)
    errors=sum(1 for _,bad in results if bad)
    return {'requests':requests,'concurrency':concurrency,'errors':errors,
            'error_rate':round(errors/requests,4),
            'p95_ms':round(ordered[max(0,math.ceil(.95*requests)-1)],2),
            'maximum_ms':round(max(ordered),2),
            'tls_peer_verified':True,'production_capacity_proven':False}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--ca',type=Path,required=True)
    p.add_argument('--requests',type=int,default=80)
    p.add_argument('--concurrency',type=int,default=8)
    p.add_argument('--p95-limit-ms',type=int,default=1500)
    args=p.parse_args(argv)
    result=measure(args.ca,requests=args.requests,concurrency=args.concurrency)
    print(json.dumps(result,indent=2))
    return 0 if result['errors']==0 and result['p95_ms']<=args.p95_limit_ms else 2


if __name__=='__main__':raise SystemExit(main())
