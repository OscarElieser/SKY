"""Historial persistente de consultas SKY HUD en SQLite privado, sin nube."""
from __future__ import annotations
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROLE={"user","assistant"}
SOURCE={"chat","voz","hud"}


def _connect():
    p=Path(os.getenv("SKY_HUD_HISTORY_DB") or ROOT/"local_data"/"sky_hud_history.sqlite3")
    p.parent.mkdir(parents=True,exist_ok=True)
    try:p.parent.chmod(0o700)
    except OSError:pass
    conn=sqlite3.connect(p,timeout=12)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA busy_timeout=12000")
    conn.execute("""CREATE TABLE IF NOT EXISTS entries(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      role TEXT NOT NULL, source TEXT NOT NULL, text TEXT NOT NULL,
      created_at TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sky_history_created ON entries(id DESC)")
    try:p.chmod(0o600)
    except OSError:pass
    return conn


def append(role,text,source="chat"):
    if role not in ROLE or source not in SOURCE:
        raise ValueError("Tipo de conversación inválido.")
    if not isinstance(text,str) or not 1<=len(text.strip())<=4000:
        raise ValueError("Texto de historial inválido.")
    value=text.strip()
    with _connect() as conn:
        cur=conn.execute("INSERT INTO entries(role,source,text,created_at) VALUES(?,?,?,?)",
                         (role,source,value,datetime.now(timezone.utc).isoformat()))
        ident=cur.lastrowid
    return {"id":ident,"saved":True}


def list_entries(limit=50,before=None,query=None):
    if type(limit) is not int or not 1<=limit<=200:
        raise ValueError("Límite 1–200.")
    if before is not None and (type(before) is not int or before<1):
        raise ValueError("Cursor inválido.")
    if query is not None and (not isinstance(query,str) or len(query)>100):
        raise ValueError("Filtro inválido.")
    wheres=[];args=[]
    if before is not None:
        wheres.append("id < ?");args.append(before)
    if query:
        pattern=query.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
        wheres.append("text LIKE ? ESCAPE '\\'");args.append("%"+pattern+"%")
    where=" WHERE "+" AND ".join(wheres) if wheres else ""
    with _connect() as conn:
        rows=conn.execute("SELECT id,role,source,text,created_at FROM entries"+where+
                          " ORDER BY id DESC LIMIT ?",(*args,limit+1)).fetchall()
    has_more=len(rows)>limit
    rows=rows[:limit]
    return {"entries":[dict(x) for x in rows],
            "has_more":has_more,"next_before":rows[-1]["id"] if rows and has_more else None}


def count():
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
