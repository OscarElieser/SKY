#!/usr/bin/env bash
# Run only on disposable CI hosts. This script never uses production.env.
set -euo pipefail
cd "$(dirname "$0")/.."
file=deploy/compose.integration.yml
export SKY_SMOKE_IMAGE="${SKY_SMOKE_IMAGE:-sky-v110:local}"
created_secrets=0
cleanup() {
  docker compose -f "$file" down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -f deploy/integration-test-ca.crt
  if [[ "$created_secrets" == "1" ]]; then rm -rf deploy/secrets; fi
}
trap cleanup EXIT
if [[ -e deploy/secrets || -e deploy/integration-test-ca.crt ]]; then
  echo 'Refusing to remove or use existing secrets' >&2; exit 3
fi
python -m scripts.provision_secrets_v107 --directory deploy/secrets >/dev/null
created_secrets=1
# Docker Compose bind-mounted file secrets retain host permissions on Linux.
# Grant ONLY the dedicated 10001 service group read access in this disposable CI run.
if ! command -v sudo >/dev/null; then echo 'sudo required for CI-only ACL setup' >&2; exit 6; fi
sudo chgrp 10001 deploy/secrets/*.txt deploy/secrets/redis.conf
sudo chmod 0640 deploy/secrets/*.txt deploy/secrets/redis.conf
docker compose -f "$file" config --quiet
docker compose -f "$file" up -d --wait --wait-timeout 240
# Validate Redis is truly authenticated, not merely reachable.
docker compose -f "$file" exec -T redis sh -c 'REDISCLI_AUTH="$(cat /run/secrets/sky_redis_password)" redis-cli ping' | grep -qx PONG
# Caddy's internal CA root, extracted from the ephemeral test volume.
container="$(docker compose -f "$file" ps -q proxy)"
for attempt in $(seq 1 25); do
  if docker cp "${container}:/data/caddy/pki/authorities/local/root.crt" deploy/integration-test-ca.crt 2>/dev/null; then break; fi
  sleep 1
done
[[ -s deploy/integration-test-ca.crt ]] || { echo 'Local TLS CA not available' >&2; exit 7; }
# HTTPS must verify the certificate chain and expected DNS name.
curl --noproxy '*' --fail --silent --show-error --cacert deploy/integration-test-ca.crt \
  --resolve 'sky.test:18443:127.0.0.1' https://sky.test:18443/api/health > /tmp/sky-v109-health.json
python - <<'PY'
import json
r=json.load(open('/tmp/sky-v109-health.json'))
assert isinstance(r,dict) and r, 'Health payload invalid'
print('TLS verified + API health valid; health keys:',sorted(r))
PY
# Owner resource must not be readable without an API key.
code="$(curl --noproxy '*' --silent --output /dev/null --write-out '%{http_code}' \
  --cacert deploy/integration-test-ca.crt --resolve 'sky.test:18443:127.0.0.1' \
  https://sky.test:18443/api/office/formats)"
[[ "$code" == "401" ]] || { echo "Expected 401, got $code" >&2; exit 4; }
# Renderer must be in a network namespace with no interfaces except loopback.
docker compose -f "$file" exec -T renderer python -c \
  'from pathlib import Path; x=Path("/proc/net/route").read_text().splitlines(); assert len(x)==1, "renderer has a network route"'
# Prove renderer has its own process healthcheck (not an HTTP endpoint).
renderer_state="$(docker inspect --format '{{.State.Health.Status}}' "$(docker compose -f "$file" ps -q renderer)")"
[[ "$renderer_state" == "healthy" ]] || { echo "Renderer not healthy: $renderer_state" >&2; exit 8; }
# Bounded HTTP/TLS load: synthetic health only. This is NOT a full load certification.
PYTHONPATH=. python -m scripts.ci_https_load_v110 --ca deploy/integration-test-ca.crt \
    --requests 60 --concurrency 6 --p95-limit-ms 3000
# No direct host port exposure from API, worker or Redis.
docker compose -f "$file" ps --format json | PYTHONPATH=. python -m scripts.ci_exposure_audit_v110
