#!/usr/bin/env bash
# Independent network-disabled container mimics another machine's fresh runtime.
# Real second-host deployment requires operator to transfer encrypted backup separately.
set -euo pipefail
cd "$(dirname "$0")/.."
workspace="$(mktemp -d)"
trap 'rm -rf "$workspace"' EXIT
mkdir -m 700 "$workspace/restore"
python - "$workspace/secret" <<'PY'
import os,secrets,sys
fd=os.open(sys.argv[1],os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as out: out.write(secrets.token_urlsafe(48))
PY
python -m scripts.cross_host_recovery_v109 fixture \
  --file "$workspace/sky-fixture.skybackup" --key-file "$workspace/secret" > "$workspace/create.json"
expected="$(python - "$workspace/create.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['archive_sha256'])
PY
)"
# Do not mount the original SKY data or Docker socket inside the restoration container.
docker run --rm --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 80 --memory 512m --cpus 1 \
  --tmpfs /tmp:rw,nosuid,noexec,nodev,size=64m \
  --mount "type=bind,src=$workspace/sky-fixture.skybackup,dst=/transferred/test.skybackup,readonly" \
  --mount "type=bind,src=$workspace/secret,dst=/secrets/key,readonly" \
  --mount "type=bind,src=$workspace/restore,dst=/recovery" \
  --entrypoint python "${SKY_SMOKE_IMAGE:-sky-v109:local}" \
  -m scripts.cross_host_recovery_v109 restore \
  --file /transferred/test.skybackup --destination /recovery/restored \
  --key-file /secrets/key --expected-sha256 "$expected" > "$workspace/result.json"
python - "$workspace/result.json" "$workspace/restore/restored" <<'PY'
import json, sqlite3,sys
from pathlib import Path
result=json.load(open(sys.argv[1]));dest=Path(sys.argv[2])
assert result['transfer_sha256_verified'] and result['restored_files']==2
with sqlite3.connect(dest/'db/synthetic.sqlite3') as db:
 assert db.execute('SELECT name FROM dummy').fetchone()[0]=='restauracion-sintetica'
assert (dest/'media/images/sample.png').read_bytes().startswith(b'\x89PNG')
print('Verified independent-network-container encrypted recovery: two synthetic files')
PY
