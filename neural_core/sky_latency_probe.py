"""Diagnóstico local de latencia de SKY.

Nunca llama API cloud, nunca escribe .env y nunca imprime memoria o claves.
Compara el tiempo de Ollama y el tiempo del asistente completo por modelo.
Uso: python -m neural_core.sky_latency_probe
Uso: python -m neural_core.sky_latency_probe --models llama3.2 qwen2.5:3b
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import os
import time
import urllib.error
import urllib.request
from unittest.mock import patch


PREGUNTA = "Explica en dos oraciones que es la fotosintesis."


def instalados(base: str) -> set[str]:
    """Consulta la lista de modelos locales sin descargarlos ni ejecutarlos."""
    with urllib.request.urlopen(base.rstrip("/") + "/api/tags", timeout=5) as resp:
        payload = json.load(resp)
    return {str(row.get("name") or "") for row in payload.get("models", [])
            if isinstance(row, dict)}


def instalado(modelo: str, nombres: set[str]) -> bool:
    return modelo in nombres or (":" not in modelo and modelo + ":latest" in nombres)


def _segundos(ns: object) -> float:
    try:
        return round(max(0, int(ns)) / 1_000_000_000, 3)
    except (TypeError, ValueError):
        return 0.0


def prueba_ollama(base: str, modelo: str, pregunta: str = PREGUNTA) -> dict:
    """Obtiene contadores propios de Ollama sin copiar la respuesta generada."""
    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Responde en español, de forma breve y factual."},
            {"role": "user", "content": pregunta},
        ],
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0.2, "num_predict": 128},
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    inicio = time.perf_counter()
    with urllib.request.urlopen(req, timeout=150) as resp:
        dato = json.load(resp)
    transcurrido = round(time.perf_counter() - inicio, 3)
    if not str((dato.get("message") or {}).get("content") or "").strip():
        raise ValueError("Ollama no devolvio texto")
    generados = int(dato.get("eval_count") or 0)
    evaluacion = _segundos(dato.get("eval_duration"))
    return {
        "segundos": transcurrido,
        "carga_s": _segundos(dato.get("load_duration")),
        "prompt_s": _segundos(dato.get("prompt_eval_duration")),
        "generacion_s": evaluacion,
        "tokens_entrada": int(dato.get("prompt_eval_count") or 0),
        "tokens_salida": generados,
        "tokens_segundo": round(generados / evaluacion, 2) if evaluacion else 0.0,
    }


def prueba_asistente(modelo: str, pregunta: str = PREGUNTA) -> dict:
    """Cronometra pasos reales, sin alterar su funcionamiento ni autorizaciones.

    Las etapas son inclusivas: 'cerebro' incluye su preparación de contexto
    y Ollama. No se deben sumar las etapas para deducir el tiempo final.
    """
    from . import sky_asistente_personal as asistente
    from . import sky_unified_agents
    from . import sky_cerebro
    tiempos: dict[str, float] = {}
    medidas: dict[str, object] = {}
    ollama_info: dict[str, object] = {}
    original_llamar = sky_cerebro._llamar
    original_eventos = sky_cerebro._eventos

    def medir_llamada(msgs: list[dict], stream: bool):
        # Solo longitudes y contadores, nunca el contenido de los mensajes.
        medidas["system_chars"] = sum(
            len(str(m.get("content") or "")) for m in msgs if m.get("role") == "system"
        )
        medidas["history_turns"] = max(0, len(msgs) - 2)
        return original_llamar(msgs, stream)

    def medir_eventos(texto, historial, modo, info):
        try:
            yield from original_eventos(texto, historial, modo, info)
        finally:
            for k in ("prompt_tokens", "generated_tokens", "load_s", "prompt_s",
                      "generation_s"):
                if isinstance(info.get(k), (int, float)):
                    ollama_info[k] = info[k]

    def envolver(objeto, nombre: str, etiqueta: str, pila: ExitStack) -> None:
        original = getattr(objeto, nombre)

        def cronometro(*args, **kwargs):
            inicio = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                tiempos[etiqueta] = round(
                    tiempos.get(etiqueta, 0.0) + time.perf_counter() - inicio, 3
                )

        pila.enter_context(patch.object(objeto, nombre, cronometro))

    sky_cerebro.preferir(None)
    with ExitStack() as pila:
        envolver(asistente, "preparar", "preparacion_s", pila)
        envolver(asistente, "reglas", "reglas_s", pila)
        envolver(sky_unified_agents, "maybe_answer", "agentes_s", pila)
        envolver(sky_cerebro, "decidir", "cerebro_s", pila)
        pila.enter_context(patch.object(sky_cerebro, "_llamar", medir_llamada))
        pila.enter_context(patch.object(sky_cerebro, "_eventos", medir_eventos))
        comienzo = time.perf_counter()
        resultado = asistente.atender(pregunta, proveedor="auto", modo="chat")
        total = round(time.perf_counter() - comienzo, 3)
    return {
        "segundos": total,
        "proveedor": str(resultado.get("proveedor") or "sin indicar"),
        "tipo": str(resultado.get("tipo") or "desconocido"),
        "texto": bool(str(resultado.get("mensaje") or "").strip()),
        "etapas": tiempos,
        "ollama": ollama_info,
        "prompt": medidas,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Medir latencia local de SKY y Ollama sin llamadas cloud"
    )
    parser.add_argument("--models", nargs="+", default=["llama3.2", "qwen2.5:3b"],
                        help="Nombres ya instalados en Ollama")
    parser.add_argument("--skip-full", action="store_true",
                        help="Solo mide Ollama directo, no el asistente completo")
    args = parser.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv(".env", override=True)

    # Garantiza que ninguna llamada de inferencia de este diagnóstico salga
    # a un proveedor cloud, sin guardar ninguna modificación en .env.
    os.environ["SKY_LOCAL_ONLY"] = "1"
    os.environ["SKY_CEREBRO"] = "subasta"
    from . import sky_cerebro
    base = sky_cerebro.OLLAMA
    try:
        disponibles = instalados(base)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        print("OLLAMA NO DISPONIBLE:", type(exc).__name__)
        return 2

    print("=== MEDICION LOCAL SKY ===")
    print("Nube desactivada durante esta prueba. .env permanece sin cambios.")
    print("Modelos instalados:", ", ".join(sorted(disponibles)))
    pendientes = 0
    for mod in args.models:
        if not instalado(mod, disponibles):
            print(f"[{mod}] NO INSTALADO, omitido.")
            pendientes += 1
            continue
        os.environ["OLLAMA_MODEL"] = mod
        print(f"\n=== MODELO {mod} ===")
        try:
            directo = prueba_ollama(base, mod)
            print("Ollama directo (s):", directo["segundos"])
            print("Carga / prompt / generacion (s):",
                  directo["carga_s"], directo["prompt_s"], directo["generacion_s"])
            print("Tokens entrada / salida:", directo["tokens_entrada"],
                  directo["tokens_salida"])
            print("Generacion (tokens/s):", directo["tokens_segundo"])
            if not args.skip_full:
                completo = prueba_asistente(mod)
                print("SKY completo (s):", completo["segundos"])
                print("Proveedor / tipo:", completo["proveedor"], "/", completo["tipo"])
                print("Respuesta presente:", completo["texto"])
                print("Tiempos de etapas (s):", completo["etapas"])
                print("Metricas Ollama en SKY:", completo["ollama"])
                print("Tamano seguro del contexto:", completo["prompt"])
                if completo["tipo"] != "respuesta" or completo["proveedor"] != "ollama" or not completo["texto"]:
                    pendientes += 1
        except Exception as exc:
            # No imprimir str(exc): puede contener mensajes y contexto privado.
            print(f"[{mod}] ERROR ({type(exc).__name__})")
            pendientes += 1
    return 1 if pendientes else 0


if __name__ == "__main__":
    raise SystemExit(main())
