"""SKY Developer: catálogo verificable de lenguajes y toolchains.

Este módulo NO ejecuta código recibido: la mera existencia de un compilador no
significa que se haya construido, probado ni aislado un proyecto.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
from typing import Any


# Claves visibles, alias reconocibles, herramientas instalables (no se ejecutan).
# Los lenguajes declarativos y servicios propietarios pueden carecer de CLI.
PROFILES: dict[str, dict[str, Any]] = {
    "Python": {"aliases": ("python", "python3"), "tools": ("python", "python3"), "family": "general"},
    "JavaScript": {"aliases": ("javascript", "node.js", "nodejs", "js"), "tools": ("node",), "family": "web"},
    "TypeScript": {"aliases": ("typescript", "ts"), "tools": ("tsc",), "family": "web"},
    "Java": {"aliases": ("java",), "tools": ("javac",), "family": "general"},
    "C": {"aliases": ("lenguaje c", "en c", "c language", "c"), "tools": ("gcc", "clang"), "family": "systems"},
    "C++": {"aliases": ("c++", "cpp"), "tools": ("g++", "clang++"), "family": "systems"},
    "C#": {"aliases": ("c#", "csharp"), "tools": ("dotnet", "csc"), "family": "general"},
    "Go": {"aliases": ("golang", "go"), "tools": ("go",), "family": "general"},
    "Rust": {"aliases": ("rust",), "tools": ("rustc",), "family": "systems"},
    "Dart": {"aliases": ("dart",), "tools": ("dart",), "family": "mobile"},
    "Kotlin": {"aliases": ("kotlin",), "tools": ("kotlinc",), "family": "mobile"},
    "Swift": {"aliases": ("swift",), "tools": ("swiftc",), "family": "mobile"},
    "PHP": {"aliases": ("php",), "tools": ("php",), "family": "web"},
    "Ruby": {"aliases": ("ruby",), "tools": ("ruby",), "family": "general"},
    "Lua": {"aliases": ("lua",), "tools": ("lua",), "family": "scripting"},
    "Perl": {"aliases": ("perl",), "tools": ("perl",), "family": "scripting"},
    "R": {"aliases": ("lenguaje r", "r language", "rstudio", "en r", "r"), "tools": ("Rscript",), "family": "scientific"},
    "Julia": {"aliases": ("julia",), "tools": ("julia",), "family": "scientific"},
    "Scala": {"aliases": ("scala",), "tools": ("scalac",), "family": "functional"},
    "Haskell": {"aliases": ("haskell",), "tools": ("ghc",), "family": "functional"},
    "Elixir": {"aliases": ("elixir",), "tools": ("elixir",), "family": "functional"},
    "Erlang": {"aliases": ("erlang",), "tools": ("erl",), "family": "functional"},
    "F#": {"aliases": ("f#", "fsharp"), "tools": ("dotnet",), "family": "functional"},
    "OCaml": {"aliases": ("ocaml",), "tools": ("ocamlc",), "family": "functional"},
    "Clojure": {"aliases": ("clojure",), "tools": ("clojure",), "family": "functional"},
    "Lisp": {"aliases": ("lisp", "common lisp"), "tools": ("sbcl", "clisp"), "family": "functional"},
    "COBOL": {"aliases": ("cobol",), "tools": ("cobc",), "family": "enterprise"},
    "Fortran": {"aliases": ("fortran",), "tools": ("gfortran",), "family": "scientific"},
    "Zig": {"aliases": ("zig",), "tools": ("zig",), "family": "systems"},
    "Assembly": {"aliases": ("assembly", "assembler", "nasm"), "tools": ("nasm", "as"), "family": "systems"},
    "GDScript": {"aliases": ("gdscript",), "tools": ("godot",), "family": "games"},
    "Solidity": {"aliases": ("solidity",), "tools": ("solc",), "family": "blockchain"},
    "Move": {"aliases": ("move language", "move blockchain"), "tools": (), "family": "blockchain"},
    "ABAP": {"aliases": ("abap",), "tools": (), "family": "enterprise"},
    "MATLAB": {"aliases": ("matlab",), "tools": ("matlab",), "family": "scientific"},
    "Octave": {"aliases": ("octave",), "tools": ("octave",), "family": "scientific"},
    "CUDA": {"aliases": ("cuda",), "tools": ("nvcc",), "family": "scientific"},
    "PowerShell": {"aliases": ("powershell", "pwsh"), "tools": ("pwsh", "powershell"), "family": "scripting"},
    "Bash": {"aliases": ("bash", "shell script"), "tools": ("bash",), "family": "scripting"},
    "Visual Basic": {"aliases": ("visual basic", "vb.net"), "tools": ("dotnet",), "family": "enterprise"},
    "SQL": {"aliases": ("sql",), "tools": ("sqlite3", "psql", "mysql"), "family": "database"},
    "PL/SQL": {"aliases": ("pl/sql",), "tools": (), "family": "database"},
    "T-SQL": {"aliases": ("t-sql", "transact-sql"), "tools": (), "family": "database"},
    "GraphQL": {"aliases": ("graphql",), "tools": (), "family": "declarative"},
    "Cypher": {"aliases": ("cypher",), "tools": (), "family": "database"},
    "SPARQL": {"aliases": ("sparql",), "tools": (), "family": "database"},
    "HTML": {"aliases": ("html",), "tools": (), "family": "declarative"},
    "CSS": {"aliases": ("css",), "tools": (), "family": "declarative"},
    "JSON": {"aliases": ("json",), "tools": (), "family": "declarative"},
    "YAML": {"aliases": ("yaml", "yml"), "tools": (), "family": "declarative"},
    "TOML": {"aliases": ("toml",), "tools": (), "family": "declarative"},
    "XML": {"aliases": ("xml",), "tools": (), "family": "declarative"},
    "HCL": {"aliases": ("terraform hcl", "hcl"), "tools": ("terraform",), "family": "declarative"},
}


def _alias_pattern(alias: str) -> str:
    # Los delimitadores de palabra no funcionan tras el '+' de C++ ni el '#' de C#.
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    return r"(?<![\w])" + escaped + r"(?![\w+#])"


def detect_languages(text: str) -> list[str]:
    """Reconoce alias, puntuación y familias sin confundir Java y JavaScript."""
    if not isinstance(text, str):
        return []
    results = []
    for name, profile in PROFILES.items():
        if any(re.search(_alias_pattern(alias), text, re.IGNORECASE)
               for alias in profile["aliases"]):
            results.append(name)
    return results


def resolve_language(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    key = value.strip().casefold()
    for language, details in PROFILES.items():
        if key == language.casefold() or key in (a.casefold() for a in details["aliases"]):
            return language
    return None


def toolchain_status(language: str | None = None) -> dict[str, Any]:
    """Inspección de PATH SIN ejecutar binarios ni exponer rutas privadas."""
    requested = resolve_language(language) if language else None
    if language and requested is None:
        raise ValueError("Lenguaje no reconocido por el catálogo.")
    names = [requested] if requested else list(PROFILES)
    entries = []
    for name in names:
        profile = PROFILES[name]
        detected = next((tool for tool in profile["tools"] if shutil.which(tool)), None)
        if detected:
            state = "installed_unverified"
        elif profile["tools"]:
            state = "needs_toolchain_installation"
        else:
            state = "requires_specialized_validator_or_service"
        entries.append({
            "language": name,
            "family": profile["family"],
            "toolchain_name": detected,
            "toolchain_detected": bool(detected),
            "state": state,
            "code_generation_possible": True,
            "source_compiled_or_run": False,
            "physical_device_verified": False,
        })
    return {
        "ok": True,
        "checks": entries,
        "method": "read_only_path_lookup",
        "code_execution_performed": False,
        "global_all_languages_certified": False,
        "note": "La detección de un compilador no demuestra que compile, ejecute ni aísle el proyecto."
    }


def validate_source(language: str, source: str) -> dict[str, Any]:
    """Prueba de sintaxis estrictamente estática para Python y JSON."""
    canonical = resolve_language(language)
    if canonical is None:
        raise ValueError("Lenguaje no reconocido por el catálogo.")
    if not isinstance(source, str) or not source or len(source.encode("utf-8")) > 50_000 or "\x00" in source:
        raise ValueError("El código debe ser texto no vacío, sin NUL y de hasta 50 KB.")
    result = {
        "ok": True, "language": canonical, "syntax_checked": False,
        "syntax_valid": None, "code_executed": False,
        "compile_verified": False,
    }
    if canonical == "Python":
        try:
            ast.parse(source)
        except (SyntaxError, ValueError, MemoryError, RecursionError) as exc:
            result.update(syntax_checked=True, syntax_valid=False,
                          status="invalid_syntax", line=getattr(exc, "lineno", None),
                          error=str(getattr(exc, "msg", type(exc).__name__))[:160])
        else:
            result.update(syntax_checked=True, syntax_valid=True,
                          status="syntax_validated_not_executed")
    elif canonical == "JSON":
        try:
            json.loads(source)
        except (json.JSONDecodeError, ValueError, RecursionError) as exc:
            result.update(syntax_checked=True, syntax_valid=False,
                          status="invalid_syntax", line=getattr(exc, "lineno", None),
                          error="JSON inválido")
        else:
            result.update(syntax_checked=True, syntax_valid=True,
                          status="syntax_validated_not_executed")
    else:
        result["status"] = "requires_language_specific_toolchain"
    return result
