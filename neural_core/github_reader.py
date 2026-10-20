"""Lector y Consultor Seguro de Repositorios GitHub para SKY IA.

Permite a SKY consultar código, documentación y arquitecturas de referencia
desde repositorios autorizados públicos de forma controlada y con caché local,
sin necesidad de tokens obligatorios ni riesgos de modificación no autorizada.
"""
from __future__ import annotations
import os, json, time, re, urllib.request, urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "knowledge" / "repositories" / "sources.json"
CACHE_DIR = ROOT / "local_data" / "github_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT = 10

def load_sources_catalog() -> Dict[str, Any]:
    """Carga el catálogo de fuentes de repositorios registrados."""
    if not SOURCES_FILE.is_file():
        return {"version": "1.0", "mode": "read_only", "repositories": []}
    try:
        return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "1.0", "mode": "read_only", "repositories": []}

def list_reference_repositories() -> List[Dict[str, Any]]:
    """Devuelve la lista de repositorios disponibles para consulta técnica."""
    catalog = load_sources_catalog()
    return catalog.get("repositories", [])

def find_repository_entry(identifier: str) -> Optional[Dict[str, Any]]:
    """Busca un repositorio por nombre o identificador (ej: 'Flutter' o 'flutter/flutter')."""
    catalog = load_sources_catalog()
    id_lower = identifier.casefold()
    for repo in catalog.get("repositories", []):
        if repo.get("name", "").casefold() == id_lower or repo.get("repository", "").casefold() == id_lower:
            return repo
    return None

def _github_api_request(endpoint: str) -> Dict[str, Any]:
    """Realiza una petición a la API pública de GitHub con headers y caché."""
    url = f"https://api.github.com/{endpoint.lstrip('/')}"
    headers = {"User-Agent": "SKY-IA-Developer-Core/1.0", "Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"token {token}"

    safe_cache_key = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', endpoint)
    cache_file = CACHE_DIR / f"api_{safe_cache_key}.json"

    if cache_file.is_file():
        try:
            if time.time() - cache_file.stat().st_mtime < 3600: # 1 hora de caché
                return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            try:
                cache_file.write_text(json.dumps(data), encoding="utf-8")
            except Exception:
                pass
            return {"ok": True, "data": data}
    except Exception as exc:
        if cache_file.is_file():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"ok": False, "error": str(exc)}

def fetch_file_content(repo_name_or_path: str, file_path: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """Obtiene el contenido de un archivo de un repositorio GitHub con caché local.
    
    Usa https://raw.githubusercontent.com/{repo}/{branch}/{file_path}
    """
    entry = find_repository_entry(repo_name_or_path)
    repo_full = entry["repository"] if entry else repo_name_or_path
    if "/" not in repo_full:
        return {"ok": False, "error": f"Repositorio no reconocido o formato inválido: {repo_name_or_path}"}

    default_branch = entry.get("default_branch", "main") if entry else "main"
    use_branch = branch or default_branch

    # Cache local seguro
    safe_cache_key = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', f"{repo_full}_{use_branch}_{file_path}")
    cache_file = CACHE_DIR / f"{safe_cache_key}.txt"

    # Si está en caché y tiene menos de 24 horas, usarlo
    if cache_file.is_file():
        try:
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime < 86400: # 24 horas
                return {
                    "ok": True,
                    "repository": repo_full,
                    "branch": use_branch,
                    "path": file_path,
                    "content": cache_file.read_text(encoding="utf-8", errors="replace"),
                    "cached": True
                }
        except Exception:
            pass

    clean_path = file_path.lstrip("/")
    raw_url = f"https://raw.githubusercontent.com/{repo_full}/{use_branch}/{clean_path}"

    headers = {"User-Agent": "SKY-IA-Developer-Core/1.0"}
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    if gh_token:
        headers["Authorization"] = f"token {gh_token}"

    try:
        req = urllib.request.Request(raw_url, headers=headers)
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            try:
                cache_file.write_text(content, encoding="utf-8")
            except Exception:
                pass
            return {
                "ok": True,
                "repository": repo_full,
                "branch": use_branch,
                "path": file_path,
                "content": content,
                "cached": False,
                "size_bytes": len(content.encode("utf-8"))
            }
    except urllib.error.HTTPError as http_err:
        return {"ok": False, "status_code": http_err.code, "error": f"HTTP {http_err.code}: {http_err.reason}"}
    except Exception as exc:
        if cache_file.is_file():
            return {
                "ok": True,
                "repository": repo_full,
                "branch": use_branch,
                "path": file_path,
                "content": cache_file.read_text(encoding="utf-8", errors="replace"),
                "cached": True,
                "warning": "Usando versión en caché previa por indisponibilidad de red."
            }
        return {"ok": False, "error": str(exc)}

def list_repository_branches(repo_identifier: str) -> Dict[str, Any]:
    """Obtiene la lista de ramas públicas del repositorio."""
    entry = find_repository_entry(repo_identifier)
    repo = entry["repository"] if entry else repo_identifier
    res = _github_api_request(f"repos/{repo}/branches")
    if res.get("ok"):
        branches = [b.get("name") for b in res.get("data", []) if isinstance(b, dict)]
        return {"ok": True, "repository": repo, "branches": branches}
    return res

def get_recent_commits(repo_identifier: str, limit: int = 5) -> Dict[str, Any]:
    """Obtiene los commits recientes de un repositorio de referencia."""
    entry = find_repository_entry(repo_identifier)
    repo = entry["repository"] if entry else repo_identifier
    res = _github_api_request(f"repos/{repo}/commits?per_page={limit}")
    if res.get("ok"):
        commits = []
        for c in res.get("data", []):
            if isinstance(c, dict):
                commits.append({
                    "sha": c.get("sha", "")[:7],
                    "message": c.get("commit", {}).get("message", "").split("\n")[0],
                    "date": c.get("commit", {}).get("author", {}).get("date", "")
                })
        return {"ok": True, "repository": repo, "commits": commits}
    return res

def search_reference_code(query: str, repo_identifier: Optional[str] = None) -> Dict[str, Any]:
    """Busca documentación o fragmentos de referencia en los repositorios registrados."""
    sources = list_reference_repositories()
    if repo_identifier:
        found = find_repository_entry(repo_identifier)
        if found:
            sources = [found]

    results = []
    common_targets = ["README.md", "package.json", "pyproject.toml", "Cargo.toml", "pubspec.yaml"]
    q_words = query.casefold().split()

    for s in sources[:4]:
        repo_full = s.get("repository")
        branch = s.get("default_branch", "main")
        for target in common_targets:
            res = fetch_file_content(repo_full, target, branch=branch)
            if res.get("ok"):
                content = res.get("content", "")
                if any(w in content.casefold() for w in q_words if len(w) > 3):
                    idx = content.casefold().find(q_words[0]) if q_words else 0
                    start = max(0, idx - 150)
                    snippet = content[start:start + 450]
                    results.append({
                        "repository": repo_full,
                        "file": target,
                        "snippet": f"...{snippet}..."
                    })
                    break

    return {
        "ok": True,
        "query": query,
        "results": results,
        "total_matches": len(results)
    }
