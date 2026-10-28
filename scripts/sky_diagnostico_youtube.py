"""SKY: diagnóstico seguro de YouTube Data API v3 sin exponer credenciales.

Uso (desde la raíz del repositorio):
  python -m scripts.sky_diagnostico_youtube
  python -m scripts.sky_diagnostico_youtube "Enanitos Verdes mi primer día sin ti"
"""
from __future__ import annotations

import argparse
import json


def diagnosticar(consulta: str) -> dict:
    from metaverse.hud_api import _youtube_clave
    from neural_core.sky_youtube_search import buscar_videos
    clave = _youtube_clave()
    if not clave:
        return {"api_configurada": False, "consulta": consulta, "origen": "sin_api_oficial",
                "reproduccion_confirmada": False, "videos": [],
                "motivo": "No se encontró YOUTUBE_API_KEY en el proceso ni en el .env local."}
    datos = buscar_videos(consulta, clave=clave)
    return {
        "api_configurada": True,
        "consulta": consulta,
        "origen": datos.get("origen"),
        "metadatos_de_incrustacion": bool(datos.get("verificado")),
        "reproduccion_confirmada": False,
        "motivo": datos.get("motivo", ""),
        "videos": [
            {"titulo": item.get("title"), "canal": item.get("channel"),
             "id": item.get("id"), "enlace_oficial": item.get("url")}
            for item in datos.get("videos", [])[:6]
        ],
        "nota": ("Que la API encuentre videos incrustables NO significa que hayan comenzado "
                 "a reproducirse. El IFrame Player debe confirmarlo en el navegador. "
                 "Si el titular o YouTube bloquean la incrustación, utilizar otro "
                 "video permitido o el enlace oficial."),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico oficial YouTube para SKY")
    parser.add_argument("consulta", nargs="?", default="Enanitos Verdes Mi primer día sin ti")
    args = parser.parse_args()
    print(json.dumps(diagnosticar(args.consulta[:120]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
