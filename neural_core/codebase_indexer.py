"""Indexador Inteligente de Código y Arquitectura para SKY IA.

Módulo de Code Intelligence (SKY Developer Intelligence v11.1).
Analiza estructuras de proyectos, árboles de archivos, AST de Python,
imports, clases, funciones, lenguajes, frameworks y dependencias.
"""
from __future__ import annotations
import os, sys, ast, re, json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React (JSX)",
    ".tsx": "React (TSX)",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "Sass",
    ".dart": "Dart/Flutter",
    ".kt": "Kotlin",
    ".java": "Java",
    ".swift": "Swift",
    ".rs": "Rust",
    ".go": "Go",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".sql": "SQL",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".sh": "Shell",
    ".bat": "Batch"
}

IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".pytest_cache", ".idea", ".vscode", "build", "dist",
    ".dart_tool", ".gradle"
}

def analyze_directory_structure(root_path: Path, max_depth: int = 4) -> Dict[str, Any]:
    """Escanea y resume la estructura física de directorios y lenguajes."""
    root = Path(root_path).resolve()
    if not root.is_dir():
        return {"error": f"La ruta {root} no es un directorio válido."}

    file_count = 0
    dir_count = 0
    total_lines = 0
    languages: Dict[str, int] = {}
    config_files: List[str] = []

    tree: Dict[str, Any] = {"name": root.name, "type": "directory", "children": []}

    def _walk(curr_dir: Path, curr_node: Dict[str, Any], depth: int):
        nonlocal file_count, dir_count, total_lines
        if depth > max_depth:
            return

        try:
            entries = sorted(curr_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception:
            return

        for entry in entries:
            if entry.name in IGNORE_DIRS or entry.name.startswith(".system_generated"):
                continue

            if entry.is_dir():
                dir_count += 1
                child_node = {"name": entry.name, "type": "directory", "children": []}
                curr_node["children"].append(child_node)
                _walk(entry, child_node, depth + 1)
            elif entry.is_file():
                file_count += 1
                ext = entry.suffix.lower()
                lang = LANGUAGE_EXTENSIONS.get(ext, "Otro")
                languages[lang] = languages.get(lang, 0) + 1

                # Detectar archivos clave de configuración
                if entry.name.lower() in {
                    "package.json", "requirements.txt", "pyproject.toml",
                    "pubspec.yaml", "dockerfile", "docker-compose.yml",
                    "cargo.toml", "gemfile", "composer.json", "pom.xml"
                }:
                    config_files.append(str(entry.relative_to(root)))

                # Contar líneas si es texto
                try:
                    lines = entry.read_text(encoding="utf-8", errors="ignore").count("\n")
                    total_lines += lines
                except Exception:
                    lines = 0

                curr_node["children"].append({
                    "name": entry.name,
                    "type": "file",
                    "language": lang,
                    "lines": lines
                })

    _walk(root, tree, 1)

    return {
        "root_path": str(root),
        "total_files": file_count,
        "total_directories": dir_count,
        "total_lines_approx": total_lines,
        "language_distribution": languages,
        "config_files": config_files,
        "tree": tree
    }

def extract_python_symbols(file_path: Path) -> Dict[str, Any]:
    """Analiza un archivo Python usando el AST oficial de Python."""
    p = Path(file_path)
    if not p.is_file() or p.suffix != ".py":
        return {"error": "Archivo no válido para análisis Python"}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(p))
    except Exception as exc:
        return {"error": f"Error parseando AST Python: {str(exc)}"}

    classes = []
    functions = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imports.append(f"{mod}.{alias.name}" if mod else alias.name)
        elif isinstance(node, ast.ClassDef):
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            doc = ast.get_docstring(node) or ""
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "bases": bases,
                "methods": methods,
                "docstring": doc[:160]
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Solo funciones a nivel de módulo (no métodos de clase)
            if hasattr(node, 'col_offset') and node.col_offset == 0:
                args = [a.arg for a in node.args.args]
                doc = ast.get_docstring(node) or ""
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": args,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "docstring": doc[:160]
                })

    return {
        "file": p.name,
        "total_classes": len(classes),
        "total_functions": len(functions),
        "total_imports": len(imports),
        "classes": classes,
        "functions": functions,
        "imports": sorted(list(set(imports)))
    }

def search_symbols_in_directory(root_path: Path, query: str) -> List[Dict[str, Any]]:
    """Busca clases, métodos o funciones coincidentes en el proyecto."""
    root = Path(root_path)
    matches = []
    q_lower = query.casefold()

    for py_file in root.rglob("*.py"):
        if any(ign in py_file.parts for ign in IGNORE_DIRS):
            continue
        symbols = extract_python_symbols(py_file)
        if "error" in symbols:
            continue

        for cls in symbols.get("classes", []):
            if q_lower in cls["name"].casefold():
                matches.append({
                    "type": "class",
                    "name": cls["name"],
                    "file": str(py_file.relative_to(root)),
                    "line": cls["line"],
                    "doc": cls["docstring"]
                })

        for fn in symbols.get("functions", []):
            if q_lower in fn["name"].casefold():
                matches.append({
                    "type": "function",
                    "name": fn["name"],
                    "file": str(py_file.relative_to(root)),
                    "line": fn["line"],
                    "doc": fn["docstring"]
                })

    return matches

def detect_codebase_frameworks(root_path: Path) -> List[str]:
    """Detecta los frameworks y arquitecturas empleadas en el repositorio."""
    root = Path(root_path)
    detected = set()

    # Inspeccionar archivos de paquetes
    req_file = root / "requirements.txt"
    if req_file.is_file():
        text = req_file.read_text(encoding="utf-8", errors="ignore").casefold()
        if "fastapi" in text: detected.add("FastAPI")
        if "flask" in text: detected.add("Flask")
        if "django" in text: detected.add("Django")
        if "streamlit" in text: detected.add("Streamlit")
        if "torch" in text or "pytorch" in text: detected.add("PyTorch")
        if "opencv" in text or "cv2" in text: detected.add("OpenCV")
        if "pytest" in text: detected.add("Pytest")

    pkg_file = root / "package.json"
    if pkg_file.is_file():
        try:
            data = json.loads(pkg_file.read_text(encoding="utf-8", errors="ignore"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "react" in deps: detected.add("React")
            if "next" in deps: detected.add("Next.js")
            if "vue" in deps: detected.add("Vue")
            if "express" in deps: detected.add("Express")
            if "tailwindcss" in deps: detected.add("Tailwind CSS")
        except Exception:
            pass

    pub_file = root / "pubspec.yaml"
    if pub_file.is_file():
        detected.add("Flutter")

    return sorted(list(detected))
