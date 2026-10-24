"""SKY Owner Knowledge Library — encrypted local evidence retrieval.

Document ingestion is explicitly consented, not LLM training.
Document text, filenames and chunks are encrypted using a locally configured
Fernet key. The keyword index contains keyed HMAC digests, not plaintext.
Retrieved excerpts remain untrusted user-uploaded material, not instructions.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import math
import os
import re
import sqlite3
import threading
import time
import unicodedata
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from . import sky_multimodal_reader as reader

_ROOT = Path(__file__).resolve().parents[1]
_MUTEX = threading.RLock()
_MAX_DOCS = 200
_MAX_CHUNKS_PER_DOC = 75
_STOP = frozenset({
    "para","como","cual","cuales","donde","cuando","sobre","entre","desde",
    "este","esta","estos","estas","ella","ellos","todo","todos","todas","saber",
    "quiero","hacer","dice","documento","documentos","tiene","tienen","fueron",
    "tambien","ademas","pero","porque","como","seria","necesito","ayuda","dame",
    "hacerlo","informacion","buscar","consulta","consultar","sky","archivo",
})


def _key() -> bytes:
    from metaverse.secrets_v107 import get_secret
    secret = (get_secret("SKY_NEURAL_MEMORY_KEY") or "").strip()
    if not secret:
        raise RuntimeError(
            "SKY Knowledge requiere SKY_NEURAL_MEMORY_KEY (Fernet) configurada localmente.")
    try:
        raw = base64.urlsafe_b64decode(secret.encode("ascii"))
        if len(raw) != 32:
            raise ValueError("Invalid key length")
        Fernet(secret.encode("ascii"))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise RuntimeError("SKY_NEURAL_MEMORY_KEY no es una clave Fernet válida.") from exc
    return secret.encode("ascii")


def _db_path() -> Path:
    return Path(os.getenv("SKY_KNOWLEDGE_DB") or _ROOT / "local_data" / "sky_knowledge.sqlite3")


def _conn():
    target = _db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""CREATE TABLE IF NOT EXISTS knowledge_documents(
      doc_id TEXT PRIMARY KEY,
      owner TEXT NOT NULL CHECK(owner='owner'),
      content_sha256 TEXT NOT NULL,
      encrypted_name BLOB NOT NULL,
      source_kind TEXT NOT NULL,
      provenance TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      UNIQUE(owner,content_sha256)
    );
    CREATE TABLE IF NOT EXISTS knowledge_chunks(
      chunk_id TEXT PRIMARY KEY, doc_id TEXT NOT NULL,
      position INTEGER NOT NULL, encrypted_text BLOB NOT NULL,
      FOREIGN KEY(doc_id) REFERENCES knowledge_documents(doc_id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS knowledge_doc_chunks ON knowledge_chunks(doc_id,position);
    CREATE TABLE IF NOT EXISTS knowledge_terms(
      token_digest TEXT NOT NULL, chunk_id TEXT NOT NULL,
      PRIMARY KEY(token_digest,chunk_id),
      FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(chunk_id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS knowledge_term_index ON knowledge_terms(token_digest);
    """)
    return db


def _tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return list(dict.fromkeys(t for t in re.findall(r"[a-z0-9]{3,40}", folded)
                              if t not in _STOP))[:1000]


