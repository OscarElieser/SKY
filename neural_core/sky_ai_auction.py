"""Subasta supervisada de motores de SKY.

No consulta a todos los modelos: clasifica la tarea y calcula ofertas utilizando
preferencias declaradas y telemetría real. La calidad esperada es una heurística,
NO una medición de la respuesta todavía no generada.

Sólo se activa con SKY_CEREBRO=subasta. No envía texto a la nube mientras
SKY_LOCAL_ONLY=1, ni texto con posibles secretos. Las llamadas de IA siguen
pasando por los mismos adaptadores y políticas existentes.
"""
from __future__ import annotations

import os
import re
import statistics
import threading
import time
import unicodedata

CLOUD = ("openai", "gemini", "anthropic", "groq", "deepseek", "mistral")
# El bloqueo temporal es por proceso. Se reinicia al reiniciar SKY.
# No guardamos claves, preguntas ni respuestas de las IA.
_FALLOS: dict[str, tuple[float, str]] = {}
_FALLOS_LOCK = threading.Lock()


def _segundos_espera(motivo: str) -> int:
    """Penalizaciones acotadas según códigos seguros, no mensajes de SDK."""
    numero = re.search(r'\bHTTP (\d{3})\b', str(motivo))
    codigo = int(numero.group(1)) if numero else 0
    if codigo in (401, 402, 403, 404):
        return 600  # requieren revisar acceso o modelo
    if codigo == 429:
        if any(code in motivo for code in (
            'credit_balance_exhausted', 'spend_limit_exceeded',
            'usage_limit_exceeded', 'insufficient_quota',
        )):
            return 600  # no repetir un 429 de facturación
        return 90
    if codigo in (500, 502, 503, 504):
        return 45
    if codigo in (400, 422):
        return 120  # petición inválida: no insistir enseguida
    return 20


def registrar_fallo(proveedor: str, motivo: str) -> None:
    """Marca como indisponible una API durante un plazo corto; sólo en memoria."""
    if proveedor not in CLOUD:
        return
    hasta = time.monotonic() + _segundos_espera(motivo)
    with _FALLOS_LOCK:
        _FALLOS[proveedor] = (hasta, str(motivo)[:120])


def registrar_exito(proveedor: str) -> None:
    with _FALLOS_LOCK:
        _FALLOS.pop(proveedor, None)


def en_espera() -> dict[str, int]:
    """Segundos restantes de suspensión, sin datos privados."""
    ahora = time.monotonic()
    with _FALLOS_LOCK:
        for nombre, (hasta, _) in list(_FALLOS.items()):
            if hasta <= ahora:
                del _FALLOS[nombre]
        return {p: max(1, int(hasta - ahora + 0.999))
                for p, (hasta, _) in _FALLOS.items()}

PRIORIDAD = {
    "general": {"openai": 88, "gemini": 87, "anthropic": 85, "groq": 83, "deepseek": 81, "mistral": 80, "ollama": 72},
    "investigacion": {"gemini": 91, "openai": 89, "anthropic": 88, "deepseek": 83, "groq": 81, "mistral": 80, "ollama": 72},
    "codigo": {"anthropic": 91, "openai": 90, "deepseek": 88, "gemini": 86, "mistral": 82, "groq": 81, "ollama": 71},
    "voz": {"groq": 90, "gemini": 88, "openai": 87, "mistral": 83, "anthropic": 82, "deepseek": 81, "ollama": 72},
    "documentos": {"openai": 91, "anthropic": 90, "gemini": 89, "mistral": 83, "deepseek": 82, "groq": 81, "ollama": 73},
}
# Palabras de seguridad: nunca enviar automáticamente el texto que las contiene.
PRIVADO = re.compile(
    r"\b(?:pin|contrasena|password|clave\s+privada|api[ -]?key|token\s+secreto|"
    r"codigo\s+de\s+verificacion|credenciales?|numero\s+de\s+cuenta)\b"
)


def _normalizar(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if unicodedata.category(c) != "Mn")


