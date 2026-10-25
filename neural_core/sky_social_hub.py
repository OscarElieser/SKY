"""SKY Social Hub: cuentas propias, contenido aprobado y aprendizaje medible.

SKY sigue siendo la única API pública del producto. Este módulo usa APIs
oficiales y credenciales OAuth autorizadas por el propietario, guardadas
FUERA de SQLite. NO automatiza seguidores, likes, spam ni mensajes masivos.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib import parse, request

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("x", "facebook", "instagram", "tiktok", "threads", "snapchat")
DIRECT_TEXT = ("x", "facebook", "threads")
VALID_KINDS = ("post", "reply")
MAX_TEXT = {"x": 280, "facebook": 5000, "threads": 500, "instagram": 2200,
            "tiktok": 2200, "snapchat": 2000}
ENV = {
    "x": "SKY_SOCIAL_X_ACCESS_TOKEN",
    "facebook": "SKY_SOCIAL_FACEBOOK_PAGE_TOKEN",
    "threads": "SKY_SOCIAL_THREADS_ACCESS_TOKEN",
}
MAX_DAILY_PER_PLATFORM = 4


class SocialError(ValueError):
    pass


class SocialUnavailable(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db_path() -> Path:
    return Path(os.getenv("SKY_SOCIAL_HUB_DB") or ROOT / "local_data" / "sky_social_hub.sqlite3")


def _db():
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p, timeout=15, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=15000")
    c.executescript("""CREATE TABLE IF NOT EXISTS outbound (
        id TEXT PRIMARY KEY, platform TEXT NOT NULL, kind TEXT NOT NULL,
        body TEXT NOT NULL, target_id TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL, created_at TEXT NOT NULL,
        approved_at TEXT, scheduled_at TEXT, published_at TEXT,
        external_id TEXT, container_id TEXT, error_class TEXT,
        attempts INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_social_queue ON outbound(status,scheduled_at);
    CREATE TABLE IF NOT EXISTS verified_metrics (
        post_id TEXT NOT NULL REFERENCES outbound(id), recorded_at TEXT NOT NULL,
        source TEXT NOT NULL, views INTEGER, likes INTEGER,
        comments INTEGER, shares INTEGER, followers INTEGER,
        PRIMARY KEY(post_id,recorded_at)
    );""")
    return c


def capabilities() -> dict:
    entries = []
    for platform in PLATFORMS:
        ready = bool(os.getenv(ENV.get(platform, ""), "").strip()) if platform in ENV else False
        if platform == "facebook":
            ready = ready and bool(re.fullmatch(r"\d{3,32}", os.getenv("SKY_SOCIAL_FACEBOOK_PAGE_ID", "")))
        entries.append({
            "platform": platform, "account_connected": ready,
            "text_publish_supported": platform in DIRECT_TEXT,
            "replies_supported": platform in ("x", "threads"),
            "media_publish_supported": False,
            "requires_official_app_review_or_account_eligibility": True,
            "mode": "official_api" if platform in DIRECT_TEXT else "draft_only",
        })
    return {"controller": "SKY", "platforms": entries, "publish_requires_owner_approval": True,
            "autolikes": False, "autofollows": False, "bulk_engagement": False,
            "workflow": "draft -> owner-approved -> published or needs-review"}


def _valid_platform(platform: str) -> str:
    if platform not in PLATFORMS:
        raise SocialError("Red social no reconocida.")
    return platform


def _valid_text(platform: str, text: str) -> str:
    if not isinstance(text, str) or not (1 <= len(text.strip()) <= MAX_TEXT[platform]):
        raise SocialError("Texto vacío o demasiado largo para la red social.")
    return text.strip()


def _valid_target(kind: str, platform: str, target_id: str) -> str:
    if kind not in VALID_KINDS:
        raise SocialError("Solo se permiten publicaciones y respuestas de texto.")
    if kind == "reply" and platform not in ("x", "threads"):
        raise SocialError("Las respuestas directas todavía no están conectadas para esta red.")
    if kind == "reply" and not re.fullmatch(r"[A-Za-z0-9_-]{5,100}", target_id or ""):
        raise SocialError("Para responder se requiere el identificador del post autorizado.")
    if kind == "post" and target_id:
        raise SocialError("Un post nuevo no necesita target_id.")
    return target_id


def draft(platform: str, text: str, kind: str = "post", target_id: str = "") -> dict:
    platform = _valid_platform(platform)
    text = _valid_text(platform, text)
    _valid_target(kind, platform, target_id)
    ident = "soc_" + uuid.uuid4().hex
    with _db() as c:
        c.execute("INSERT INTO outbound(id,platform,kind,body,target_id,status,created_at) "
                  "VALUES(?,?,?,?,?,?,?)",
                  (ident, platform, kind, text, target_id, "draft", _now()))
    return get(ident)


def _row(row) -> dict:
    return dict(row) if row else {}


def get(ident: str) -> dict | None:
    if not re.fullmatch(r"soc_[a-f0-9]{32}", ident):
        return None
    with _db() as c:
        row = c.execute("SELECT * FROM outbound WHERE id=?", (ident,)).fetchone()
    return _row(row) if row else None


def list_items(limit: int = 40) -> list[dict]:
    with _db() as c:
        rows = c.execute("SELECT * FROM outbound ORDER BY created_at DESC,id DESC LIMIT ?",
                         (max(1, min(100, int(limit))),)).fetchall()
    return [_row(x) for x in rows]


def approve(ident: str, *, owner_approved: bool, scheduled_at: str | None = None) -> dict:
    if owner_approved is not True:
        raise PermissionError("Solo el propietario puede aprobar la publicación.")
    scheduled = None
    if scheduled_at:
        try:
            dt = datetime.fromisoformat(scheduled_at)
            if dt.tzinfo is None:
                raise ValueError("Falta zona horaria")
            if dt.timestamp() < time.time() - 30:
                raise ValueError("Fecha en el pasado")
            scheduled = dt.astimezone(timezone.utc).isoformat(timespec="seconds")
        except (TypeError, ValueError) as exc:
            raise SocialError("Usá fecha futura ISO 8601 con zona horaria.") from exc
    with _db() as c:
        c.execute("BEGIN IMMEDIATE")
        item = c.execute("SELECT platform,status FROM outbound WHERE id=?", (ident,)).fetchone()
        if not item:
            raise SocialError("Borrador inexistente.")
        if item["status"] != "draft":
            raise SocialError("Solo los borradores se pueden aprobar.")
        if item["platform"] not in DIRECT_TEXT:
            raise SocialUnavailable("Esta red requiere una integración oficial de medios; SKY conserva el borrador.")
        c.execute("UPDATE outbound SET status='approved',approved_at=?,scheduled_at=? WHERE id=?",
                  (_now(), scheduled, ident))
        c.commit()
    return get(ident)


def cancel(ident: str) -> dict:
    with _db() as c:
        c.execute("BEGIN IMMEDIATE")
        result = c.execute("UPDATE outbound SET status='cancelled' WHERE id=? AND status IN ('draft','approved')",
                           (ident,))
        if result.rowcount != 1:
            raise SocialError("La publicación ya está iniciada, enviada o cancelada.")
        c.commit()
    return get(ident)


def _token(platform: str) -> str:
    env = ENV.get(platform)
    token = os.getenv(env or "", "").strip()
    if not token:
        raise SocialUnavailable("Falta autorización oficial de la cuenta " + platform + ".")
    if len(token) < 15 or "\n" in token or "\r" in token:
        raise SocialUnavailable("Token OAuth inválido.")
    return token


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http(url: str, token: str, data: dict) -> dict:
    # Endpoints FIJOS y HTTPS: no URLs de usuario ni redirecciones.
    if not url.startswith(("https://api.x.com/2/tweets",
                           "https://graph.facebook.com/v26.0/",
                           "https://graph.threads.net/v1.0/me/")):
        raise SocialError("Endpoint fuera del catálogo oficial.")
    if url.startswith("https://api.x.com/"):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        content_type = "application/json"
    else:
        raw = parse.urlencode(data).encode("utf-8")
        content_type = "application/x-www-form-urlencoded"
    req = request.Request(url, data=raw, method="POST", headers={
        "Authorization": "Bearer " + token,
        "Content-Type": content_type, "Accept": "application/json",
    })
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    with opener.open(req, timeout=25) as response:
        response_data = response.read(150_001)
    if len(response_data) > 150_000:
        raise SocialUnavailable("La respuesta del proveedor supera el límite permitido.")
    result = json.loads(response_data)
    if not isinstance(result, dict):
        raise SocialUnavailable("Respuesta inválida de la plataforma.")
    # Nunca devolver respuesta de error con datos de OAuth o payload original.
    return result


def _send(item: dict) -> tuple[str, str | None]:
    platform = item["platform"]
    token = _token(platform)
    text = item["body"]
    if platform == "x":
        payload = {"text": text}
        if item["kind"] == "reply":
            payload["reply"] = {"in_reply_to_tweet_id": item["target_id"]}
        reply = _http("https://api.x.com/2/tweets", token, payload)
        ident = (reply.get("data") or {}).get("id")
        if not isinstance(ident, str) or not ident:
            raise SocialUnavailable("X no confirmó el identificador de publicación.")
        return ident, None
    if platform == "facebook":
        if item["kind"] != "post":
            raise SocialUnavailable("Respuestas a comentarios de Facebook aún no integradas.")
        page = os.getenv("SKY_SOCIAL_FACEBOOK_PAGE_ID", "").strip()
        if not re.fullmatch(r"\d{3,32}", page):
            raise SocialUnavailable("Falta el ID de una Página administrada.")
        reply = _http(f"https://graph.facebook.com/v26.0/{page}/feed", token, {"message": text})
        ident = reply.get("id")
        if not isinstance(ident, str) or not ident:
            raise SocialUnavailable("Facebook no confirmó la publicación.")
        return ident, None
    if platform == "threads":
        # Si se creó el contenedor y falla la publicación, se guarda su ID
        # para revisión humana; no se reinicia el flujo de forma automática.
        payload = {"media_type": "TEXT", "text": text}
        if item["kind"] == "reply":
            payload["reply_to_id"] = item["target_id"]
        container = _http("https://graph.threads.net/v1.0/me/threads", token, payload)
        cid = container.get("id")
        if not isinstance(cid, str) or not cid:
            raise SocialUnavailable("Threads no confirmó el contenedor.")
        with _db() as c:
            c.execute("UPDATE outbound SET container_id=? WHERE id=? AND status='sending'",
                      (cid, item["id"]))
        result = _http("https://graph.threads.net/v1.0/me/threads_publish",
                       token, {"creation_id": cid})
        ident = result.get("id")
        if not isinstance(ident, str) or not ident:
            raise SocialUnavailable("Threads no confirmó la publicación.")
        return ident, cid
    raise SocialUnavailable("Esta plataforma aún no tiene adaptador autorizado para publicación.")


def _claim(ident: str | None) -> dict | None:
    """Aprobar no es publicar: solo tomamos un elemento ya autorizado."""
    with _db() as c:
        c.execute("BEGIN IMMEDIATE")
        if ident:
            row = c.execute("SELECT * FROM outbound WHERE id=?", (ident,)).fetchone()
            if not row or row["status"] != "approved":
                c.rollback()
                return None
            if row["scheduled_at"] and row["scheduled_at"] > _now():
                c.rollback()
                return None
        else:
            row = c.execute("SELECT * FROM outbound WHERE status='approved' "
                            "AND (scheduled_at IS NULL OR scheduled_at<=?) "
                            "ORDER BY COALESCE(scheduled_at,approved_at),id LIMIT 1",
                            (_now(),)).fetchone()
            if not row:
                c.rollback()
                return None
        # Limite anti-spam por red: número máximo de publicaciones al día.
        day = datetime.now(timezone.utc).date().isoformat()
        n = c.execute("SELECT COUNT(*) FROM outbound WHERE platform=? AND "
                      "substr(published_at,1,10)=?", (row["platform"], day)).fetchone()[0]
        if n >= MAX_DAILY_PER_PLATFORM:
            c.rollback()
            return None
        c.execute("UPDATE outbound SET status='sending',attempts=attempts+1 "
                  "WHERE id=? AND status='approved'", (row["id"],))
        c.commit()
    return dict(row)


def publish_approved(ident: str | None = None) -> dict | None:
    """One-shot; on ambiguous HTTP error requires review (no blind retries)."""
    item = _claim(ident)
    if not item:
        return None
    started = time.monotonic()
    ok = False
    try:
        external_id, cid = _send(item)
        with _db() as c:
            c.execute("UPDATE outbound SET status='published',published_at=?,external_id=?,"
                      "container_id=COALESCE(container_id,?) WHERE id=? AND status='sending'",
                      (_now(), external_id, cid, item["id"]))
        ok = True
    except Exception as exc:
        # Ni la excepción, ni credenciales, ni contenido original salen en logs.
        with _db() as c:
            c.execute("UPDATE outbound SET status='needs_review',error_class=? "
                      "WHERE id=? AND status='sending'", (type(exc).__name__[:60], item["id"]))
    finally:
        try:
            from .sky_metricas import registrar
            registrar("accion", "social_publish_" + item["platform"], ok,
                      ms=(time.monotonic() - started) * 1000, origen="social")
        except Exception:
            pass
    return get(item["id"])


def worker_tick() -> dict:
    """Procesa como máximo una publicación aprobada por iteración."""
    if os.getenv("SKY_SOCIAL_WORKER_ENABLED", "0") != "1":
        return {"active": False, "processed": 0}
    result = publish_approved()
    return {"active": True, "processed": int(result is not None),
            "status": result["status"] if result else "idle"}


def record_metrics(ident: str, *, views: int | None = None, likes: int | None = None,
                   comments: int | None = None, shares: int | None = None,
                   followers: int | None = None) -> dict:
    values = (views, likes, comments, shares, followers)
    if any(x is not None and (not isinstance(x, int) or isinstance(x, bool) or x < 0 or x > 1_000_000_000)
           for x in values) or all(x is None for x in values):
        raise SocialError("Enviá al menos una métrica numérica válida.")
    post = get(ident)
    if not post or post["status"] != "published":
        raise SocialError("Solo se registran resultados de publicaciones confirmadas.")
    now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    with _db() as c:
        c.execute("INSERT INTO verified_metrics(post_id,recorded_at,source,views,likes,comments,shares,followers) "
                  "VALUES(?,?,?,?,?,?,?,?)", (ident, now, "manual_unverified", *values))
    return {"post_id": ident, "source": "manual_unverified", "recorded_at": now}


def insights() -> dict:
    with _db() as c:
        posts = c.execute("SELECT platform,COUNT(*) AS total FROM outbound "
                          "WHERE status='published' GROUP BY platform").fetchall()
        data = c.execute("""SELECT o.platform, m.views, m.likes, m.comments, m.shares,
                            m.source FROM verified_metrics m JOIN outbound o ON o.id=m.post_id
                            WHERE m.views>0""").fetchall()
    groups = {}
    for r in data:
        platform = r["platform"]
        record = groups.setdefault(platform, {"samples": 0, "engagement_sum": 0.0})
        record["samples"] += 1
        record["engagement_sum"] += 100 * sum(r[k] or 0 for k in ("likes", "comments", "shares")) / r["views"]
    return {
        "confirmed_posts": {r["platform"]: r["total"] for r in posts},
        "sample_engagement": {
            p: {"observations": v["samples"],
                "average_engagement_pct": round(v["engagement_sum"] / v["samples"], 2),
                "sufficient_data": v["samples"] >= 3}
            for p, v in groups.items()},
        "source": "owner_entered_unverified",
        "growth_guaranteed": False,
        "note": "No son métricas extraídas de la red: verificar en el panel oficial antes de tomar decisiones.",
    }
