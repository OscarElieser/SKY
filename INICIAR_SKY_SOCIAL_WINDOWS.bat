@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (set "PY=py -3") else (set "PY=python")
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 (echo Python 3.11 o superior es necesario & pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -r requirements_social.txt
if errorlevel 1 (echo Error instalando dependencias & pause & exit /b 1)
echo SKY SOCIAL: http://127.0.0.1:8765/community
echo Panel de propietario: http://127.0.0.1:8765
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1
pause
