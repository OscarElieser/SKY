# SKY Design Studio Flutter: explicit and scoped owner-approved setup.
# The flutter create step creates platform boilerplate in this project only.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path ".\pubspec.yaml")) { throw "Ejecutá este script dentro del proyecto Flutter generado." }
if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
    throw "Flutter SDK no está en PATH. Instalá el SDK oficial y verificá flutter doctor."
}
Write-Host "SKY preparará SOLO este proyecto Flutter."
Write-Host "Se crearán archivos de plataforma Android/Web si faltan; se descargará flutter_animate."
Write-Host "El proceso analizará Dart y ejecutará las pruebas de widgets."
$approval = Read-Host "Escribí INSTALAR para autorizar"
if ($approval -cne "INSTALAR") { Write-Host "Cancelado, sin modificar ni instalar."; exit 0 }
if (-not (Test-Path ".\android") -or -not (Test-Path ".\web")) {
    flutter create --platforms=android,web --project-name sky_design_flutter .
    if ($LASTEXITCODE -ne 0) { throw "No se pudo generar el proyecto Flutter." }
}
flutter pub get
if ($LASTEXITCODE -ne 0) { throw "No se pudieron descargar dependencias Flutter." }
flutter analyze
if ($LASTEXITCODE -ne 0) { throw "Análisis Flutter fallido: no declarar éxito." }
flutter test
if ($LASTEXITCODE -ne 0) { throw "Pruebas Flutter fallidas: no declarar éxito." }
Write-Host "Dependencias, análisis y pruebas completados."
Write-Host "APK/AAB e iOS NO se han compilado; requieren SDK, dispositivo y firma correspondientes."
