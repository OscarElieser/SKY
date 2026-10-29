"""Read-only SKY repository duplicate/dependency inventory (stdlib only).

Usage: python scripts/audit_repository_layout.py --output repository-audit.json
No files are moved or removed. Do not include secret contents in reports.
"""
import argparse
import ast
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "venv", "node_modules", "build", "dist", ".gradle",
        ".dart_tool", "__pycache__", ".pytest_cache", ".idea", ".vscode"}
EXTS = {".py", ".kt", ".java", ".json", ".yml", ".yaml", ".md", ".sh", ".ps1", ".gradle", ".kts"}
MAX_BYTES = 2_000_000
REFERENCE_EXTS = {".ps1", ".kt", ".kts", ".gradle", ".yml", ".yaml", ".sh", ".json", ".md"}
REFERENCE_PATTERN = re.compile(r"[A-Za-z0-9_./-]+\.(?:py|ps1|kt|kts|gradle|json|ya?ml|sh)")



def inventory(root=ROOT):
    by_hash = defaultdict(list)
    by_name = defaultdict(list)
    imports = []
    file_references = []
    files = 0
    skipped = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP for part in path.relative_to(root).parts):
            continue
        if path.is_symlink() or path.suffix.lower() not in EXTS:
            continue
        relative = path.relative_to(root).as_posix()
        try:
            if path.stat().st_size > MAX_BYTES:
                skipped += 1
                continue
            raw = path.read_bytes()
        except OSError:
            skipped += 1
            continue
        files += 1
        by_hash[hashlib.sha256(raw).hexdigest()].append(relative)
        by_name[path.name.lower()].append(relative)
        if path.suffix.lower() in REFERENCE_EXTS or path.name.endswith(".gradle.kts"):
            try:
                source = raw.decode("utf-8-sig")
            except UnicodeError:
                skipped += 1
                continue
            for match in REFERENCE_PATTERN.finditer(source):
                file_references.append({"source": relative, "reference": match.group(0)})
        if path.suffix == ".py":
            try:
                tree = ast.parse(raw.decode("utf-8-sig"), filename=relative)
            except (SyntaxError, UnicodeError):
                skipped += 1
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({"source": relative, "module": alias.name})
                elif isinstance(node, ast.ImportFrom):
                    imports.append({"source": relative, "module": "." * node.level + (node.module or "")})
    return {
        "schema_version": 1,
        "files_scanned": files,
        "files_skipped": skipped,
        "exact_duplicate_groups": [
            {"sha256": digest, "paths": paths}
            for digest, paths in sorted(by_hash.items()) if len(paths) > 1
        ],
        "same_filename_groups": [
            {"filename": name, "paths": paths}
            for name, paths in sorted(by_name.items()) if len(paths) > 1
        ],
        "python_imports": sorted(imports, key=lambda x: (x["source"], x["module"])),
        "cross_language_file_references": sorted(file_references, key=lambda x: (x["source"], x["reference"])),
        "caution": "Reference strings are candidates, not a complete dependency graph. No files were moved.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="repository-audit.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.write_text(json.dumps(inventory(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Repository audit written:", output)


if __name__ == "__main__":
    main()
