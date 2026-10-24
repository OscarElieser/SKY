"""SKY Developer Workbench — ecosystem discovery, project auditing and guided code.

Owner-authenticated, read-only by default. No project source is executed, no
package is installed, no editor is launched, and no secrets are requested.
Registry checks are explicit opt-in and query fixed public HTTPS hosts only.
"""
from __future__ import annotations

import ast
import html
import json
import os
import re
import shutil
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import PurePosixPath
from typing import Any

from .sky_programming_capabilities import PROFILES as LANGUAGES, resolve_language

# Selected authoritative entry points, not an exhaustive list of the world's
# technologies. Every result explicitly records that it is not installed/tested.
CATALOGUE: dict[str, tuple[tuple[str, str], ...]] = {
    "frameworks": (
        ("React", "https://react.dev/"),
        ("Next.js", "https://nextjs.org/docs"),
        ("Vue", "https://vuejs.org/guide/introduction.html"),
        ("Nuxt", "https://nuxt.com/docs"),
        ("Angular", "https://angular.dev/"),
        ("Svelte", "https://svelte.dev/docs"),
        ("SvelteKit", "https://svelte.dev/docs/kit"),
        ("Astro", "https://docs.astro.build/"),
        ("Vite", "https://vite.dev/guide/"),
        ("Tailwind CSS", "https://tailwindcss.com/docs"),
        ("Bootstrap", "https://getbootstrap.com/docs/"),
        ("Express", "https://expressjs.com/"),
        ("NestJS", "https://docs.nestjs.com/"),
        ("FastAPI", "https://fastapi.tiangolo.com/"),
        ("Django", "https://docs.djangoproject.com/"),
        ("Flask", "https://flask.palletsprojects.com/"),
        ("Spring Boot", "https://spring.io/projects/spring-boot"),
        ("ASP.NET Core", "https://learn.microsoft.com/aspnet/core/"),
        ("Laravel", "https://laravel.com/docs"),
        ("Ruby on Rails", "https://guides.rubyonrails.org/"),
        ("Flutter", "https://docs.flutter.dev/"),
        ("React Native", "https://reactnative.dev/docs/getting-started"),
        ("Expo", "https://docs.expo.dev/"),
        ("Jetpack Compose", "https://developer.android.com/compose"),
        ("SwiftUI", "https://developer.apple.com/xcode/swiftui/"),
        ("Kotlin Multiplatform", "https://kotlinlang.org/docs/multiplatform.html"),
        (".NET MAUI", "https://learn.microsoft.com/dotnet/maui/"),
        ("Unity", "https://docs.unity3d.com/"),
        ("Unreal Engine", "https://dev.epicgames.com/documentation/en-us/unreal-engine"),
        ("Godot", "https://docs.godotengine.org/"),
        ("Phaser", "https://docs.phaser.io/"),
        ("Three.js", "https://threejs.org/docs/"),
        ("Babylon.js", "https://doc.babylonjs.com/"),
        ("PyTorch", "https://docs.pytorch.org/"),
        ("TensorFlow", "https://www.tensorflow.org/guide"),
        ("scikit-learn", "https://scikit-learn.org/stable/"),
        ("Hugging Face Transformers", "https://huggingface.co/docs/transformers/"),
        ("LangChain", "https://docs.langchain.com/"),
        ("LlamaIndex", "https://docs.llamaindex.ai/"),
    ),
    "databases": (
        ("PostgreSQL", "https://www.postgresql.org/docs/"),
        ("MySQL", "https://dev.mysql.com/doc/"),
        ("SQLite", "https://www.sqlite.org/docs.html"),
        ("MariaDB", "https://mariadb.com/docs/"),
        ("Microsoft SQL Server", "https://learn.microsoft.com/sql/sql-server/"),
        ("MongoDB", "https://www.mongodb.com/docs/"),
        ("Redis", "https://redis.io/docs/"),
        ("Supabase", "https://supabase.com/docs"),
        ("Firebase", "https://firebase.google.com/docs"),
        ("Firestore", "https://firebase.google.com/docs/firestore"),
        ("Oracle Database", "https://docs.oracle.com/en/database/"),
        ("ClickHouse", "https://clickhouse.com/docs"),
        ("Elasticsearch", "https://www.elastic.co/guide/"),
        ("Neo4j", "https://neo4j.com/docs/"),
        ("DynamoDB", "https://docs.aws.amazon.com/amazondynamodb/"),
        ("CockroachDB", "https://www.cockroachlabs.com/docs/"),
    ),
    "ides": (
        ("Visual Studio Code", "https://code.visualstudio.com/docs"),
        ("Visual Studio", "https://learn.microsoft.com/visualstudio/"),
        ("Android Studio", "https://developer.android.com/studio"),
        ("IntelliJ IDEA", "https://www.jetbrains.com/help/idea/"),
        ("PyCharm", "https://www.jetbrains.com/help/pycharm/"),
        ("WebStorm", "https://www.jetbrains.com/help/webstorm/"),
        ("Rider", "https://www.jetbrains.com/help/rider/"),
        ("Xcode", "https://developer.apple.com/xcode/"),
        ("Cursor", "https://docs.cursor.com/"),
        ("Windsurf", "https://docs.windsurf.com/"),
        ("Eclipse", "https://www.eclipse.org/documentation/"),
        ("Neovim", "https://neovim.io/doc/"),
        ("Unity Editor", "https://docs.unity3d.com/"),
        ("Godot Editor", "https://docs.godotengine.org/"),
    ),
    "icons": (
        ("Lucide", "https://lucide.dev/"),
        ("Font Awesome", "https://fontawesome.com/docs"),
        ("Material Symbols", "https://fonts.google.com/icons"),
        ("Heroicons", "https://heroicons.com/"),
        ("Bootstrap Icons", "https://icons.getbootstrap.com/"),
        ("Phosphor Icons", "https://phosphoricons.com/"),
        ("Tabler Icons", "https://tabler.io/icons"),
        ("Iconify", "https://iconify.design/docs/"),
        ("Remix Icon", "https://remixicon.com/"),
        ("Ionicons", "https://ionic.io/ionicons"),
    ),
    "fonts": (
        ("Google Fonts", "https://fonts.google.com/"),
        ("Fontsource", "https://fontsource.org/"),
        ("Adobe Fonts", "https://fonts.adobe.com/"),
        ("Inter", "https://rsms.me/inter/"),
        ("Roboto", "https://fonts.google.com/specimen/Roboto"),
        ("Noto Sans", "https://fonts.google.com/noto"),
        ("Poppins", "https://fonts.google.com/specimen/Poppins"),
        ("Manrope", "https://fonts.google.com/specimen/Manrope"),
        ("Fira Code", "https://github.com/tonsky/FiraCode"),
        ("JetBrains Mono", "https://www.jetbrains.com/lp/mono/"),
    ),
}

