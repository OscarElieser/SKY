"""SKY Guardian: owner-controlled personal safety, not a police surveillance system.

No direct stream access, facial/biometric recognition, bulk tracking, licence
plate identification, autonomous police calls, or access to private networks.
Registered camera entries are attestations, not grants of technical access.
"""
from __future__ import annotations

import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import os

_MAX_SITES = 12
_MAX_CAMERAS = 64
_MAX_DAYS = 30
_EVENT_TYPES = {
    "camera_offline": "medium",
    "door_open": "medium",
    "smoke_alarm": "critical",
    "water_leak": "high",
    "power_loss": "medium",
    "panic_requested": "critical",
    "movement_on_authorized_property": "low",
}
_SATELLITE_SOURCES = [
    {"name":"Copernicus Browser", "url":"https://dataspace.copernicus.eu/browser/",
     "kind":"open_satellite_imagery", "live_street_video":False,
     "purpose":"Cambios territoriales, inundaciones, vegetación y cobertura del suelo"},
    {"name":"NASA Worldview", "url":"https://worldview.earthdata.nasa.gov/",
     "kind":"earth_observation", "live_street_video":False,
     "purpose":"Imágenes satelitales y fenómenos ambientales observados"},
    {"name":"INETER amenazas", "url":"https://www.ineter.gob.ni/geoportales/vulnerabilidades-amenazas/index.html",
     "kind":"official_public_risk_map", "live_street_video":False,
     "purpose":"Mapas públicos de riesgos y amenazas naturales de Nicaragua"},
    {"name":"SINAPRED", "url":"https://www.sinapred.gob.ni/",
     "kind":"official_public_information", "live_street_video":False,
     "purpose":"Prevención y preparación ante emergencias"},
    {"name":"Policía Nacional", "url":"https://www.policia.gob.ni/",
     "kind":"official_public_information", "live_street_video":False,
     "purpose":"Comunicados públicos e información de Tránsito Nacional"},
]


def _path() -> Path:
    return Path(os.getenv("SKY_GUARDIAN_DB") or Path(__file__).resolve().parents[1] / "local_data" / "sky_guardian.sqlite3")


def _connection():
    path=_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=12)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA busy_timeout=12000")
    conn.execute("""CREATE TABLE IF NOT EXISTS cameras(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, area TEXT NOT NULL,
      permission_basis TEXT NOT NULL CHECK(permission_basis='owner_attested'),
      active INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS incidents(
      id TEXT PRIMARY KEY, event_type TEXT NOT NULL, camera_id TEXT,
      level TEXT NOT NULL, created_at INTEGER NOT NULL,
      source TEXT NOT NULL CHECK(source='owner_manual'),
      acknowledged_at INTEGER,
      FOREIGN KEY(camera_id) REFERENCES cameras(id)
    )""")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _clean(value: str,max_length: int) -> str:
    if not isinstance(value,str) or not (2<=len(value.strip())<=max_length):
        raise ValueError("Datos incompletos o demasiado extensos.")
    cleaned=" ".join(value.split())
    if any(ord(c)<32 for c in cleaned):
        raise ValueError("Datos no permitidos.")
    return cleaned


def register_camera(name: str, area: str, *, owner_attested: bool) -> dict:
    """Owner-attested inventory only. No URL, credentials or stream access."""
    if owner_attested is not True:
        raise PermissionError("Es obligatorio declarar autorización legítima de la cámara.")
    name=_clean(name,80)
    area=_clean(area,80)
    with _connection() as db:
        if db.execute("SELECT COUNT(*) FROM cameras").fetchone()[0]>=_MAX_CAMERAS:
            raise ValueError("Inventario de cámaras lleno.")
        ident="cam_"+uuid.uuid4().hex[:24]
        db.execute("INSERT INTO cameras VALUES(?,?,?,?,?,?)",
                   (ident,name,area,"owner_attested",0,int(time.time())))
    return {"id":ident,"name":name,"area":area,"authorized":True,
            "connection_status":"not_connected",
            "live_video_enabled":False,
            "biometric_identification_enabled":False}


