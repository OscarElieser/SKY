"""Inventario local sin descargas de manifiestos pip con referencias recursivas.

Devuelve 0: distribuciones declaradas/versiones compatibles y no hay extras.
Devuelve 1: faltan paquetes o las versiones instaladas son incompatibles.
Devuelve 2: manifests invalidos o extras no comprobables sin resolver dependencias.
Nunca invoca pip install, HTTP, descargas ni comandos del sistema.
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib import metadata
from pathlib import Path

from pip._vendor.packaging.requirements import Requirement


def leer_manifest(ruta: Path, visitados: set[Path] | None = None) -> list[str]:
    seen = visitados if visitados is not None else set()
    path = ruta.resolve()
    if path in seen:
        return []
    if not path.is_file():
        raise ValueError(f"Manifiesto no encontrado: {path.name}")
    seen.add(path)
    requisitos: list[str] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        linea = raw.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("-r ") or linea.startswith("--requirement "):
            nombre = linea.split(maxsplit=1)[1].strip()
            hijo = (path.parent / nombre).resolve()
            # No salir a rutas del sistema a traves de archivos declarativos.
            if path.parent not in hijo.parents:
                raise ValueError("Referencia de requisitos fuera del directorio del manifiesto")
            requisitos.extend(leer_manifest(hijo, seen))
        elif linea.startswith("-") or "://" in linea:
            raise ValueError("Opcion pip o URL directa fuera del alcance de auditoria")
        else:
            requisitos.append(linea.split(" #", 1)[0].strip())
    return requisitos


def inventario(manifest: Path) -> dict:
    lines = leer_manifest(manifest)
    resultado: dict = {
        "declaraciones": len(lines),
        "instalados": 0,
        "faltantes": [],
        "incompatibles": [],
        "extras_sin_verificar": [],
    }
    comprobados: set[str] = set()
    for line in lines:
        req = Requirement(line)
        if req.url:
            raise ValueError("No se comprueban dependencias externas directas")
        if req.marker is not None and not req.marker.evaluate():
            continue
        nombre = req.name.lower().replace("_", "-")
        if req.extras:
            resultado["extras_sin_verificar"].append(str(req))
        if nombre in comprobados:
            # Validar cada declaracion, aunque la distribucion ya se encontro.
            pass
        comprobados.add(nombre)
        try:
            installed = metadata.version(req.name)
        except metadata.PackageNotFoundError:
            resultado["faltantes"].append(str(req))
            continue
        if req.specifier and installed not in req.specifier:
            resultado["incompatibles"].append(
                {"declarado": str(req), "instalado": installed})
            continue
        resultado["instalados"] += 1
    resultado["completo_verificable"] = not (
        resultado["faltantes"] or resultado["incompatibles"]
        or resultado["extras_sin_verificar"]
    )
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SKY: inspeccion de dependencias Python sin red")
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = inventario(args.manifest)
    except (ValueError, OSError) as exc:
        print(f"SKY: no fue posible inspeccionar el manifiesto: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["faltantes"] or result["incompatibles"]:
        return 1
    if result["extras_sin_verificar"]:
        print("Aviso: extras pip no comprobables solamente con metadatos locales.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
