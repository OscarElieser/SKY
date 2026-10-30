"""Enrutamiento verificable de SKY: un rol, una herramienta, sin permisos nuevos."""
import re
import unicodedata
from . import sky_verified_roles as execution
from . import sky_role_lessons as memory

class RoutingError(ValueError): pass

DOMAINS=(
 ("fisica","mecanica_si",("fuerza","newton","energia cinetica")),
 ("quimica","masa_molar",("masa molar","formula quimica")),
 ("educacion","evaluar_rubrica",("rubrica","evaluacion por criterios")),
 ("datos","resumen",("promedio","mediana","estadistica")),
 ("programacion","sintaxis_python",("sintaxis python","sintaxis de python")),
 ("ciberseguridad","auditoria_python",("audita el codigo","auditar codigo")),
 ("investigacion","semantic_scholar",("semantic scholar","publicaciones academicas")),
)
def _normalize(task):
    if not isinstance(task,str) or not 3<=len(task.strip())<=500:
        raise RoutingError("Solicitud inválida (3-500 caracteres).")
    val=unicodedata.normalize("NFKD",task.casefold())
    return " ".join(re.sub(r"[^a-z0-9 ]"," ","".join(ch for ch in val if not unicodedata.combining(ch))).split())

def _select(task):
    s=_normalize(task)
    matches=[(role,tool) for role,tool,terms in DOMAINS if any(
        re.search(r"\b"+re.escape(term)+r"\b",s) for term in terms)]
    if len(matches)>1:return None,"ambiguous"
    if matches:return matches[0],"specific_domain"
    if any(re.search(r"\b"+re.escape(t)+r"\b",s) for t in (
        "calcula","cuanto es","aritmetica","expresion matematica")):
        return ("matematicas","calcular"),"explicit_arithmetic"
    return None,"unknown"

def _quality(role,tool,data=None):
    try:
        allrows=memory.report()["tools"] if data is None else data
    except (OSError,ValueError):
        allrows=[]
    row=next((x for x in allrows if x["role"]==role and x["tool"]==tool),{})
    verified=int(row.get("verified",0))
    failed=int(row.get("failed",0))
    n=verified+failed
    return {"sample_count":n,"verified":verified,"failed":failed,
            "external_unverified":int(row.get("unverified_external",0)),
            "local_pass_rate":round(verified/n,3) if n else None,
            "requires_review":n>=5 and failed/n>0.5,
            "not_device_certification":True}

def recommend(task,allow_network=False):
    if type(allow_network) is not bool:raise RoutingError("Permiso inválido.")
    pair,reason=_select(task)
    if pair is None:return {"status":"NOT_ROUTED","reason":reason,"executed":False}
    role,tool=pair
    if tool not in execution.TOOLS.get(role,()):
        return {"status":"NOT_ROUTED","reason":"unavailable","executed":False}
    return {"status":"RECOMMENDED","role":role,"tool":tool,"reason":reason,
            "quality":_quality(role,tool),"needs_network_consent":role=="investigacion",
            "network_allowed":role=="investigacion" and allow_network,
            "executed":False,"auto_approved":False}

def dispatch(task,args,allow_network=False):
    if not isinstance(args,dict):raise RoutingError("Argumentos inválidos.")
    plan=recommend(task,allow_network=allow_network)
    if plan["status"]!="RECOMMENDED":
        return {"status":"NOT_ROUTED","selection":plan,"executed":False}
    if plan["quality"]["requires_review"]:
        return {"status":"REQUIRES_REVIEW","selection":plan,"executed":False}
    result=execution.run_plan([{"id":"router1","role":plan["role"],
                               "tool":plan["tool"],"args":args}],
                              allow_network=allow_network)
    return {"status":result["status"],"selection":plan,"execution":result,
            "executed":True,"external_device_actions":False}

def dashboard():
    try:info=memory.report();available=True
    except (OSError,ValueError):
        info={"tools":[],"total_observations":0};available=False
    rows=[{"role":role,"tool":tool,"quality":_quality(role,tool,info["tools"])}
          for role,tools in sorted(execution.TOOLS.items()) for tool in tools]
    return {"registered_tools":len(rows),"observations":info["total_observations"],
            "history_available":available,"tools":rows,
            "physical_device_verified":False,"model_weights_updated":False}
