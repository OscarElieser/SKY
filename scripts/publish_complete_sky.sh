#!/usr/bin/env bash
# Importar el SKY IA v9.8 COMPLETO desde la carpeta del ZIP descomprimido.
# Ejecutar en la raíz del proyecto local, con Git instalado y autenticado.
set -euo pipefail
if [[ ! -f README_V9_8_INICIO.md || ! -d neural_core || ! -d metaverse ]]; then
  echo 'Error: ejecutá este script desde la raíz de SKY IA v9.8 descomprimida.' >&2
  exit 1
fi
if [[ -e .env ]]; then echo 'Aviso: .env existe, la regla .gitignore debe excluirlo.'; fi
if [[ ! -d .git ]]; then
  git init
  git branch -M main
  git remote add origin https://github.com/OscarElieser/SKY.git
  git fetch origin main
  git reset --mixed origin/main
fi
if ! git remote get-url origin >/dev/null 2>&1; then git remote add origin https://github.com/OscarElieser/SKY.git; fi
# Publicar sobre una rama dedicada; no reescribir main ni forzar push.
git switch -C import/sky-v9.8-complete
git add .
if git ls-files --cached | grep -E '(^|/)(local_data/|\.env$|.*\.sqlite3$|.*\.pem$|.*\.key$)' ; then
  echo 'Error: se ha preparado material privado; corregir .gitignore antes de continuar.' >&2
  exit 2
fi
git status --short
read -r -p '¿Confirmás los archivos mostrados y querés enviarlos a una nueva rama de GitHub? [s/N] ' answer
if [[ "$answer" != 's' && "$answer" != 'S' ]]; then echo 'Sin publicación.'; exit 0; fi
git commit -m 'feat: import SKY IA v9.8 complete source' || true
git push -u origin import/sky-v9.8-complete
echo 'Abrí una solicitud de cambios hacia main para revisión.'
