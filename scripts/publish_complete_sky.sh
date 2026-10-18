#!/usr/bin/env bash
set -euo pipefail
if [[ ! -f README_V9_8_INICIO.md || ! -d neural_core || ! -d metaverse ]]; then echo 'Ejecutá desde la raíz del SKY IA v9.8 extraído' >&2; exit 1; fi
if [[ ! -d .git ]]; then git init; git branch -M main; git remote add origin https://github.com/OscarElieser/SKY.git; git fetch origin main; git reset --mixed origin/main; fi
if ! git remote get-url origin >/dev/null 2>&1; then git remote add origin https://github.com/OscarElieser/SKY.git; fi
git switch -C import/sky-v9.8-complete
git add .
if git ls-files --cached | grep -E '(^|/)(local_data/|\.env$|.*\.sqlite3$|.*\.pem$|.*\.key$)'; then echo 'Material privado detectado. Abortando.' >&2; exit 2; fi
git status --short
read -r -p '¿Confirmás y publicás esta rama en GitHub? [s/N] ' answer
[[ "$answer" = 's' || "$answer" = 'S' ]] || exit 0
git commit -m 'feat: import SKY IA v9.8 complete source' || true
git push -u origin import/sky-v9.8-complete