# Library names are hints and docs, never dynamically installed or imported.
PACKAGE_HINTS: dict[str, tuple[str, str]] = {
    "lucide": ("npm", "lucide"),
    "lucide-react": ("npm", "lucide-react"),
    "react-icons": ("npm", "react-icons"),
    "@fortawesome/fontawesome-svg-core": ("npm", "@fortawesome/fontawesome-svg-core"),
    "@fortawesome/react-fontawesome": ("npm", "@fortawesome/react-fontawesome"),
    "@iconify/react": ("npm", "@iconify/react"),
    "@phosphor-icons/react": ("npm", "@phosphor-icons/react"),
    "bootstrap-icons": ("npm", "bootstrap-icons"),
    "@fontsource/inter": ("npm", "@fontsource/inter"),
    "@fontsource/roboto": ("npm", "@fontsource/roboto"),
    "tailwindcss": ("npm", "tailwindcss"),
    "three": ("npm", "three"),
    "phaser": ("npm", "phaser"),
    "flutter_svg": ("pub", "flutter_svg"),
    "google_fonts": ("pub", "google_fonts"),
    "font_awesome_flutter": ("pub", "font_awesome_flutter"),
    "lucide_icons": ("pub", "lucide_icons"),
    "fastapi": ("pypi", "fastapi"),
    "django": ("pypi", "Django"),
    "pillow": ("pypi", "Pillow"),
}

