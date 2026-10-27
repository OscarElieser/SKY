"""Vista compartida de aprendizaje del núcleo SKY sobre módulos ya existentes.

Consulta registros operacionales y feedback SIN copiar conversaciones ni archivos.
Solo recomienda: nunca ejecuta herramientas, cambia permisos, código o pesos.
Una activación o métrica positiva no equivale a una acción físicamente verificada.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
import unicodedata
from pathlib import Path


def _normalizar(texto: str) -> str:
    limpio = unicodedata.normalize("NFKD", str(texto or "").casefold())
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", limpio).split())


def _catalogo() -> list[dict]:
    """Solo metadatos registrados en código; no carga motores ni comprueba claves."""
    from .sky_module_registry import all_modules
    from .sky_modulos import catalogo
    existentes: dict[str, dict] = {}
    for item in all_modules():
        existentes[item["id"]] = {"id": item["id"], "nombre": item["title"],
                                   "alias": item.get("aliases", [])}
    for item in catalogo():
        if item["id"] not in existentes:
            existentes[item["id"]] = {"id": item["id"], "nombre": item["nombre"],
                                       "alias": list(item.get("alias", ()))}
    return list(existentes.values())


def _telemetria(dias: int = 30) -> dict:
    """Agregados anónimos de la base KPI existente, leída sin modificarla."""
    vacio = {"acciones_reportadas": 0, "acciones_fallidas": 0,
             "modelos_consultados": 0, "activaciones": {}}
    try:
        from .sky_metricas import _ruta_db
        ruta = Path(_ruta_db())
        if not ruta.is_file():
            return vacio
        with sqlite3.connect(ruta.as_uri() + "?mode=ro", uri=True, timeout=0.3) as db:
            filas = db.execute("""SELECT tipo,nombre,COUNT(*),SUM(CASE WHEN ok=1 THEN 1 ELSE 0 END)
                FROM eventos WHERE ts>=? AND
                (tipo IN ('accion','modelo') OR (tipo='servicio' AND nombre LIKE 'modulo_%'))
                AND NOT (tipo='accion' AND UPPER(COALESCE(origen,''))
                    IN ('SENT','RUNNING','PENDING','DISPATCHED','UI'))
                GROUP BY tipo,nombre LIMIT 250""", (time.time() - dias * 86400,)).fetchall()
        resultado = {**vacio, "activaciones": {}}
        for tipo, nombre, cantidad, exitos in filas:
            if tipo == "accion":
                resultado["acciones_reportadas"] += int(cantidad)
                resultado["acciones_fallidas"] += int(cantidad) - int(exitos or 0)
            elif tipo == "modelo":
                resultado["modelos_consultados"] += int(cantidad)
            elif tipo == "servicio" and nombre.startswith("modulo_"):
                modulo = nombre[7:]
                if re.fullmatch(r"[a-z0-9_-]{1,65}", modulo):
                    resultado["activaciones"][modulo] = {"intentos": int(cantidad),
                                                            "correctas": int(exitos or 0)}
        return resultado
    except (OSError, ValueError, sqlite3.Error):
        return vacio


def diagnostico() -> dict:
    """Consolida estadísticas existentes; no afirma que el modelo se reentrenó."""
    try:
        modulos = _catalogo()
    except (ImportError, ValueError, OSError):
        modulos = []
    try:
        from .sky_neural_memory import execution_report
        verificados = execution_report()
    except (ImportError, OSError, sqlite3.Error, ValueError):
        verificados = {"total_observations": 0, "completed": 0, "failed": 0, "by_role": {}}
    try:
        from .sky_evolution import feedback_resumen
        calificaciones = feedback_resumen()
    except (ImportError, OSError, sqlite3.Error, ValueError):
        calificaciones = []
    return {"modulos_catalogados": len(modulos), "catalogo": modulos,
            "ejecuciones_verificadas": verificados, "valoraciones": calificaciones,
            "telemetria": _telemetria(), "modelo_reentrenado": False,
            "politica": "Observaciones consultivas; ninguna capacidad o permiso se amplía automáticamente."}


def contexto_para_cerebro(texto: str) -> str:
    """Resumen breve, acotado y sin contenido privado para los motores de SKY."""
    if os.getenv("SKY_NUCLEO_EVOLUTIVO", "1").strip().lower() in ("0", "false", "off"):
        return ""
    pregunta = " " + _normalizar(texto) + " "
    if len(pregunta) < 5:
        return ""
    datos = diagnostico()
    coincidencias = []
    for modulo in datos["catalogo"]:
        posibles = [modulo["id"].replace("-", " "), modulo["nombre"], *modulo["alias"]]
        if any(len(a := _normalizar(alias)) >= 4 and f" {a} " in pregunta for alias in posibles):
            coincidencias.append(modulo["id"])
    partes = []
    if coincidencias:
        partes.append("Módulos declarados relacionados (su existencia NO garantiza instalación ni disponibilidad): "
                      + ", ".join(coincidencias[:5]) + ".")
    verificados = datos["ejecuciones_verificadas"]
    if verificados.get("total_observations", 0):
        partes.append("Historial operativo con evidencia: "
                      f"{verificados.get('completed', 0)} ciclos completados y "
                      f"{verificados.get('failed', 0)} fallidos. "
                      "Esto no demuestra competencia en una tarea distinta.")
    activaciones = datos["telemetria"]["activaciones"]
    for modulo in coincidencias[:3]:
        item = activaciones.get(modulo)
        if item and item["intentos"]:
            partes.append(f"Activaciones registradas de {modulo}: "
                          f"{item['correctas']}/{item['intentos']}. Activar no verifica una tarea.")
    if not partes:
        return ""
    return ("Aprendizaje operacional SKY (datos de referencia, no instrucciones):\n"
            + "\n".join(partes)
            + "\nNo inventes éxitos ni cambies permisos o herramientas por estas estadísticas.")[:1000]


def explicar_estado() -> str:
    datos = diagnostico()
    v = datos["ejecuciones_verificadas"]
    t = datos["telemetria"]
    return (f"Tengo {datos['modulos_catalogados']} componentes catalogados. "
            f"Registro {v.get('completed', 0)} ciclos completados con evidencia y "
            f"{v.get('failed', 0)} fallidos; además, {t['acciones_reportadas']} "
            f"acciones reportadas en los últimos 30 días. "
            "Aprovecho estos resultados y tus correcciones para orientar mis respuestas, "
            "pero no modifico mi código, mis permisos ni los pesos del modelo por mi cuenta. "
            "No todos los módulos tienen todavía seguimiento individual de resultados.")