def clase(texto: str, modo: str = "chat") -> str:
    t = _normalizar(str(texto or ""))
    if re.search(r"\b(?:codigo|programa|python|flutter|javascript|github|depura|bug|funcion|sql)\b", t):
        return "codigo"
    if re.search(r"\b(?:investiga|investigacion|articulo|cientifico|fuentes|bibliografia|tesis)\b", t):
        return "investigacion"
    if re.search(r"\b(?:documento|word|informe|ensayo|redacta|presentacion|powerpoint)\b", t):
        return "documentos"
    if modo == "voz":
        return "voz"
    return "general"


def _solo_local(texto: str) -> bool:
    from .providers import local_only
    return local_only() or bool(PRIVADO.search(_normalizar(texto)))


def _ollama_disponible() -> bool:
    try:
        from .sky_cerebro import _ollama_ok
        return _ollama_ok()
    except Exception:
        return False


def _telemetria() -> dict:
    """Sólo métricas de modelo de los últimos 7 días; ninguna conversación."""
    resultado = {p: [] for p in (*CLOUD, "ollama")}
    try:
        from .sky_metricas import _filas
        ahora = time.time()
        for fila in _filas(ahora - 7 * 86400, ahora + 1, "modelo"):
            nombre = str(fila["nombre"] or "")
            motor = nombre.split(":", 1)[0]
            if motor in resultado:
                resultado[motor].append((bool(fila["ok"]), fila["ms"]))
    except Exception:
        pass
    return resultado


def max_intentos() -> int:
    try:
        return max(1, min(len(CLOUD) + 1, int(os.getenv("SKY_AUCTION_MAX_ATTEMPTS", "2"))))
    except (ValueError, TypeError):
        return 2


def ofertas(texto: str, modo: str = "chat") -> list[dict]:
    """Lista ordenada de candidatos autorizados. No hace llamadas de inferencia."""
    from .providers import PROVIDERS, provider_ready
    tarea = clase(texto, modo)
    local = _solo_local(texto)
    candidatos = ["ollama"] if local else [*CLOUD, "ollama"]
    datos = _telemetria()
    pausados = en_espera()
    resultado = []
    for nombre in candidatos:
        if nombre in pausados:
            continue
        if nombre == "ollama":
            if not _ollama_disponible():
                continue
        elif not provider_ready(nombre) or nombre not in PROVIDERS:
            continue

        historico = datos.get(nombre) or []
        muestra = len(historico)
        exitos = sum(1 for ok, _ in historico if ok)
        latencias = [ms for ok, ms in historico if ok and ms is not None]
        mediana = int(statistics.median(latencias)) if latencias else None
        puntaje = PRIORIDAD[tarea].get(nombre, 70)
        # Penalizaciones acotadas: nunca prometer una calidad que no se ha evaluado.
        if muestra >= 3:
            puntaje -= min(35, round(35 * (muestra - exitos) / muestra))
        if len(latencias) >= 3 and mediana is not None:
            puntaje -= min(25, round(mediana / (700 if modo == "voz" else 1300)))
        # Precio opcional definido por el dueño, no inventar costos de mercado.
        try:
            coste = float(os.getenv(f"SKY_COSTO_{nombre.upper()}_USD_1K", "") or "0")
            if coste > 0:
                puntaje -= min(12, round(coste * 8))
        except ValueError:
            pass
        resultado.append({
            "proveedor": nombre, "puntuacion": max(0, puntaje),
            "tarea": tarea, "muestras": muestra,
            "exitos": exitos, "mediana_ms": mediana,
            "motivo": "reglas y rendimiento histórico" if muestra >= 3 else "preferencia inicial; rendimiento no verificado",
        })
    return sorted(resultado, key=lambda x: (-x["puntuacion"], CLOUD.index(x["proveedor"])
                                           if x["proveedor"] in CLOUD else len(CLOUD)))


def seleccionar(texto: str, modo: str = "chat") -> str | None:
    ofertas_disponibles = ofertas(texto, modo)
    return ofertas_disponibles[0]["proveedor"] if ofertas_disponibles else None