_FRAMEWORK_PACKAGES = {
    "react": "React", "next": "Next.js", "vue": "Vue",
    "nuxt": "Nuxt", "@angular/core": "Angular", "svelte": "Svelte",
    "@sveltejs/kit": "SvelteKit", "astro": "Astro", "vite": "Vite",
    "tailwindcss": "Tailwind CSS", "bootstrap": "Bootstrap",
    "express": "Express", "@nestjs/core": "NestJS",
    "three": "Three.js", "phaser": "Phaser",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "torch": "PyTorch", "tensorflow": "TensorFlow",
    "scikit-learn": "scikit-learn", "transformers": "Hugging Face Transformers",
    "langchain": "LangChain", "llama-index": "LlamaIndex",
    "flutter": "Flutter",
}
_DB_PACKAGES = {
    "pg": "PostgreSQL", "psycopg": "PostgreSQL", "psycopg2": "PostgreSQL",
    "mysql2": "MySQL", "pymysql": "MySQL", "sqlite3": "SQLite",
    "better-sqlite3": "SQLite", "mongoose": "MongoDB", "mongodb": "MongoDB",
    "pymongo": "MongoDB", "redis": "Redis", "firebase": "Firebase",
    "firebase-admin": "Firebase", "@supabase/supabase-js": "Supabase",
    "supabase": "Supabase", "sqlalchemy": "SQL (SQLAlchemy)",
    "@prisma/client": "SQL (Prisma)", "prisma": "SQL (Prisma)",
    "drift": "SQLite", "sqflite": "SQLite",
}
_EXT = {
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "Sass",
    ".js": "JavaScript", ".jsx": "JavaScript/JSX",
    ".ts": "TypeScript", ".tsx": "TypeScript/TSX",
    ".py": "Python", ".dart": "Dart", ".kt": "Kotlin", ".kts": "Kotlin",
    ".swift": "Swift", ".java": "Java", ".cs": "C#", ".gd": "GDScript",
    ".cpp": "C++", ".c": "C", ".rs": "Rust", ".go": "Go", ".php": "PHP",
    ".rb": "Ruby", ".sql": "SQL", ".hlsl": "HLSL", ".shader": "Shader",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".xml": "XML",
}
_SECRET_FILE = re.compile(
    r"(^|/)(?:\.env(?:[.]|$)|id_rsa|id_ed25519|.*\.(?:pem|key|p12|pfx|keystore)|"
    r"service.account.*[.]json|google-services[.]json|"
    r"GoogleService-Info[.]plist|credentials[.]json|secrets[.]json)",
    re.IGNORECASE,
)
_PATH = re.compile(r"^[A-Za-z0-9_.@+/\-]{1,180}$")
_NAME = re.compile(r"^(?:@[a-zA-Z0-9_.~-]+/)?[a-zA-Z0-9][a-zA-Z0-9_.~-]{0,100}$")
_LIMIT_BYTES = 240_000


class WorkbenchInvalid(ValueError):
    pass


class RegistryUnavailable(RuntimeError):
    pass


def ecosystem(category: str | None = None, query: str = "", limit: int = 80) -> dict[str, Any]:
    """Selected official references. Visibility != installation or test coverage."""
    if category and category not in set(CATALOGUE) | {"languages"}:
        raise WorkbenchInvalid("Categoría no admitida.")
    if not isinstance(query, str) or len(query) > 100 or type(limit) is not int or not 1 <= limit <= 150:
        raise WorkbenchInvalid("Consulta o límite inválido.")
    cats = [category] if category else ["languages", *CATALOGUE]
    items: list[dict[str, Any]] = []
    from .sky_docker_builder import PROFILES as DOCKER_PROFILES
    for cat in cats:
        if cat == "languages":
            source = ((name, None) for name in LANGUAGES)
        else:
            source = CATALOGUE[cat]
        for name, url in source:
            if query.casefold().strip() and query.casefold().strip() not in name.casefold():
                continue
            items.append({
                "name": name, "category": cat, "official_docs": url,
                "docker_profile_defined": cat == "languages" and name in DOCKER_PROFILES,
                "installed": None, "tested_on_this_device": False,
                "package_installed": False,
                "status": "reference_only" if cat != "languages" else "catalogued",
            })
    return {
        "ok": True, "items": items[:limit], "matched": len(items),
        "returned": min(limit, len(items)), "exhaustive_world_catalogue": False,
        "installed_or_verified": False,
        "note": "Referencias y perfiles no significan SDK, librería, IDE o motor instalado.",
        "package_hints": len(PACKAGE_HINTS),
    }