def cameras() -> list[dict]:
    with _connection() as db:
        entries=db.execute("SELECT id,name,area,permission_basis,active FROM cameras ORDER BY created_at DESC LIMIT 64").fetchall()
    return [{"id":x["id"],"name":x["name"],"area":x["area"],
             "authorized":x["permission_basis"]=="owner_attested",
             "connection_status":"not_connected","live_video_enabled":False}
            for x in entries]


def remove_camera(ident: str) -> bool:
    if not re.fullmatch(r"cam_[a-f0-9]{24}",ident):return False
    with _connection() as db:
        # Keep incident history with camera_id null, not tied to equipment any more.
        db.execute("UPDATE incidents SET camera_id=NULL WHERE camera_id=?",(ident,))
        return bool(db.execute("DELETE FROM cameras WHERE id=?",(ident,)).rowcount)


def report_event(event_type: str, camera_id: str | None = None) -> dict:
    """Manually registered observation is NOT proof of a crime or event."""
    if event_type not in _EVENT_TYPES:
        raise ValueError("Tipo de aviso no permitido.")
    if camera_id is not None and not re.fullmatch(r"cam_[a-f0-9]{24}",camera_id):
        raise ValueError("Cámara no válida.")
    with _connection() as db:
        if camera_id and not db.execute("SELECT 1 FROM cameras WHERE id=?",(camera_id,)).fetchone():
            raise ValueError("La cámara no está autorizada o registrada.")
        now=int(time.time())
        db.execute("DELETE FROM incidents WHERE created_at<?",(now-_MAX_DAYS*86400,))
        ident="inc_"+uuid.uuid4().hex[:24]
        db.execute("INSERT INTO incidents VALUES(?,?,?,?,?,?,NULL)",
                   (ident,event_type,camera_id,_EVENT_TYPES[event_type],now,"owner_manual"))
    return {"id":ident,"event_type":event_type,"severity":_EVENT_TYPES[event_type],
            "observation":"owner_reported_unverified", "alert_dispatched":False,
            "police_contacted":False, "requires_human_review":True,
            "guidance":"En una emergencia real, buscá un lugar seguro y contactá los servicios locales por los canales oficiales."}


def recent_events() -> list[dict]:
    with _connection() as db:
        cutoff=int(time.time())-_MAX_DAYS*86400
        db.execute("DELETE FROM incidents WHERE created_at<?",(cutoff,))
        entries=db.execute("""SELECT id,event_type,camera_id,level,created_at,source,acknowledged_at
                               FROM incidents ORDER BY created_at DESC LIMIT 100""").fetchall()
    return [dict(x) for x in entries]


def acknowledge(ident: str) -> bool:
    if not re.fullmatch(r"inc_[a-f0-9]{24}",ident):return False
    with _connection() as db:
        return bool(db.execute("UPDATE incidents SET acknowledged_at=? WHERE id=? AND acknowledged_at IS NULL",
                               (int(time.time()),ident)).rowcount)


def catalogue() -> dict:
    return {
        "product":"SKY GUARDIAN", "owner":"SKY CORE",
        "mode":"owner_consented_property_and_public_information",
        "camera_registry_ready":True, "camera_streaming_ready":False,
        "authorized_feed_connector_ready":False,
        "public_satellite_sources_ready":True,
        "satellite_imagery_download_ready":False,
        "police_or_traffic_system_access":False,
        "auto_report_to_authorities":False,
        "face_or_person_identification":False,
        "person_tracking":False,
        "automated_enforcement":False,
        "event_types":list(_EVENT_TYPES),
        "incident_retention_days":_MAX_DAYS,
        "satellite_sources":list(_SATELLITE_SOURCES),
        "notice":"Solo fuentes públicas y cámaras propias/autorizadas. No reemplaza emergencias ni vigilancia profesional.",
    }
