#!/usr/bin/env bash
# Manual GitHub release uploader for SKY historical ZIP archives.
# Requires GitHub CLI authenticated with write permissions: gh auth login
# Usage: bash scripts/publish_history_gh.sh /ruta/SKY_HISTORY_FILES
# Does NOT push binaries into main; every version becomes a separate release asset.
set -euo pipefail
ARCHIVE_DIR=${1:-}
REPO='OscarElieser/SKY'
if [[ -z "$ARCHIVE_DIR" || ! -f "$ARCHIVE_DIR/HISTORIAL_VERSIONES.json" ]]; then
  echo 'Extraé SKY_IA_HISTORIAL_VERSIONES_COMPLETO.zip y pasá su carpeta como argumento.' >&2
  exit 1
fi
command -v gh >/dev/null || { echo 'Instalá GitHub CLI (gh).';exit 1; }
command -v python >/dev/null || { echo 'Se requiere Python 3';exit 1; }
gh auth status >/dev/null
python - "$ARCHIVE_DIR" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);data=json.loads((p/'HISTORIAL_VERSIONES.json').read_text())
for e in data['archives']:
 f=p/e['file']
 if not f.is_file() or f.stat().st_size!=e['bytes'] or hashlib.sha256(f.read_bytes()).hexdigest()!=e['sha256']:
  raise SystemExit('Falló la integridad: '+e['file'])
print(f"Verificadas {len(data['archives'])} versiones ZIP antes de enviar a GitHub.")
PY
while IFS=$'\t' read -r tag file title;do
 [[ -n "$tag" ]]||continue
 if gh release view "$tag" --repo "$REPO" >/dev/null 2>&1; then
  echo "Ya existe $tag: no se sobrescribe automáticamente."
  continue
 fi
 echo "Creando $tag ($file)"
 gh release create "$tag" "$ARCHIVE_DIR/$file" --repo "$REPO" \
  --title "$title" --notes "Snapshot histórico del proyecto SKY. Archivo SHA-256 comprobado localmente; revisar seguridad antes de ejecutar. Autoría conceptual: Oscar Elieser Chamorro Guzmán." \
  --target main
 done < <(python - "$ARCHIVE_DIR" <<'PY'
import json,pathlib,sys
for item in json.loads((pathlib.Path(sys.argv[1])/'HISTORIAL_VERSIONES.json').read_text())['archives']:
 print(item['tag']+'\t'+item['file']+'\t'+item['title'])
PY
)
echo 'Publicación revisable en GitHub → Releases. Los ZIP no cambian main.'
