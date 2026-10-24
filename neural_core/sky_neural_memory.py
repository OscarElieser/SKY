"""SKY Neural Memory: reviewable encrypted facts + evidence-only execution learning.

No hidden LLM weight updates, no scraping or auto-ingestion of untrusted text.
Auto-observations store ONLY action categories and verified outcomes.
Personal memory is explicit, owner-scoped, encrypted at rest, and revocable.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
_LOCK = threading.RLock()
CATEGORIES = {"preferencia", "proyecto", "correccion", "conocimiento"}
MAX_FACTS = 400
MAX_OBSERVATIONS = 10000


def _db_path() -> Path:
    return Path(os.environ.get("SKY_NEURAL_MEMORY_DB") or ROOT / "local_data" / "sky_neural_memory.sqlite3")


def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("""CREATE TABLE IF NOT EXISTS verified_executions (
        workflow_digest TEXT PRIMARY KEY, action_families TEXT NOT NULL,
        result TEXT NOT NULL CHECK(result IN ('completed','failed')),
        verified INTEGER NOT NULL CHECK(verified IN (0,1)),
        observed_at INTEGER NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS explicit_facts (
        fact_id TEXT PRIMARY KEY, owner TEXT NOT NULL, category TEXT NOT NULL,
        ciphertext BLOB NOT NULL, source TEXT NOT NULL,
        created_at INTEGER NOT NULL, modified_at INTEGER NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS neural_owner_idx ON explicit_facts(owner,category)")
    return db


def _key() -> bytes:
    from cryptography.fernet import Fernet
    from metaverse.secrets_v107 import get_secret
    encoded = get_secret("SKY_NEURAL_MEMORY_KEY").strip()
    if not encoded:
        raise RuntimeError("Memoria personal cifrada no habilitada: configurá SKY_NEURAL_MEMORY_KEY.")
    try:
        key = base64.urlsafe_b64decode(encoded.encode("ascii"))
        if len(key) != 32:
            raise ValueError("Invalid length")
        Fernet(encoded.encode("ascii"))
    except (ValueError, UnicodeError, TypeError) as exc:
        raise RuntimeError("SKY_NEURAL_MEMORY_KEY debe ser una clave Fernet de 32 bytes.") from exc
    return encoded.encode("ascii")


def save_fact(owner: str, category: str, text: str, source: str = "owner_confirmed") -> dict:
    from cryptography.fernet import Fernet
    if owner != "owner":
        raise ValueError("Solo puede almacenar memorias el propietario autenticado.")
    if category not in CATEGORIES:
        raise ValueError("Categoría de memoria no autorizada.")
    if not isinstance(text, str) or not 5 <= len(text.strip()) <= 1500:
        raise ValueError("Memoria vacía o demasiado extensa.")
    if source != "owner_confirmed":
        raise ValueError("El origen debe ser el propietario; fuentes externas requieren revisión.")
    token = Fernet(_key()).encrypt(text.strip().encode("utf-8"))
    now = int(time.time())
    ident = "mem_" + uuid.uuid4().hex
    with _LOCK, _connect() as db:
        count = db.execute("SELECT COUNT(*) FROM explicit_facts WHERE owner=?", (owner,)).fetchone()[0]
        if count >= MAX_FACTS:
            raise ValueError("Capacidad máxima de memoria personal; revisá o borrá recuerdos antiguos.")
        db.execute("INSERT INTO explicit_facts VALUES(?,?,?,?,?,?,?)",
                   (ident,owner,category,token,source,now,now))
    return {"id":ident,"category":category,"stored":True,"source":source}


def facts(owner: str = "owner", category: str | None = None) -> list[dict]:
    from cryptography.fernet import Fernet, InvalidToken
    if owner != "owner" or (category and category not in CATEGORIES):
        raise ValueError("Acceso a memoria denegado.")
    cipher = Fernet(_key())
    with _LOCK, _connect() as db:
        rows=db.execute("SELECT * FROM explicit_facts WHERE owner=? ORDER BY modified_at DESC LIMIT ?",
                        (owner, MAX_FACTS)).fetchall()
    records=[]
    for row in rows:
        if category and row["category"] != category: continue
        try: value=cipher.decrypt(row["ciphertext"]).decode("utf-8")
        except InvalidToken:
            records.append({"id":row["fact_id"],"category":row["category"],
                            "status":"undecryptable","source":row["source"]})
            continue
        records.append({"id":row["fact_id"],"category":row["category"],
                        "text":value,"source":row["source"],"modified_at":row["modified_at"]})
    return records


def delete_fact(ident: str, owner: str = "owner") -> bool:
    if owner != "owner" or not re.fullmatch(r"mem_[a-f0-9]{32}", ident):
        return False
    with _LOCK, _connect() as db:
        return bool(db.execute("DELETE FROM explicit_facts WHERE owner=? AND fact_id=?",
                               (owner,ident)).rowcount)


def record_verified_outcome(workflow_id: str, roles: list[str], status: str,
                            *, verified: bool) -> bool:
    """Auto-learn operational stats without copying private tasks or documents.

    Rejected/pending/ambiguous work NEVER becomes an evidence of success.
    """
    if status not in ("completed","failed") or (status == "completed" and not verified):
        return False
    if not isinstance(workflow_id,str) or len(workflow_id)>150:
        return False
    allowed={"planificador","documentalista","diseñador","creador_3d","memoria"}
    role_names=sorted(set(roles))
    if not role_names or any(r not in allowed for r in role_names):
        return False
    digest=hashlib.sha256(workflow_id.encode("utf-8")).hexdigest()
    with _LOCK, _connect() as db:
        db.execute("INSERT OR IGNORE INTO verified_executions VALUES(?,?,?,?,?)",
                   (digest,json.dumps(role_names,ensure_ascii=False),
                    status,int(verified),int(time.time())))
        db.execute("DELETE FROM verified_executions WHERE observed_at<?",
                   (int(time.time())-90*86400,))
        count=db.execute("SELECT COUNT(*) FROM verified_executions").fetchone()[0]
        if count>MAX_OBSERVATIONS:
            db.execute("""DELETE FROM verified_executions WHERE workflow_digest IN
                (SELECT workflow_digest FROM verified_executions ORDER BY observed_at ASC LIMIT ?)""",
                (count-MAX_OBSERVATIONS,))
        return bool(db.execute("SELECT changes()").fetchone()[0])


def execution_report() -> dict:
    """Real measured outcomes by role, no asserted improvements to model weights."""
    with _LOCK,_connect() as db:
        rows=db.execute("SELECT action_families,result,verified FROM verified_executions").fetchall()
    observations=Counter()
    role_counts:dict[str,Counter]={}
    for item in rows:
        observations[item["result"]]+=1
        for role in json.loads(item["action_families"]):
            role_counts.setdefault(role,Counter())[item["result"]]+=1
    return {
        "total_observations":len(rows),
        "completed":observations["completed"],
        "failed":observations["failed"],
        "by_role":{role:{"completed":v["completed"],"failed":v["failed"]}
                   for role,v in role_counts.items()},
        "model_weights_updated":False,
        "privacy":"Only hashed workflow IDs and role outcomes; no private input stored",
    }


def planning_feedback(roles: list[str]) -> dict:
    """Advisory only: never grants tool rights or automatically rewrites prompts."""
    stats=execution_report()["by_role"]
    return {"role_history":{
        role: stats.get(role,{"completed":0,"failed":0}) for role in roles
    },"policy":"Metrics advisory; role permissions never derived from outcomes."}
