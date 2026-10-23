@echo off
setlocal
cd /d "%~dp0"
title SKY IA - Instalador
echo ==============================================================
echo   SKY IA - Instalador (Python, IA local, voz natural, escucha)
echo ==============================================================
echo  Opciones: INSTALAR_SKY_WINDOWS.bat -Local     (100%% local)
echo            INSTALAR_SKY_WINDOWS.bat -Modelo qwen2.5:7b
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_sky.ps1" %*
if errorlevel 1 (
  echo.
  echo [SKY] La instalacion no termino. Revisa el mensaje de arriba y vuelve a ejecutar.
)
pause
