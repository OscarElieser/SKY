@echo off
setlocal
cd /d "%~dp0"
rem SKY Engine ya puede usar 8765; el agente JARVIS emplea 18765 por defecto.
rem Respetar SKY_DEVICE_PORT si el propietario ya eligio un puerto distinto.
if not defined SKY_DEVICE_PORT set "SKY_DEVICE_PORT=18765"
echo [SKY] Puerto del agente local: %SKY_DEVICE_PORT%
set "PYTHON=py -3"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
set "VOICE_MODEL=%~1"
if "%VOICE_MODEL%"=="" set "VOICE_MODEL=modelos\vosk-model-es"
if not exist "%VOICE_MODEL%\" (
  echo [SKY] Falta un modelo Vosk. Descarga un modelo de espanol y pasa su carpeta como argumento.
  echo Ejemplo: INICIAR_SKY_JARVIS_WINDOWS.bat "C:\modelos\vosk-model-es"
  pause
  exit /b 1
)
echo [SKY] Agente solo en localhost. No abras el puerto a Internet.
start "SKY Agente Local" cmd /k "%PYTHON% agente_dispositivo.py"
echo [SKY] Activacion por voz: di SKY, abre YouTube.
%PYTHON% sky_manos_libres.py --model "%VOICE_MODEL%" --execute-safe
pause