def _clean_project(files: Any) -> dict[str, str]:
    if not isinstance(files, dict) or not 1 <= len(files) <= 36:
        raise WorkbenchInvalid("Enviá entre 1 y 36 archivos de texto, sin datos privados.")
    clean: dict[str, str] = {}
    total = 0
    for path, content in files.items():
        if not isinstance(path, str) or not _PATH.fullmatch(path) or "//" in path or "\\" in path:
            raise WorkbenchInvalid("Ruta relativa no admitida.")
        segments = PurePosixPath(path).parts
        if any(p in ("", ".", "..", ".git", "node_modules", ".venv") for p in segments):
            raise WorkbenchInvalid("Rutas privadas o no permitidas.")
        if _SECRET_FILE.search(path):
            raise WorkbenchInvalid("No enviés claves, .env, certificados ni credenciales a SKY Developer.")
        if not isinstance(content, str) or "\x00" in content:
            raise WorkbenchInvalid("El contenido debe ser texto plano.")
        size = len(content.encode("utf-8", errors="replace"))
        total += size
        if size > 64_000 or total > _LIMIT_BYTES:
            raise WorkbenchInvalid("El proyecto supera los límites de análisis.")
        clean[path] = content
    return clean


def _python_deps(content: str) -> set[str]:
    names: set[str] = set()
    for raw in content.splitlines()[:300]:
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(("-", "git+", "http")):
            continue
        item = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if item:
            names.add(item.group(1).lower().replace("_", "-"))
    return names


def _dart_deps(content: str) -> set[str]:
    # Small, conservative top-level pubspec dependency scanner (not YAML parser).
    section = None
    names: set[str] = set()
    for line in content.splitlines()[:350]:
        if re.match(r"^[A-Za-z_][\w-]*:", line):
            section = line.split(":", 1)[0]
        if section in {"dependencies", "dev_dependencies"}:
            m = re.match(r"^  ([a-zA-Z_][a-zA-Z0-9_]*):", line)
            if m:
                names.add(m.group(1).lower())
    return names


