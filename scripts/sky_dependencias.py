"""Audita dependencias instaladas sin consultar internet ni modificarlas.

Utiliza metadatos del entorno virtual y el parser de requisitos de pip.
No interpreta flags arbitrarias de pip ni instalaciones desde URL.
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib import metadata
from pathlib import Path

try:
    from pip._vendor.packaging.requirements import Requirement
except ImportError:
    from packaging.requirements import Requirement


def revisar(requisitos: list[str]) -> dict:
    faltantes: list[str] = []
    incompatibles: list[dict[str, str]] = []
    omitidos: list[str] = []
    errores: list[str] = []
    comprobados = 0

    for raw in requisitos:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Comentarios separados por espacio; '#' en URL directa es parte de la URL.
        line = line.split(" #", 1)[0].strip()
        if not line or line.startswith("-"):
            errores.append("Opción no admitida en auditoría: " + line[:80])
            continue
        try:
            req = Requirement(line)
            if req.url is not None:
                errores.append("Requisito directo no verificable: " + req.name)
                continue
            if req.extras:
                errores.append("Extras no verificables: " + req.name)
                continue
            if req.marker is not None and not req.marker.evaluate():
                omitidos.append(req.name)
                continue
            comprobados += 1
            try:
                version = metadata.version(req.name)
            except metadata.PackageNotFoundError:
                faltantes.append(str(req))
                continue
            if version not in req.specifier:
                incompatibles.append({
                    "requisito": str(req), "instalado": version,
                })
        except (ValueError, SyntaxError) as exc:
            errores.append("Requisito inválido: " + line[:80] + " (" + type(exc).__name__ + ")")

    return {
        "completo": not (faltantes or incompatibles or errores),
        "comprobados": comprobados, "omitidos": omitidos,
        "faltantes": faltantes, "incompatibles": incompatibles,
        "errores": errores,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SKY: inventario de dependencias sin descargas")
    parser.add_argument("--requirements", type=Path, help="requirements.txt que se comprobará")
    parser.add_argument("--paquetes", nargs="+", help="nombres de paquetes opcionales")
    parser.add_argument("--json", action="store_true", help="resultado legible por scripts")
    args = parser.parse_args(argv)
    if not args.requirements and not args.paquetes:
        parser.error("Indicá --requirements o --paquetes")
    lines = []
    if args.requirements:
        if not args.requirements.is_file():
            print("No se encuentra requirements.txt", file=sys.stderr)
            return 2
        lines.extend(args.requirements.read_text(encoding="utf-8-sig").splitlines())
    if args.paquetes:
        lines.extend(args.paquetes)
    result = revisar(lines)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("SKY — dependencias comprobadas:", result["comprobados"])
        print("Faltantes:", len(result["faltantes"]), "| Versiones incompatibles:", len(result["incompatibles"]))
        for name in result["faltantes"]:
            print("  [FALTA]", name)
        for item in result["incompatibles"]:
            print("  [VERSIÓN]", item["requisito"], "instalado:", item["instalado"])
        for error in result["errores"]:
            print("  [NO VERIFICABLE]", error)
        if result["completo"]:
            print("SKY — requisitos declarados satisfechos. No hace falta reinstalar.")
    return 2 if result["errores"] else (0 if result["completo"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())
