"""SKY: ejecutores de roles reales, de solo lectura y con evidencia limitada.

No ejecuta Python suministrado, no actúa en dispositivos ni concede permisos
a modelos. La investigación remota se etiqueta como no verificada.
"""
from __future__ import annotations
import ast
import hashlib
import json
import math
import operator
import os
import sqlite3
import statistics
import time
import uuid
from pathlib import Path
from . import sky_verified_science as _science
from . import sky_role_lessons as _lessons

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    "matematicas": ("calcular",),
    "datos": ("resumen",),
    "programacion": ("sintaxis_python",),
    "ciberseguridad": ("auditoria_python",),
    "investigacion": ("semantic_scholar",),
    "fisica": ("mecanica_si",),
    "quimica": ("masa_molar",),
    "educacion": ("evaluar_rubrica",),
}
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
       ast.Mod: operator.mod, ast.Pow: operator.pow}

class RoleError(ValueError):
    pass

def _number(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1e12:
        raise RoleError("Número inválido o fuera de rango.")
    return v

def _arithmetic(node, variables):
    if isinstance(node, ast.Expression):
        return _arithmetic(node.body, variables)
    if isinstance(node, ast.Constant):
        return _number(node.value)
    if isinstance(node, ast.Name) and node.id in variables:
        return _number(variables[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _arithmetic(node.operand, variables)
        return _number(-v if isinstance(node.op, ast.USub) else v)
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        left, right = _arithmetic(node.left, variables), _arithmetic(node.right, variables)
        if isinstance(node.op, ast.Pow) and (abs(left) > 1e6 or abs(right) > 8):
            raise RoleError("Potencia fuera de límites.")
        try:
            return _number(OPS[type(node.op)](left, right))
        except (ArithmeticError, ValueError) as exc:
            raise RoleError("Operación matemática inválida.") from exc
    raise RoleError("Expresión no permitida (sin ejecución de código).")

def _calculate(args, prev):
    expr = args.get("expression")
    if not isinstance(expr, str) or not 1 <= len(expr) <= 140:
        raise RoleError("Expresión inválida.")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise RoleError("Sintaxis matemática inválida.") from exc
    if sum(1 for _ in ast.walk(tree)) > 36:
        raise RoleError("Expresión demasiado compleja.")
    variables = {k: _number(v) for k,v in (prev or {}).items()
                 if k.isidentifier() and isinstance(v, (int, float)) and not isinstance(v, bool)}
    answer = _arithmetic(tree, variables)
    if _arithmetic(tree, variables) != answer:
        raise RoleError("Falló la segunda comprobación.")
    return {"value": answer, "scope": "aritmetica_limitada", "check": "ast_double_execution"}

def _summary(args, prev):
    vals = args.get("values")
    if not isinstance(vals, list) or not 1 <= len(vals) <= 1000:
        raise RoleError("Se requieren 1 a 1000 datos.")
    nums = [_number(v) for v in vals]
    mean = statistics.fmean(nums)
    if not math.isclose(mean, sum(nums)/len(nums), rel_tol=1e-10, abs_tol=1e-10):
        raise RoleError("Inconsistencia estadística.")
    return {"count": len(nums), "mean": mean, "median": statistics.median(nums),
            "minimum": min(nums), "maximum": max(nums), "scope": "estadistica_descriptiva"}

def _parse_source(args):
    source = args.get("source")
    if not isinstance(source, str) or not 1 <= len(source) <= 12000:
        raise RoleError("Código Python inválido.")
    try:
        return ast.parse(source)
    except SyntaxError as exc:
        raise RoleError("Error sintáctico en línea " + str(exc.lineno)) from exc

def _syntax(args, prev):
    tree = _parse_source(args)
    return {"syntax_valid": True, "functions": [
        n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ][:50], "scope": "sintaxis_sin_ejecucion"}

def _audit(args, prev):
    tree = _parse_source(args)
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else (
            f.value.id + "." + f.attr if isinstance(f, ast.Attribute)
            and isinstance(f.value, ast.Name) else "")
        if name in ("eval", "exec", "os.system", "os.popen", "pickle.loads", "subprocess.Popen"):
            findings.append({"line": node.lineno, "rule": "risky_call", "symbol": name})
        if name in ("subprocess.run", "subprocess.call", "subprocess.check_output") and any(
            kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords):
            findings.append({"line": node.lineno, "rule": "shell_true", "symbol": name})
    return {"findings": findings[:100], "code_executed": False,
            "scope": "auditoria_estatica_parcial_no_certifica_seguridad"}

def _research(args, allow_network):
    if not allow_network:
        raise PermissionError("Consulta externa sin autorización explícita.")
    q = args.get("query")
    if not isinstance(q, str) or not 3 <= len(q.strip()) <= 220:
        raise RoleError("Consulta académica inválida.")
    from .sky_research_connectors import semantic_scholar
    response = semantic_scholar(q.strip(), limit=5)
    if not isinstance(response, dict) or not isinstance(response.get("items"), list):
        raise RoleError("Respuesta académica inválida.")
    items = [{"title": str(x.get("title") or "")[:240],
              "year": x.get("year"), "doi": str(x.get("doi") or "")[:140],
              "url": str(x.get("url") or "")[:350]}
             for x in response["items"][:5] if isinstance(x, dict)]
    return {"items": items, "source": "Semantic Scholar", "scope": "fuentes_no_verificadas"}

EXECUTORS = {
    ("matematicas", "calcular"): _calculate,
    ("datos", "resumen"): _summary,
    ("programacion", "sintaxis_python"): _syntax,
    ("ciberseguridad", "auditoria_python"): _audit,
    ("fisica", "mecanica_si"): _science.mecanica_si,
    ("quimica", "masa_molar"): _science.masa_molar,
    ("educacion", "evaluar_rubrica"): _science.evaluar_rubrica,
}

def catalogue():
    from .sky_roles import ROLES
    return {"engine": "sky-verified-roles-v1", "max_steps": 6,
            "roles": [{"id": k, "tools": list(TOOLS.get(k, ())),
                       "execution": "read_only_tools" if k in TOOLS else "catalogue_only"}
                      for k in sorted(set(ROLES) | set(TOOLS))],
            "cannot_execute_device_actions": True, "model_weights_updated": False}

def _db():
    path = Path(os.getenv("SKY_VERIFIED_ROLES_DB") or ROOT / "local_data" / "sky_verified_roles.sqlite3")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=8)
    conn.execute("""CREATE TABLE IF NOT EXISTS role_outcomes(
        id TEXT PRIMARY KEY, role TEXT, tool TEXT, outcome TEXT, elapsed_ms INTEGER, time_utc INTEGER)""")
    return conn

def _remember(role, tool, status, elapsed):
    try:
        with _db() as db:
            db.execute("INSERT INTO role_outcomes VALUES (?,?,?,?,?,?)",
                       (hashlib.sha256(uuid.uuid4().bytes).hexdigest(), role, tool,
                        status, elapsed, int(time.time())))
            db.execute("""DELETE FROM role_outcomes WHERE id IN (
                SELECT id FROM role_outcomes ORDER BY time_utc DESC LIMIT -1 OFFSET 1000)""")
        return True
    except (sqlite3.Error, OSError):
        return False

def metrics():
    with _db() as db:
        rows = db.execute("SELECT role,tool,outcome,COUNT(*) FROM role_outcomes GROUP BY 1,2,3").fetchall()
    return {"events": [{"role": a, "tool": b, "outcome": c, "count": d} for a,b,c,d in rows],
            "stores_user_prompts": False, "model_weights_updated": False}

def run_plan(steps, *, allow_network=False):
    """Plan estructurado de hasta 6 pasos; sus dependencias reciben solo datos verificados."""
    if not isinstance(steps, list) or not 1 <= len(steps) <= 6 or type(allow_network) is not bool:
        raise RoleError("Plan o permiso inválido.")
    seen = set()
    for s in steps:
        if not isinstance(s, dict) or set(s) - {"id", "role", "tool", "args", "depends_on"}:
            raise RoleError("Paso no autorizado.")
        ident, role, tool = s.get("id"), s.get("role"), s.get("tool")
        if not isinstance(ident, str) or not ident.isidentifier() or len(ident) > 30 or ident in seen:
            raise RoleError("ID duplicado o inválido.")
        if not isinstance(role, str) or not isinstance(tool, str) or tool not in TOOLS.get(role, ()):
            raise RoleError("El rol no dispone de esta herramienta real.")
        if not isinstance(s.get("args"), dict):
            raise RoleError("Argumentos no estructurados.")
        try:
            encoded = json.dumps(s["args"], ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise RoleError("Argumentos no JSON o no finitos.") from exc
        if len(encoded) > 24000 or (s.get("depends_on") is not None and s["depends_on"] not in seen):
            raise RoleError("Argumentos excesivos o dependencia no resuelta.")
        seen.add(ident)
    results, states = [], {}
    for s in steps:
        role, tool = s["role"], s["tool"]
        start = time.monotonic()
        attempts = 0
        verification = None
        failure_kind = "none"
        try:
            prior_lesson = _lessons.lesson(role, tool)
        except (OSError, sqlite3.Error, ValueError):
            prior_lesson = None
        try:
            if role == "investigacion":
                attempts = 1
                data = _research(s["args"], allow_network)
                status = "RETRIEVED_UNVERIFIED"
            else:
                # Auto-reparación restringida: una sola repetición de operación
                # pura cuando un revisor encuentra resultados inconsistentes.
                # Nunca modifica código, archivos ni dispositivos.
                for attempts in (1, 2):
                    data = EXECUTORS[(role, tool)](s["args"], states.get(s.get("depends_on")))
                    verification = _science.review(role, tool, s["args"], data)
                    if verification["passed"]:
                        break
                else:
                    raise RoleError("El resultado no pasó el control tras dos intentos.")
                status = "VERIFIED_LIMITED_SCOPE"
            states[s["id"]] = data if status == "VERIFIED_LIMITED_SCOPE" else {}
            item = {"id": s["id"], "role": role, "tool": tool, "status": status, "result": data}
        except (RoleError, PermissionError, RuntimeError, ArithmeticError,
                ImportError, OSError, ValueError) as exc:
            if verification is not None and not verification.get("passed", False):
                failure_kind = "verification_mismatch"
            elif isinstance(exc, PermissionError):
                failure_kind = "permission_required"
            elif isinstance(exc, (ImportError, OSError)):
                failure_kind = "dependency_unavailable"
            elif isinstance(exc, (RoleError, ValueError, ArithmeticError)):
                failure_kind = "invalid_input"
            else:
                failure_kind = "execution_failed"
            item = {"id": s["id"], "role": role, "tool": tool, "status": "FAILED",
                    "error": str(exc)[:200]}
        item["attempts"] = attempts
        if verification is not None:
            item["review"] = verification
            item["correction"] = "repeated_after_mismatch" if attempts == 2 else "not_needed"
        item["duration_ms"] = max(0, round((time.monotonic() - start)*1000))
        item["prior_lesson"] = prior_lesson
        item["issue_category"] = failure_kind
        item["memory_recorded"] = _remember(role, tool, item["status"], item["duration_ms"])
        try:
            item["lesson_recorded"] = _lessons.record(
                role, tool, item["status"], issue=failure_kind,
                attempts=attempts, duration_ms=min(item["duration_ms"], 3_600_000))
        except (OSError, sqlite3.Error, ValueError):
            item["lesson_recorded"] = False
        results.append(item)
        if item["status"] == "FAILED":
            break
    status = "FAILED" if results[-1]["status"] == "FAILED" else (
        "REQUIRES_SOURCE_VERIFICATION" if any(x["status"] == "RETRIEVED_UNVERIFIED" for x in results)
        else "VERIFIED_LIMITED_SCOPE")
    return {"status": status, "completed_steps": len(results), "requested_steps": len(steps),
            "steps": results, "external_device_actions": False, "model_weights_updated": False}