def inspect_project(files: dict[str, str]) -> dict[str, Any]:
    """Analyze provided in-memory manifests; never open or modify local files."""
    fs = _clean_project(files)
    names = set(fs)
    languages = Counter(_EXT.get(PurePosixPath(path).suffix.lower(), "Otro") for path in names)
    packages: set[str] = set()
    files_examined: list[str] = []
    warnings: list[str] = []
    if "package.json" in fs:
        try:
            pkg = json.loads(fs["package.json"])
            if not isinstance(pkg, dict):
                raise ValueError("JSON root must be an object")
            for key in ("dependencies", "devDependencies", "optionalDependencies"):
                block = pkg.get(key, {})
                if isinstance(block, dict):
                    packages.update(name.casefold() for name in block if isinstance(name, str) and _NAME.fullmatch(name))
            if "package-lock.json" not in names and "pnpm-lock.yaml" not in names and "yarn.lock" not in names:
                warnings.append("No se encontró lockfile JS; una instalación podría resolver versiones diferentes.")
            if pkg.get("scripts"):
                warnings.append("package.json tiene scripts; SKY no los ejecutó ni los declaró seguros.")
            files_examined.append("package.json")
        except (ValueError, TypeError) as exc:
            warnings.append("package.json no pudo analizarse como JSON válido.")
    for path in ("requirements.txt", "requirements-dev.txt"):
        if path in fs:
            packages.update(_python_deps(fs[path]))
            files_examined.append(path)
    if "pyproject.toml" in fs:
        try:
            cfg = tomllib.loads(fs["pyproject.toml"])
            project = cfg.get("project", {})
            for dep in project.get("dependencies", []) if isinstance(project, dict) else []:
                if isinstance(dep, str):
                    m = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", dep)
                    if m:
                        packages.add(m.group(1).lower().replace("_", "-"))
            files_examined.append("pyproject.toml")
        except (ValueError, TypeError):
            warnings.append("pyproject.toml inválido o no reconocible.")
    if "pubspec.yaml" in fs:
        packages.update(_dart_deps(fs["pubspec.yaml"]))
        files_examined.append("pubspec.yaml")
    if "Cargo.toml" in fs:
        try:
            cfg = tomllib.loads(fs["Cargo.toml"])
            deps = cfg.get("dependencies", {})
            if isinstance(deps, dict):
                packages.update(x.casefold() for x in deps if isinstance(x, str))
            files_examined.append("Cargo.toml")
        except (ValueError, TypeError):
            warnings.append("Cargo.toml inválido o no reconocible.")
    if "Packages/manifest.json" in fs:
        try:
            manifest = json.loads(fs["Packages/manifest.json"])
            block = manifest.get("dependencies", {})
            if isinstance(block, dict):
                packages.update(k.casefold() for k in block if isinstance(k, str))
            files_examined.append("Packages/manifest.json")
        except (ValueError, TypeError):
            warnings.append("Manifest de Unity inválido.")
    frameworks = {label for p, label in _FRAMEWORK_PACKAGES.items() if p in packages}
    databases = {label for p, label in _DB_PACKAGES.items() if p in packages}
    if "pubspec.yaml" in fs and "flutter" in packages:
        frameworks.add("Flutter")
    if "project.godot" in names:
        frameworks.add("Godot")
    if any(n.endswith(".uproject") for n in names):
        frameworks.add("Unreal Engine")
    if "ProjectSettings/ProjectVersion.txt" in names or "Packages/manifest.json" in names:
        frameworks.add("Unity")
    if any(n.startswith("app/src/") or n.startswith("android/") for n in names) and any(
        n.endswith(("build.gradle", "build.gradle.kts")) for n in names
    ):
        frameworks.add("Android / Gradle")
    if any(n.endswith((".xcodeproj/project.pbxproj", ".xcworkspace/contents.xcworkspacedata")) for n in names):
        frameworks.add("Xcode / iOS")
    editors = []
    if any(n.startswith(".vscode/") for n in names):
        editors.append("Visual Studio Code (config presente)")
    if any(n.startswith(".idea/") for n in names):
        editors.append("JetBrains (config presente)")
    if not frameworks:
        warnings.append("No hay evidencia suficiente para identificar un framework concreto.")
    known_guides = {
        "Flutter": "Ejecutar flutter doctor, flutter pub get, flutter analyze y flutter test en SDK autorizado.",
        "Unity": "Abrir con versión de Unity compatible y probar escenas en Unity Editor real.",
        "Unreal Engine": "Verificar motor Unreal y SDK del sistema antes de compilar el proyecto.",
        "Godot": "Abrir en Godot Engine instalado; probar escenas y exportación real.",
        "Android / Gradle": "Comprobar Android SDK, JDK, gradle wrapper y emulador/dispositivo real.",
        "Xcode / iOS": "Requiere macOS, Xcode instalado y permisos de firma/provisioning para dispositivo.",
        "React": "Ejecutar instalación aprobada, build, lint, pruebas y navegador real en entorno aislado.",
        "Next.js": "Verificar versión Node y ejecutar tests/build sin exponer secretos del proyecto.",
    }
    next_steps = [known_guides[f] for f in sorted(frameworks) if f in known_guides]
    if not next_steps:
        next_steps.append("Seleccioná el SDK y la prueba específica para verificar el proyecto en su entorno real.")
    return {
        "ok": True, "files_analyzed": len(fs), "manifest_files": sorted(files_examined),
        "language_files": dict(sorted(languages.items())),
        "frameworks_detected": sorted(frameworks), "databases_detected": sorted(databases),
        "ide_project_hints": editors,
        "dependency_names": sorted(packages)[:100], "dependency_count": len(packages),
        "warnings": warnings, "recommended_validation": next_steps[:8],
        "analysis_scope": "in_memory_manifest_static_only",
        "dependencies_installed": False, "project_built": False,
        "tests_run": False, "security_audit_certified": False,
    }


