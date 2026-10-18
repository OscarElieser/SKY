"""SKY Live: monitor informativo periódico, persistente en SQLite local.

Se ejecuta sólo si el propietario arranca sky_live.py. Sin publicaciones ni escrituras
remotas. URL fija, no se hace de proxy a direcciones arbitrarias.
"""
from __future__ import annotations
import json, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error
from .sky_evolution import path_db
BAQUEANO_URL='https://baqueanonicaragua.com/'


def _db():
    c=sqlite3.connect(path_db(),timeout=10)
    c.row_factory=sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS live_checks (
      id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
      check_name TEXT NOT NULL, ok INTEGER NOT NULL, latency_ms INTEGER,
      http_code INTEGER, message TEXT NOT NULL)''')
    return c


def registrar(name:str, ok:bool, ms:int|None, code:int|None, msg:str):
    if name not in ('baqueano_web','sky_heartbeat'):raise ValueError('Check no permitido')
    with _db() as c:
        c.execute('INSERT INTO live_checks(created_at,check_name,ok,latency_ms,http_code,message) VALUES (?,?,?,?,?,?)',
                 (datetime.now(timezone.utc).isoformat(),name,int(ok),ms,code,msg[:250]))
        c.execute('DELETE FROM live_checks WHERE id NOT IN (SELECT id FROM live_checks ORDER BY id DESC LIMIT 300)')


def revisar_baqueano():
    start=time.monotonic()
    req=request.Request(BAQUEANO_URL,headers={'User-Agent':'SKY-Personal-HealthCheck/5.0'})
    try:
        with request.urlopen(req,timeout=9) as r: code=int(r.status)
        elapsed=int((time.monotonic()-start)*1000)
        ok=200<=code<400
        registrar('baqueano_web',ok,elapsed,code,'Respuesta HTTP recibida' if ok else 'Código HTTP inesperado')
        return {'ok':ok,'http_code':code,'latency_ms':elapsed}
    except error.HTTPError as exc:
        elapsed=int((time.monotonic()-start)*1000)
        registrar('baqueano_web',False,elapsed,exc.code,f'Error HTTP {exc.code}')
        return {'ok':False,'http_code':exc.code,'latency_ms':elapsed}
    except (error.URLError,TimeoutError,OSError) as exc:
        registrar('baqueano_web',False,int((time.monotonic()-start)*1000),None,type(exc).__name__)
        return {'ok':False,'http_code':None,'latency_ms':None}


def heartbeat():
    registrar('sky_heartbeat',True,None,None,'SKY Live sigue ejecutándose')


def historial(limit:int=30):
    with _db() as c:return [dict(r) for r in c.execute('SELECT * FROM live_checks ORDER BY id DESC LIMIT ?', (max(1,min(limit,300)),))]


def ejecutar_ciclo():
    heartbeat()
    return revisar_baqueano()