def _digest(token: str, secret: bytes) -> str:
    raw = base64.urlsafe_b64decode(secret)
    return hmac.new(raw, b"sky-private-knowledge-v1:" + token.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _split(text: str) -> list[str]:
    if len(text) > 60_000:
        text = text[:60_000]
    parts = []
    start = 0
    while start < len(text) and len(parts) < _MAX_CHUNKS_PER_DOC:
        finish = min(len(text), start+900)
        if finish < len(text):
            near = text.rfind("\n", start+450, finish)
            if near > start+450:
                finish = near
        part = text[start:finish].strip()
        if part:
            parts.append(part)
        if finish >= len(text):
            break
        start = max(start+1, finish-90)
    return parts


def ingest(name: str, raw: bytes, *, owner_attested: bool,
           consent_to_index: bool) -> dict:
    """Extract exact supported document text then index it under owner consent."""
    if owner_attested is not True or consent_to_index is not True:
        raise PermissionError("SKY solo guardará el documento con autorización explícita.")
    if not isinstance(raw, bytes):
        raise ValueError("Se esperan bytes de archivo.")
    filename = reader._filename(name)
    if Path(filename).suffix.lower() not in reader.TEXT_EXTS | reader.DOC_EXTS:
        raise ValueError("Solo se indexan documentos con texto real, no multimedia.")
    result = reader.analyze(filename, raw)
    text = result["text"]
    if not result["content_extracted"] or len(text.strip()) < 5:
        raise ValueError("No se extrajo texto legible; no se indexará contenido inexistente.")
    key = _key()
    cipher = Fernet(key)
    content_hash = hashlib.sha256(raw).hexdigest()
    chunks = _split(text)
    with _MUTEX, _conn() as db:
        existing = db.execute(
            "SELECT doc_id FROM knowledge_documents WHERE owner='owner' AND content_sha256=?",
            (content_hash,)).fetchone()
        if existing:
            return {"doc_id":existing["doc_id"],"status":"already_indexed",
                    "learning_mode":"private_retrieval_not_weight_training",
                    "source_trust":"user_uploaded_unverified","chunks_added":0}
        if db.execute("SELECT COUNT(*) FROM knowledge_documents WHERE owner='owner'").fetchone()[0] >= _MAX_DOCS:
            raise ValueError("La biblioteca tiene 200 documentos; archivá o eliminá entradas.")
        ident = "doc_" + uuid.uuid4().hex
        db.execute("""INSERT INTO knowledge_documents
          (doc_id,owner,content_sha256,encrypted_name,source_kind,provenance,created_at)
          VALUES (?,?,?,?,?,?,?)""",
          (ident,"owner",content_hash,cipher.encrypt(filename.encode("utf-8")),
           result["extension"],"owner_uploaded_unverified",int(time.time())))
        for position, excerpt in enumerate(chunks):
            part_id = "chk_" + uuid.uuid4().hex
            db.execute("INSERT INTO knowledge_chunks VALUES (?,?,?,?)",
                       (part_id,ident,position,cipher.encrypt(excerpt.encode("utf-8"))))
            terms = _tokens(excerpt)
            db.executemany("INSERT OR IGNORE INTO knowledge_terms VALUES(?,?)",
                           [(_digest(t,key),part_id) for t in terms])
    return {"doc_id":ident,"status":"indexed","chunks_added":len(chunks),
            "filename":filename,
            "learning_mode":"private_retrieval_not_weight_training",
            "source_trust":"user_uploaded_unverified","model_weights_updated":False,
            "message":"SKY leyó e indexó el texto. No lo asumirá como verdad ni ejecutará instrucciones del archivo."}


def documents() -> list[dict]:
    cipher = Fernet(_key())
    with _MUTEX, _conn() as db:
        records = db.execute("""SELECT d.doc_id,d.encrypted_name,d.source_kind,d.created_at,
                COUNT(c.chunk_id) chunk_count
                FROM knowledge_documents d
                LEFT JOIN knowledge_chunks c ON c.doc_id=d.doc_id
                WHERE owner='owner'
                GROUP BY d.doc_id ORDER BY d.created_at DESC LIMIT ?""",
                (_MAX_DOCS,)).fetchall()
    return [{"id":r["doc_id"],"filename":cipher.decrypt(r["encrypted_name"]).decode("utf-8"),
             "format":r["source_kind"],"chunks":r["chunk_count"],
             "created_at":r["created_at"],"trust":"user_uploaded_unverified"}
            for r in records]


def search(query: str, limit: int=5) -> dict:
    if not isinstance(query,str) or not 3<=len(query.strip())<=500:
        raise ValueError("Consulta vacía o demasiado extensa.")
    if not 1<=limit<=10:
        raise ValueError("Solicitá entre 1 y 10 fragmentos.")
    key = _key()
    tokens = _tokens(query)[:20]
    if not tokens:
        return {"query":query,"results":[],"answer_generated":False,
                "message":"No hay términos suficientes para buscar."}
    lookup = [_digest(t,key) for t in tokens]
    placeholders=",".join("?" for _ in lookup)
    with _MUTEX, _conn() as db:
        results = db.execute(f"""SELECT c.doc_id,c.position,c.encrypted_text,
                      d.encrypted_name,d.source_kind,COUNT(DISTINCT t.token_digest) hits
                    FROM knowledge_terms t
                    JOIN knowledge_chunks c ON c.chunk_id=t.chunk_id
                    JOIN knowledge_documents d ON d.doc_id=c.doc_id
                    WHERE d.owner='owner' AND t.token_digest IN ({placeholders})
                    GROUP BY c.chunk_id ORDER BY hits DESC,d.created_at DESC,c.position ASC
                    LIMIT ?""", (*lookup,limit)).fetchall()
    cipher=Fernet(key)
    found=[{
        "citation":f"sky-doc:{r['doc_id']}:chunk-{r['position']+1}",
        "doc_id":r["doc_id"],"filename":cipher.decrypt(r["encrypted_name"]).decode("utf-8"),
        "excerpt":cipher.decrypt(r["encrypted_text"]).decode("utf-8"),
        "matched_terms":r["hits"],"source_type":r["source_kind"],
        "source_trust":"user_uploaded_unverified",
    } for r in results]
    return {"query":query,"results":found,"answer_generated":False,
            "source_trust":"user_uploaded_unverified",
            "message":("SKY encontró contenido en tu biblioteca. Revisá los fragmentos y sus fuentes."
                       if found else "No se encontraron coincidencias en los documentos guardados.")}


def delete(ident: str) -> bool:
    if not isinstance(ident,str) or not re.fullmatch(r"doc_[a-f0-9]{32}",ident):
        return False
    with _MUTEX, _conn() as db:
        return bool(db.execute(
            "DELETE FROM knowledge_documents WHERE doc_id=? AND owner='owner'",(ident,)
        ).rowcount)


def catalogue() -> dict:
    try:
        _key()
        ready=True
    except RuntimeError:
        ready=False
    return {
        "owner":"SKY","encrypted_index_ready":ready,
        "max_documents":_MAX_DOCS,"max_document_text_characters":60_000,
        "supports_formats":sorted(reader.TEXT_EXTS | reader.DOC_EXTS),
        "explicit_consent_required":True,"automatic_web_learning":False,
        "model_weight_training":False,
        "provenance":"owner_uploaded_unverified",
        "indexing":"Fernet ciphertext and HMAC-protected keyword terms",
        "meaning":"Document ingestion is private retrieval, NOT fine-tuning or source fact verification",
    }