def _hint(language: str, raw: str) -> str:
    line = raw.strip()
    if not line:
        return "Línea en blanco: separa bloques o mejora la legibilidad."
    if line.startswith(("#", "//", "/*", "*", "<!--")):
        return "Comentario o documentación para lectores del código."
    if language in {"HTML", "Web"} and line.startswith("<"):
        if re.match(r"<!doctype", line, re.I):
            return "Declara el modo HTML5 del documento."
        if re.search(r"<script\b", line, re.I):
            return "Incluye JavaScript; revisá la fuente, carga y permisos."
        if re.search(r"<link\b", line, re.I):
            return "Enlaza un recurso, como la hoja de estilos."
        if re.search(r"<(?:form|input|button|label)\b", line, re.I):
            return "Define un control o elemento de formulario; revisá accesibilidad."
        if re.search(r"<(?:main|header|nav|section|article|footer)\b", line, re.I):
            return "Introduce un elemento semántico de la estructura HTML."
        return "Define o cierra una etiqueta o contenido del documento HTML."
    if language == "CSS":
        if line.startswith("@"):
            return "Directiva CSS; puede definir condiciones, importaciones o animaciones."
        if "{" in line:
            return "Inicia un bloque de estilos para uno o varios selectores."
        if ":" in line and not line.startswith("}"):
            return "Declara una propiedad CSS y su valor; comprobá compatibilidad con navegadores."
        if "}" in line:
            return "Cierra un bloque de reglas CSS."
        return "Parte de un selector, valor o regla CSS."
    if re.match(r"(?:import|from|using|require\(|#include)\b", line):
        return "Declara una dependencia o importa símbolos; verificá paquete y versión."
    if re.match(r"(?:def|async def|function|func|fn)\b", line):
        return "Declara una función o procedimiento con sus parámetros."
    if re.match(r"(?:class|interface|struct|enum)\b", line):
        return "Declara un tipo, clase, interfaz o estructura."
    if re.match(r"(?:if|elif|else|switch|case|when)\b", line):
        return "Define una rama condicional; depende del estado y sus expresiones."
    if re.match(r"(?:for|while|foreach)\b", line):
        return "Inicia un ciclo de repetición; verificá su condición de salida."
    if re.match(r"(?:return|yield)\b", line):
        return "Entrega un valor o resultado desde la función."
    if re.match(r"(?:try|except|catch|finally|throw|raise)\b", line):
        return "Gestiona excepciones o errores de la operación."
    if re.search(r"\b(?:await|async)\b", line):
        return "Trabaja con operación asíncrona; necesita manejo de errores y tiempos."
    if re.search(r"\b(?:const|let|var|final)\s+[\w$]+", line):
        return "Declara o inicializa una variable o constante."
    if re.search(r"(?:querySelector|addEventListener|getElementById)\s*\(", line):
        return "Consulta o interactúa con el DOM; el elemento debe existir."
    if re.search(r"\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)\b", line, re.I) and language in {"SQL", "PL/SQL", "T-SQL"}:
        return "Instrucción SQL; validá parámetros, permisos y consultas."
    if line in {"}", "{", "};", ")", "]"}:
        return "Delimita el cierre o apertura de un bloque o expresión."
    return "Instrucción o expresión del programa; su efecto exacto depende del contexto."


