# SKY Design Studio: explicit, project-scoped library installation.
# Read this script before running. Not auto-executed by SKY.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath ".\package.json")) { throw "Ejecutá este script dentro del proyecto React de SKY." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 22+ no está disponible. Instalá Node.js desde su sitio oficial." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm no está disponible." }
Write-Host "SKY instalará SOLO bibliotecas declaradas en ESTE proyecto:"
$project = Get-Content ".\package.json" -Raw | ConvertFrom-Json
$project.dependencies.PSObject.Properties | ForEach-Object { Write-Host (" - " + $_.Name + " : " + $_.Value) }
Write-Host "Se generará package-lock.json; no se ejecutarán scripts durante npm install."
Write-Host "Después se ejecutará el build declarado en package.json (vite build)."
$approval = Read-Host "Escribí INSTALAR para autorizar"
if ($approval -cne "INSTALAR") { Write-Host "Cancelado, sin instalar bibliotecas."; exit 0 }
npm install --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación npm: ver salida anterior." }
npm run build
if ($LASTEXITCODE -ne 0) { throw "El build Vite falló. SKY no declarará esta versión funcional." }
if (-not (Test-Path ".\dist\index.html")) { throw "No se encontró el resultado de build." }
Write-Host "Bibliotecas descargadas y build Vite real verificado en dist/."
Write-Host "No es certificación de navegadores reales ni revisión de seguridad completa."
