@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_hardened_local.ps1"
if errorlevel 1 (
    echo [ERROR] No fue posible iniciar SKY endurecido. Revisa .infra\run\*.log
    pause
    exit /b 1
)
start "" "https://127.0.0.1:8443/sky"
echo [OK] SKY endurecido activo en https://127.0.0.1:8443/sky
pause
