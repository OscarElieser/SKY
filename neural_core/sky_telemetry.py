"""Telemetría verificable de solicitudes. NO es una visualización de pensamiento interno.

No almacena contenidos, IPs, agentes de usuario, secretos ni cuerpos de mensajes.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import os,time,sqlite3
ROOT=Path(__file__).resolve().parents[1]

def _conn():
    p=Path(os.getenv('SKY_TELEMETRY_DB') or ROOT/'local_data'/'sky_telemetry.sqlite3')
    p.parent.mkdir(exist_ok=True,parents=True)
    c=sqlite3.connect(p,timeout=12)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, created_at INTEGER NOT NULL, group_name TEXT NOT NULL, elapsed_ms INTEGER NOT NULL, status INTEGER NOT NULL)')
    return c

def _group(path):
    if path.startswith('/api/office'):return 'Office Studio'
    if path.startswith('/api/community'):return 'Comunidad'
    if path.startswith('/api/sky'):return 'Orquestador SKY'
    if path.startswith('/api/world'):return 'Metaverso'
    if path.startswith('/api/chat') or path.startswith('/v1/chat'):return 'Chat IA'
    if path.startswith('/api/evolution'):return 'Memoria / metas'
    if path.startswith('/api/studio'):return 'Studio 3D'
    return 'Servicios generales'

def record(path,ms,status):
    if path.startswith('/static/') or path in ('/api/health','/api/sky/activity'):return
    try:
        with _conn() as c:
            c.execute('INSERT INTO requests(created_at,group_name,elapsed_ms,status) VALUES(?,?,?,?)',
                      (int(time.time()),_group(path),max(0,min(3600000,int(ms))),int(status)))
            # Mantiene últimos ~3000 registros. No es una promesa de disponibilidad.
            c.execute('DELETE FROM requests WHERE id <= (SELECT MAX(id)-3000 FROM requests)')
    except (OSError,sqlite3.Error):pass

def activity(limit=35):
    with _conn() as c:
        rows=c.execute('SELECT created_at,group_name,elapsed_ms,status FROM requests ORDER BY id DESC LIMIT ?',(max(1,min(limit,100)),)).fetchall()
    groups=Counter(row[1] for row in rows)
    avg=int(sum(x[2] for x in rows)/len(rows)) if rows else None
    return {'events':[{'at':x[0],'module':x[1],'latency_ms':x[2],'status':x[3]} for x in rows],
            'events_sampled':len(rows),'average_ms_in_sample':avg,
            'groups':dict(groups),'mode':'Eventos reales del API local: no son activaciones de neuronas ni pensamientos del modelo',
            'modules':[{'id':'input','label':'Texto/voz/foto','type':'entrada'},
                       {'id':'roles','label':'Selección de roles','type':'enrutamiento'},
                       {'id':'tools','label':'Herramientas SKY','type':'acción'},
                       {'id':'memory','label':'Memoria','type':'persistencia'},
                       {'id':'MLP-GRU','label':'MLP + GRU','type':'motor opcional'},
                       {'id':'providers','label':'Modelos externos','type':'optativo'}]}
