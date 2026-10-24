"""SKY Agent Supervisor — orchestration using the REAL SKY Workflows executor.

The supervisor plans and delegates automatically to existing, capability-bounded
roles; it never auto-approves, simulates research, executes shell commands, or
claims that a step completed before the workflow engine reports evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import sky_workflows as wf

ROOT = Path(__file__).resolve().parents[1]
FORMAT_ALLOWLIST = frozenset({"md", "docx", "pdf", "pptx", "xlsx", "csv", "html"})
MAX_STEPS = 8


def db_path() -> Path:
    return Path(os.environ.get("SKY_SUPERVISOR_DB") or ROOT / "local_data" / "sky_supervisor.sqlite3")


def connect():
    target = db_path()
    target.parent.mkdir(exist_ok=True, parents=True)
    conn = sqlite3.connect(target, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("""CREATE TABLE IF NOT EXISTS supervisor_jobs (
        workflow_id TEXT PRIMARY KEY,
        plan_digest TEXT NOT NULL,
        roles TEXT NOT NULL,
        created_at TEXT NOT NULL,
        idempotency_key TEXT UNIQUE
    )""")
    return conn


def _norm(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _match(normalized: str, *patterns: str) -> bool:
    return any(re.search(pattern, normalized) is not None for pattern in patterns)


def analyze_request(request: str, source_text: str = "", document_format: str = "auto",
                    project_id: str | None = None) -> dict[str, Any]:
    """Deterministic planning with real capability constraints and handoffs.

    For factual research requests or missing source material, it returns an
    explicit blocker. No generated article is passed off as verified research.
    """
    if not isinstance(request, str) or not 8 <= len(request.strip()) <= 3000:
        raise ValueError("La solicitud debe contener entre 8 y 3000 caracteres.")
    if not isinstance(source_text, str) or len(source_text) > 12000:
        raise ValueError("El texto de referencia debe ser menor o igual a 12000 caracteres.")
    if document_format not in FORMAT_ALLOWLIST | {"auto"}:
        raise ValueError("Formato de documento no permitido.")
    if project_id is not None and (not isinstance(project_id, str) or len(project_id) > 120):
        raise ValueError("Identificador de proyecto inválido.")

    original = request.strip()
    normalized = _norm(original)
    source = source_text.strip()
    if document_format == "auto":
        if _match(normalized, r"\b(pptx|powerpoint|presentacion|diapositivas)\b"):
            document_format = "pptx"
        elif _match(normalized, r"\b(excel|hoja de calculo|xlsx)\b"):
            document_format = "xlsx"
        elif _match(normalized, r"\bpdf\b"):
            document_format = "pdf"
        else:
            document_format = "docx"
    wants_research = _match(normalized, r"\binvestig", r"\bbusca (?:en )?internet\b",
                            r"\bfuentes?\b", r"\binformacion (?:actual|verificada)\b")
    wants_document = _match(normalized, r"\b(informe|documento|word|pdf|pptx|powerpoint|presentacion|reporte|excel|hoja de calculo)\b")
    wants_design = _match(normalized, r"\b(disen[oa]?|disena|interfaz|pagina web visual|prototipo visual)\b")
    wants_world = _match(normalized, r"\b(3d|mundo virtual|escena tridimensional)\b")
    wants_memory = _match(normalized, r"\b(guardar? (?:nota|memoria|recordatorio)|recuerda esto|memoriza)\b")

    requested = []
    if wants_research: requested.append("research")
    if wants_document: requested.append("document")
    if wants_design: requested.append("experience")
    if wants_world: requested.append("world")
    if wants_memory: requested.append("memory")
    if not requested:
        requested = ["plan"]

    blockers: list[dict[str, str]] = []
    if wants_research:
        blockers.append({
            "capability": "research",
            "reason": ("SKY Workflows todavía no dispone de un ejecutor de investigación web "
                       "con verificación de fuentes; no se presentará un plan como investigación."),
        })
    if wants_document and not source:
        blockers.append({
            "capability": "document",
            "reason": "Necesito texto o datos de referencia para crear un documento real.",
        })
    if wants_document and document_format in ("xlsx", "csv") and source and "," not in source and ";" not in source:
        blockers.append({
            "capability": "document",
            "reason": "Para Excel/CSV se necesitan datos tabulares (CSV) de entrada.",
        })
    if wants_memory and not source:
        blockers.append({
            "capability": "memory",
            "reason": "Para guardar memoria hace falta el contenido explícito a conservar.",
        })
    if _match(normalized,
              r"\b(?:shell|powershell|cmd|terminal|comando(?:s)? de sistema)\\b",
              r"\b(?:borra|elimina|destruye|formatea|wipe)\\b",
              r"\b(?:paga|comprar|compra|transfiere dinero|transferir dinero)\\b",
              r"\b(?:publica|publicar|despliega|deploy)\\b"):
        blockers.append({
            "capability": "system_external_effects",
            "reason": ("Este supervisor no autoriza pagos, borrados, terminales ni "
                       "publicaciones. SKY necesita una herramienta específica y autorización."),
        })

    steps: list[dict] = [{
        "agent": "planificador",
        "action": "plan",
        "task": f"Organizar la solicitud bajo supervisión de SKY: {original}"[:3000],
        "params": {},
    }]

    if wants_document and source:
        title = re.sub(r"[\r\n]+", " ", original).strip()[:100]
        spec: dict[str, Any] = {"kind": document_format, "title": title}
        if document_format in ("xlsx", "csv"):
            spec["csv"] = source
        else:
            spec["content"] = source
        steps.append({
            "agent": "documentalista",
            "action": "document",
            "task": (f"Generar documento {document_format.upper()} con contenido aportado por el propietario: {title}. "
                     "Usar estructura planificada en {{step.1.plan_summary}}")[:3000],
            "params": {"document": spec},
        })
    if wants_design:
        steps.append({
            "agent": "diseñador", "action": "experience",
            "task": (f"Preparar experiencia visual solicitada por el propietario: {original}. "
                     "Tomar como contexto {{step.1.plan_summary}}")[:3000],
            "params": {"title": original[:90]},
        })
    if wants_world:
        steps.append({
            "agent": "creador_3d", "action": "world",
            "task": (f"Preparar mundo 3D solicitado por el propietario: {original}. "
                     "Tomar como contexto {{step.1.plan_summary}}")[:3000],
            "params": {"name": original[:60], "prompt": original[:950]},
        })
    if wants_memory and source:
        steps.append({
            "agent": "memoria", "action": "memory",
            "task": f"Guardar nota indicada expresamente por el propietario: {original}"[:3000],
            "params": {"label": original[:80], "content": source[:3000]},
        })
    if len(steps) > MAX_STEPS:
        raise ValueError("Demasiadas etapas para el supervisor.")
    validated = [wf._valid_step(step) for step in steps]
    wf._validate_tokens(validated, project_id)

    # Do not offer partial work as if it satisfied a blocked request.
    return {
        "central_agent": "SKY",
        "request": original,
        "requested_capabilities": requested,
        "assigned_roles": list(dict.fromkeys(step["agent"] for step in validated)),
        "steps": validated,
        "blockers": blockers,
        "ready_to_prepare": not blockers,
        "requires_owner_approval": True,
        "runs_automatically_after_approval": True,
        "executes_now": False,
        "planning_mode": "deterministic_with_capability_checks",
        "verified_research_performed": False,
        "message": ("SKY diseñó el plan; necesita información o una integración antes de continuar."
                    if blockers else "SKY distribuyó el trabajo. Falta tu aprobación para ejecutarlo."),
    }


def _digest(plan: dict) -> str:
    payload = {"request": plan["request"], "steps": plan["steps"]}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def prepare(request: str, source_text: str = "", document_format: str = "auto",
            project_id: str | None = None, request_id: str | None = None) -> dict:
    """Create persistent, UNAPPROVED workflow; optional idempotency prevents retries."""
    plan = analyze_request(request, source_text, document_format, project_id)
    if plan["blockers"]:
        return {**plan, "status": "needs_input", "workflow_id": None}
    if request_id is not None and (
        not isinstance(request_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{8,100}", request_id)
    ):
        raise ValueError("Identificador de solicitud no válido.")
    digest = _digest(plan)
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        if request_id:
            record = con.execute(
                "SELECT workflow_id,plan_digest FROM supervisor_jobs WHERE idempotency_key=?",
                (request_id,)
            ).fetchone()
            if record:
                if record["plan_digest"] != digest:
                    raise RuntimeError("Este identificador ya corresponde a otra solicitud.")
                flow = wf.get(record["workflow_id"])
                if not flow:
                    raise RuntimeError("El historial del supervisor requiere revisión manual.")
                con.commit()
                return {**plan, "status": flow["status"], "workflow_id": flow["id"],
                        "preview_url": f'/api/sky/workflows/{flow["id"]}/preview',
                        "duplicate_prevented": True}
        workflow = wf.create(
            f"SKY Supervisor: {plan['request'][:90]}"[:120],
            plan["steps"], project_id=project_id, max_attempts=2,
        )
        con.execute("""INSERT INTO supervisor_jobs(workflow_id,plan_digest,roles,created_at,idempotency_key)
                       VALUES(?,?,?,?,?)""", (
            workflow["id"], digest,
            json.dumps(plan["assigned_roles"], ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(timespec="seconds"), request_id,
        ))
        con.commit()
    return {
        **plan,
        "status": workflow["status"],
        "workflow_id": workflow["id"],
        "preview_url": f'/api/sky/workflows/{workflow["id"]}/preview',
        "duplicate_prevented": False,
    }


def get_job(workflow_id: str) -> dict:
    """Aggregate actual outcomes; a pending/failed step is never a deliverable."""
    with connect() as con:
        record = con.execute("SELECT roles,created_at FROM supervisor_jobs WHERE workflow_id=?",
                             (workflow_id,)).fetchone()
    if not record:
        raise KeyError("Solicitud supervisada no encontrada.")
    flow = wf.get(workflow_id)
    if flow is None:
        raise RuntimeError("El flujo fue retirado y requiere revisión manual.")
    finished = []
    for entry in flow["results"]:
        if entry.get("run") != flow["run_number"]:
            continue
        result = entry.get("result") or {}
        index = entry.get("step", 0)
        if not (1 <= index <= len(flow["steps"])):
            continue
        role = flow["steps"][index-1]["agent"]
        finished.append({
            "step": index, "role": role, "action": entry.get("action"),
            "item_id": entry.get("item_id"),
            "verified": True, "result": result,
        })
    status = flow["status"]
    total = len(flow["steps"])
    completed = len(finished)
    if status == "completed" and completed != total:
        status = "needs_review"
    return {
        "central_agent": "SKY",
        "workflow_id": workflow_id,
        "status": status,
        "assigned_roles": json.loads(record["roles"]),
        "completed_steps": completed,
        "total_steps": total,
        "percent_complete": round(100 * completed / total) if total else 0,
        "results": finished,
        "last_error": flow["last_error"],
        "awaits_owner_approval": status == "awaiting_approval",
        "verified_complete": status == "completed" and completed == total,
        "message": ("SKY verificó todos los pasos del flujo."
                    if status == "completed" and completed == total
                    else "SKY mantiene la solicitud en seguimiento; aún no está completamente verificada."),
    }


def catalogue() -> dict:
    return {
        "manager": "SKY Agent Supervisor",
        "central_agent": "SKY",
        "supported_roles": list(wf.ROLE_ACTION),
        "maximum_steps": MAX_STEPS,
        "requires_owner_approval": True,
        "model_creates_tools": False,
        "remote_research": False,
        "scheduler": "existing SKY workflows service",
        "note": "El supervisor planifica y delega a herramientas ya instaladas; no crea nuevos privilegios.",
    }