def explain_code(language: str, source: str, start_line: int = 1,
                 max_lines: int = 80) -> dict[str, Any]:
    """Guaranteed coverage of every requested line; never modifies executable code.

    Interpretations are explicitly heuristic, not a model-proven semantic trace.
    """
    canonical = resolve_language(language)
    if canonical is None:
        raise WorkbenchInvalid("Lenguaje no reconocido; indicá un lenguaje del catálogo.")
    if not isinstance(source, str) or len(source.encode("utf-8", "replace")) > 45_000:
        raise WorkbenchInvalid("Máximo 45 KB de código para explicar.")
    if type(start_line) is not int or start_line < 1 or type(max_lines) is not int or not 1 <= max_lines <= 100:
        raise WorkbenchInvalid("Rango de líneas inválido.")
    lines = source.splitlines()
    if not lines or start_line > len(lines):
        raise WorkbenchInvalid("No hay líneas dentro del rango solicitado.")
    stop = min(len(lines), start_line + max_lines - 1)
    annotations = [
        {"line": i, "code": lines[i - 1], "explanation_es": _hint(canonical, lines[i - 1]),
         "basis": "static_heuristic"}
        for i in range(start_line, stop + 1)
    ]
    syntax: bool | None = None
    error: str | None = None
    if canonical == "Python":
        try:
            ast.parse(source)
            syntax = True
        except SyntaxError as exc:
            syntax = False
            error = f"Python: sintaxis inválida, línea {exc.lineno}"
    elif canonical == "JSON":
        try:
            json.loads(source)
            syntax = True
        except (ValueError, RecursionError):
            syntax = False
            error = "JSON inválido"
    return {
        "ok": True, "language": canonical, "lines_total": len(lines),
        "start_line": start_line, "end_line": stop, "has_more": stop < len(lines),
        "next_start_line": stop + 1 if stop < len(lines) else None,
        "annotations": annotations,
        "source_modified": False, "code_executed": False,
        "syntax_checked": syntax is not None, "syntax_valid": syntax,
        "syntax_error": error, "semantics_fully_proven": False,
        "warning": "Explicación estática orientativa; no reemplaza depuración, tests ni revisión humana.",
    }


def scaffold_web(title: str = "Mi proyecto SKY", subtitle: str = "Sitio web creado con SKY") -> dict[str, Any]:
    """Valid starter source, generated in memory, never written to the owner PC."""
    if not isinstance(title, str) or not isinstance(subtitle, str) or len(title) > 100 or len(subtitle) > 200:
        raise WorkbenchInvalid("Título o descripción demasiado extensos.")
    title = title.strip() or "Mi proyecto SKY"
    subtitle = subtitle.strip() or "Un proyecto web funcional."
    heading = html.escape(title, quote=True)
    detail = html.escape(subtitle, quote=True)
    files = {
        "index.html": (
            '<!DOCTYPE html>\n<html lang="es">\n<head>\n'
            '  <meta charset="utf-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"  <title>{heading}</title>\n"
            '  <link rel="stylesheet" href="styles.css">\n'
            '  <script defer src="app.js"></script>\n'
            '</head>\n<body>\n  <main class="container">\n'
            f"    <h1>{heading}</h1>\n    <p>{detail}</p>\n"
            '    <button type="button" id="sky-action">Probar interacción</button>\n'
            '    <p id="sky-result" role="status" aria-live="polite"></p>\n'
            '  </main>\n</body>\n</html>\n'
        ),
        "styles.css": (
            ":root { color-scheme: light; font-family: system-ui, sans-serif; }\n"
            "body { margin: 0; background: #f6f8fb; color: #102a43; }\n"
            ".container { max-width: 56rem; margin: 4rem auto; padding: 1.5rem; }\n"
            "button { padding: .8rem 1.25rem; border: 0; border-radius: .5rem; "
            "background: #165d6f; color: #ffffff; cursor: pointer; }\n"
            "button:focus-visible { outline: 3px solid #f65e01; outline-offset: 3px; }\n"
            "@media (max-width: 600px) { .container { margin: 1rem auto; } }\n"
        ),
        "app.js": (
            'document.addEventListener("DOMContentLoaded", () => {\n'
            '  const button = document.querySelector("#sky-action");\n'
            '  const output = document.querySelector("#sky-result");\n'
            '  if (!button || !output) return;\n'
            '  button.addEventListener("click", () => {\n'
            '    output.textContent = "SKY comprobó la interacción de este botón.";\n'
            '  });\n'
            '});\n'
        ),
    }
    return {
        "ok": True, "template": "web_html5_css3_javascript",
        "files": files, "file_count": len(files), "files_written": False,
        "dependencies_installed": False, "runtime_verified": False,
        "can_be_checked_with_docker_profile": "Web",
        "message": "Plantilla generada. Ejecutá pruebas de HTML/CSS/DOM antes de declarar funcionalidad.",
    }


