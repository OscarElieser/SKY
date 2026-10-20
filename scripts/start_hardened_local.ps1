$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $PSScriptRoot 'setup_hardened_local.ps1')
$runtime = Join-Path $root '.infra\run'
$secrets = Get-Content -Raw -LiteralPath (Join-Path $runtime 'secrets.json') | ConvertFrom-Json

$occupied = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -in 8443,16379,18765
if ($occupied) { throw 'Los puertos 8443, 16379 o 18765 ya están ocupados. Ejecutá stop_hardened_local.ps1 o revisá los procesos.' }

$memurai = Start-Process -FilePath (Join-Path $root '.infra\memurai\tools\memurai.exe') `
    -ArgumentList @('memurai.conf') -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2

$env:SKY_DEPLOYMENT_MODE = 'public'
$env:SKY_TRUSTED_HOSTS = 'sky.private.test,localhost,127.0.0.1'
$env:SKY_API_KEY = $secrets.api_key
$env:SKY_OWNER_MFA_SECRET = $secrets.mfa_secret
$env:SKY_REDIS_URL = "redis://:$($secrets.redis_password)@127.0.0.1:16379/0"
$env:SKY_BEHIND_TLS_PROXY = '1'
$env:SKY_CREATIVE_WORKER = '0'
$env:SKY_BACKUP_PASSPHRASE = $secrets.backup_passphrase

$apiArgs = @('-m','uvicorn','metaverse.api:app','--host','127.0.0.1','--port','18765','--workers','1','--proxy-headers','--forwarded-allow-ips','127.0.0.1')
$api = Start-Process -FilePath (Join-Path $root '.venv\Scripts\python.exe') -ArgumentList $apiArgs `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'api.out.log') -RedirectStandardError (Join-Path $runtime 'api.err.log')
$worker = Start-Process -FilePath (Join-Path $root '.venv\Scripts\python.exe') -ArgumentList @('sky_render_worker.py') `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'worker.out.log') -RedirectStandardError (Join-Path $runtime 'worker.err.log')
Start-Sleep -Seconds 3

$caddyArgs = @('run','--config','infra\hardened\Caddyfile','--adapter','caddyfile')
$caddy = Start-Process -FilePath (Join-Path $root '.infra\caddy\caddy.exe') -ArgumentList $caddyArgs `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'caddy.out.log') -RedirectStandardError (Join-Path $runtime 'caddy.err.log')

Start-Sleep -Seconds 4
$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue
$apiPid = ($listeners | Where-Object LocalPort -eq 18765 | Select-Object -First 1).OwningProcess
$redisPid = ($listeners | Where-Object LocalPort -eq 16379 | Select-Object -First 1).OwningProcess
$caddyPid = ($listeners | Where-Object LocalPort -eq 8443 | Select-Object -First 1).OwningProcess
$workerPid = (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*sky_render_worker.py*' } | Select-Object -First 1).ProcessId
@{memurai=$redisPid;api=$apiPid;worker=$workerPid;caddy=$caddyPid} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'pids.json') -Encoding ascii
& (Join-Path $PSScriptRoot 'verify_hardened_local.ps1')
