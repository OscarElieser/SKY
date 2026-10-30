"""Puente real entre conversación y herramientas matemático-científicas de SKY.

Sólo interpreta patrones cerrados con argumentos completos. No usa LLM para
inventar parámetros, no abre archivos, no navega, no envía datos ni toca equipos.
Una frase que no coincida retorna None y sigue el cerebro habitual.
"""
from __future__ import annotations

import re
import unicodedata
from . import sky_role_router as routing

MAX_MESSAGE = 4000
_NUM = r"-?(?:\d{1,10}(?:\.\d{1,8})?|\.\d{1,8})"


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _clean(raw: str) -> str:
    value = re.sub(r"^\s*(?:(?:oye|hey|ok)\s+)?sky[\s,.:;!¡-]*", "", raw, flags=re.I).strip()
    return value.strip(" \n\t¿?¡!")


def _decimal(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Salida numérica no verificable.")
    return format(value, ".10g")


def _arithmetic(text: str):
    flat = _fold(text)
    match = re.fullmatch(
        r"(?:cuanto es|calcula|calcular|resuelve|resolvi|resultado de|cuanto da|opera)\s+(.+)",
        flat, flags=re.S
    )
    if not match:
        return None
    expr = match.group(1).strip().rstrip("?!. ")
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")
    if not 1 <= len(expr) <= 130:
        return None
    # Rechaza texto natural o referencias a variables: exclusivamente aritmética.
    if not re.fullmatch(r"[0-9.\s()+*/%-]+", expr) or not re.search(r"\d", expr):
        return None
    return "matematicas", "calcular", {"expression": expr}


def _statistics(text: str):
    flat = _fold(text)
    match = re.fullmatch(
        r"(?:(?:calcula|dame|saca|obtene|obten|encuentra|cual es|cuanto es)\s+)?"
        r"(?:(?:el|la)\s+)?(?:promedio|media aritmetica|estadisticas|resumen de datos|mediana)"
        r"\s+(?:de|entre)\s+(.+)", flat, flags=re.S
    )
    if not match:
        return None
    suffix = match.group(1).strip()
    if re.search(r"\b(?:[a-z]{2,})\b", re.sub(r"\by\b", "", suffix)):
        return None
    if not re.fullmatch(r"[\d\s.,;+\-y]+", suffix):
        return None
    strings = re.findall(_NUM, suffix)
    separators = re.sub(_NUM, "", suffix)
    if not 1 <= len(strings) <= 1000 or not re.fullmatch(r"[\s,;y]+", separators):
        return None
    return "datos", "resumen", {"values": [float(v) for v in strings]}


def _chemistry(text: str):
    match = re.fullmatch(
        r"(?:(?:calcula|calcular|dame|decime|cual es|necesito|cuanto es)\s+)?"
        r"(?:(?:la|el)\s+)?masa molar (?:de|del)\s+([A-Z][A-Za-z0-9()]{0,100})",
        text, flags=re.I
    )
    if not match:
        return None
    # La fórmula mantiene mayúsculas/minúsculas reales (Co != CO).
    if not match.group(1)[0].isupper():
        return None
    return "quimica", "masa_molar", {"formula": match.group(1)}


def _physics(text: str):
    normalized = _fold(text)
    normalized = unicodedata.normalize("NFKC", normalized).replace("²", "2")
    if not any(p in normalized for p in ("fuerza", "newton", "energia cinetica")):
        return None
    mass = re.search(r"\bmasa\s+(?:de\s+)?("+_NUM+r")\s*kg\b", normalized)
    accel = re.search(r"\baceleracion\s+(?:de\s+)?("+_NUM+r")\s*m\s*/\s*s\s*(?:2|\^2)\b", normalized)
    speed = re.search(r"\bvelocidad\s+(?:de\s+)?("+_NUM+r")\s*m\s*/\s*s\b", normalized)
    energy = "energia cinetica" in normalized
    if energy and mass and speed and not accel:
        return "fisica", "mecanica_si", {
            "modelo":"energia_cinetica","masa_kg":float(mass.group(1)),
            "velocidad_m_s":float(speed.group(1))}
    if not energy and mass and accel and not speed:
        return "fisica", "mecanica_si", {
            "modelo":"segunda_ley_newton","masa_kg":float(mass.group(1)),
            "aceleracion_m_s2":float(accel.group(1))}
    return None


def _rubric(text: str):
    match = re.fullmatch(
        r"(?:califica|calificar|evalua|evalua la|calcula|dame|revisa)\s+"
        r"(?:esta\s+|la\s+)?rubrica\s*:\s*(.+)", _fold(text), flags=re.S
    )
    if not match:
        return None
    entries = [x.strip() for x in match.group(1).split(";")]
    if not 1 <= len(entries) <= 20:
        return None
    rows = []
    for entry in entries:
        item = re.fullmatch(r"([a-z][a-z ]{1,80})\s+("+_NUM+r")\s*/\s*("+_NUM+r")", entry)
        if not item:
            return None
        rows.append({"nombre": item.group(1).strip().title(),
                     "obtenido": float(item.group(2)),
                     "maximo": float(item.group(3))})
    return "educacion", "evaluar_rubrica", {"criterios": rows}


def _choose(text: str):
    # Las rutas no compatibles (investigación, dispositivos, archivos) siguen
    # sus reglas y permisos habituales. Nunca adivinar datos ausentes.
    for candidate in (_rubric, _statistics, _chemistry, _physics, _arithmetic):
        found = candidate(text)
        if found:
            return found
    return None


def maybe_answer(raw: str, mode: str = "chat") -> dict | None:
    """Respuesta comprobada local, reutilizable por chat web, voz y cliente móvil."""
    if not isinstance(raw, str) or not 1 <= len(raw) <= MAX_MESSAGE:
        return None
    if mode not in ("chat", "voz"):
        return None
    text = _clean(raw)
    selected = _choose(text)
    if selected is None:
        return None
    role, tool, args = selected
    try:
        outcome = routing.dispatch(text, args, allow_network=False)
    except (ValueError, OSError, ArithmeticError, TypeError, OverflowError):
        return {"tipo":"respuesta","mensaje":"No pude comprobar ese cálculo. Revisá los datos y las unidades.",
                "proveedor":"sky-verified-local","verificacion":{"status":"FAILED","role":role,"tool":tool}}
    if outcome["status"] == "REQUIRES_REVIEW":
        return {"tipo":"respuesta","mensaje":"Esta herramienta requiere revisión técnica por fallos repetidos. No ejecuté el cálculo.",
                "proveedor":"sky-verified-local","verificacion":{"status":"REQUIRES_REVIEW","role":role,"tool":tool}}
    if outcome["status"] != "VERIFIED_LIMITED_SCOPE":
        return {"tipo":"respuesta","mensaje":"No pude verificar el resultado con esos datos. Comprobá la expresión y los valores.",
                "proveedor":"sky-verified-local","verificacion":{"status":"FAILED","role":role,"tool":tool}}
    step=outcome["execution"]["steps"][0]
    result=step["result"]
    try:
        if role == "matematicas":
            answer="El resultado es "+_decimal(result["value"])+"."
        elif role == "datos":
            answer=("Analicé "+str(result["count"])+" valores. Promedio: "+_decimal(result["mean"])+
                    "; mediana: "+_decimal(result["median"])+"; mínimo: "+_decimal(result["minimum"])+
                    "; máximo: "+_decimal(result["maximum"])+".")
        elif role == "quimica":
            answer=("La masa molar aproximada de "+result["formula"]+" es "+
                    _decimal(result["masa_molar_g_mol"])+" gramos por mol.")
        elif role == "fisica":
            if "fuerza_n" in result:
                answer="La fuerza es "+_decimal(result["fuerza_n"])+" newtons."
            else:
                answer="La energía cinética es "+_decimal(result["energia_j"])+" julios."
        elif role == "educacion":
            answer=("La rúbrica suma "+_decimal(result["total_obtenido"])+" de "+
                    _decimal(result["total_posible"])+" puntos ("+
                    _decimal(result["porcentaje"])+"%). El nivel es orientativo, no oficial.")
        else:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return {"tipo":"respuesta","mensaje":answer,"proveedor":"sky-verified-local",
            "ejecucion_externa":False,
            "verificacion":{"status":"VERIFIED_LIMITED_SCOPE","role":role,"tool":tool,
                            "attempts":step.get("attempts",1),
                            "scope":"operacion_local_no_certifica_dispositivos"}}
