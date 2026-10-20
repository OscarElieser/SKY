$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtime = Join-Path $root '.infra\run'
$python = Join-Path $root '.venv\Scripts\python.exe'
$memurai = Join-Path $root '.infra\memurai\tools\memurai.exe'
$caddy = Join-Path $root '.infra\caddy\caddy.exe'

foreach ($required in @($python, $memurai, $caddy)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Falta dependencia de infraestructura: $required"
    }
}
New-Item -ItemType Directory -Force -Path $runtime, (Join-Path $root 'backups_hardened'), (Join-Path $root 'security_reports') | Out-Null

$secretsPath = Join-Path $runtime 'secrets.json'
if (-not (Test-Path -LiteralPath $secretsPath)) {
    $json = & $python -c "import base64,json,secrets; print(json.dumps({'api_key':secrets.token_urlsafe(48),'mfa_secret':base64.b32encode(secrets.token_bytes(32)).decode().rstrip('='),'redis_password':secrets.token_urlsafe(48),'backup_passphrase':secrets.token_urlsafe(64)}))"
    if ($LASTEXITCODE -ne 0) { throw 'No fue posible generar secretos.' }
    Set-Content -LiteralPath $secretsPath -Value $json -Encoding ascii
}

$secrets = Get-Content -Raw -LiteralPath $secretsPath | ConvertFrom-Json
$redisConfig = @"
bind 127.0.0.1
protected-mode yes
port 16379
requirepass $($secrets.redis_password)
appendonly yes
appendfilename "sky-limits.aof"
dir "$($runtime.Replace('\','/'))"
save 900 1
save 300 10
logfile "$((Join-Path $runtime 'memurai.log').Replace('\','/'))"
"@
Set-Content -LiteralPath (Join-Path $runtime 'memurai.conf') -Value $redisConfig -Encoding ascii

# Limit runtime credentials to the current Windows account and SYSTEM.
& icacls $runtime /inheritance:r /grant:r "$($env:USERNAME):(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
Write-Output 'Infraestructura endurecida preparada en .infra\run (solo usuario actual y SYSTEM).'
