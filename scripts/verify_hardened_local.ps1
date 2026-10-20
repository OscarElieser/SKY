$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtime = Join-Path $root '.infra\run'
$secrets = Get-Content -Raw -LiteralPath (Join-Path $runtime 'secrets.json') | ConvertFrom-Json
$env:SKY_DEPLOYMENT_MODE = 'public'
$env:SKY_TRUSTED_HOSTS = 'sky.private.test,localhost,127.0.0.1'
$env:SKY_API_KEY = $secrets.api_key
$env:SKY_OWNER_MFA_SECRET = $secrets.mfa_secret
$env:SKY_REDIS_URL = "redis://:$($secrets.redis_password)@127.0.0.1:16379/0"
$env:SKY_BEHIND_TLS_PROXY = '1'
$env:SKY_CREATIVE_WORKER = '0'
$env:SKY_BACKUP_PASSPHRASE = $secrets.backup_passphrase

& (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $root 'sky_preflight.py') --json
if ($LASTEXITCODE -ne 0) { throw 'Preflight público rechazado.' }
$env:REDISCLI_AUTH = $secrets.redis_password
& (Join-Path $root '.infra\memurai\tools\memurai-cli.exe') -h 127.0.0.1 -p 16379 ping | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Redis/Memurai no responde.' }
$httpsCheck = & (Join-Path $root '.venv\Scripts\python.exe') -c "import httpx; r=httpx.get('https://127.0.0.1:8443/sky',verify=False,timeout=10,trust_env=False); assert r.status_code==200; assert r.headers.get('x-frame-options')=='DENY'; print('HTTPS 200')"
if ($LASTEXITCODE -ne 0) { throw 'El proxy HTTPS no responde con las protecciones esperadas.' }
Write-Output 'OK: HTTPS, Redis privado, API pública protegida y worker separado operativos en loopback.'