_SDK_EXECUTABLES: dict[str, tuple[str, ...]] = {
    "Docker (contenedores)": ("docker",),
    "Git": ("git",),
    "Node.js": ("node",),
    "npm": ("npm", "npm.cmd"),
    "Python": ("python", "python3"),
    "Flutter": ("flutter", "flutter.bat"),
    "Dart": ("dart", "dart.exe"),
    "Android SDK / adb": ("adb", "adb.exe"),
    "Gradle": ("gradle", "gradle.bat"),
    "Java JDK": ("javac", "javac.exe"),
    "Kotlin": ("kotlinc", "kotlinc.bat"),
    "Xcode (solo macOS)": ("xcodebuild",),
    "Swift": ("swiftc",),
    "Unity Editor": ("unity-editor", "Unity"),
    "Godot Engine": ("godot", "godot4", "Godot"),
    "Unreal Build Tool": ("UnrealBuildTool",),
    ".NET / C#": ("dotnet",),
    "Rust": ("rustc",),
    "Go": ("go",),
    "VS Code CLI": ("code", "code.cmd"),
    "Visual Studio IDE": ("devenv", "devenv.exe"),
    "C/C++ toolchain": ("gcc", "clang", "cl"),
}


def sdk_readiness() -> dict[str, Any]:
    """Read-only executable discovery; no invoking SDKs or tools."""
    platforms = []
    for name, binaries in _SDK_EXECUTABLES.items():
        found = next((p for p in binaries if shutil.which(p)), None)
        platforms.append({
            "tool": name,
            "found_on_path": bool(found),
            "executable_name": found,
            "state": "on_path_unverified" if found else "not_found_on_path",
            "installed_verified": False,
            "build_or_device_test_run": False,
            "requires_macos": name == "Xcode (solo macOS)",
        })
    return {
        "ok": True, "host_platform": sys.platform, "tools": platforms,
        "read_only": True, "commands_executed": False,
        "note": "Un IDE puede estar instalado sin agregar un comando al PATH. Xcode exige macOS.",
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _registry_endpoint(registry: str, name: str) -> str:
    if registry not in {"npm", "pypi", "pub"} or not isinstance(name, str) or not _NAME.fullmatch(name):
        raise WorkbenchInvalid("Registro o nombre de paquete no permitido.")
    safe = urllib.parse.quote(name, safe="")
    if registry == "npm":
        return "https://registry.npmjs.org/" + safe + "/latest"
    if registry == "pypi":
        return "https://pypi.org/pypi/" + safe + "/json"
    return "https://pub.dev/api/packages/" + safe


def lookup_package(registry: str, package: str) -> dict[str, Any]:
    """Opt-in metadata ONLY via pinned official hosts, no redirects, no install."""
    if os.getenv("SKY_DEV_REGISTRY_LOOKUP_ENABLED") != "1":
        raise RegistryUnavailable("La consulta externa está desactivada (SKY_DEV_REGISTRY_LOOKUP_ENABLED).")
    url = _registry_endpoint(registry, package)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": "SKY-Developer-Workbench/1.0"
    })
    try:
        with opener.open(request, timeout=6) as resp:
            if resp.status != 200:
                raise RegistryUnavailable("El registro no devolvió respuesta válida.")
            raw = resp.read(450_001)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RegistryUnavailable("No se pudo verificar el paquete con el registro oficial.") from exc
    if len(raw) > 450_000:
        raise RegistryUnavailable("Respuesta demasiado grande; no se procesó.")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("not an object")
        if registry == "pypi":
            item = data.get("info", {})
            latest = item.get("version") if isinstance(item, dict) else None
            description = item.get("summary") if isinstance(item, dict) else None
        elif registry == "npm":
            latest = data.get("version")
            description = data.get("description")
        else:
            pubspec = (data.get("latest") or {}).get("pubspec") or {}
            latest = pubspec.get("version")
            description = pubspec.get("description")
    except (ValueError, TypeError, AttributeError) as exc:
        raise RegistryUnavailable("El registro devolvió metadatos inesperados.") from exc
    return {
        "ok": True, "registry": registry, "package": package,
        "latest_reported": str(latest)[:90] if latest is not None else None,
        "description": str(description or "")[:250],
        "source_url": url, "metadata_fetched": True,
        "license_verified": False, "vulnerabilities_audited": False,
        "package_installed": False, "dependency_compatibility_verified": False,
        "note": "Metadatos publicados, no garantía de seguridad ni de compatibilidad.",
    }
