$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pidFile = Join-Path $root '.infra\run\pids.json'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Output 'La pila endurecida no tiene procesos registrados.'; exit 0 }
$pids = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
foreach ($name in @('caddy','api','worker','memurai')) {
    $processId = $pids.$name
    if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $processId -Force
    }
}
Remove-Item -LiteralPath $pidFile -Force
Write-Output 'Pila endurecida detenida.'
