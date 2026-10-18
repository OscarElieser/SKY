@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (set "PY=py -3") else (set "PY=python")
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 (echo Instala Python 3.11 o 3.12 & pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -r requirements_studio.txt
if errorlevel 1 (echo Error instalando dependencias & pause & exit /b 1)
".venv\Scripts\python.exe" sky_preflight.py
if errorlevel 1 (echo Diagnostico local fallido. No se inicia SKY. & pause & exit /b 1)
echo SKY v9.7: http://127.0.0.1:8765/sky
echo Estudio creativo: http://127.0.0.1:8765/creative (requiere FFmpeg para MP4)
start "" "http://127.0.0.1:8765/sky"
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1
pause
