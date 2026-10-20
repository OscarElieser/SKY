@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No existe .venv. Ejecuta primero SKY_INICIAR.bat.
    exit /b 1
)
echo [SKY] Metaverso local: http://127.0.0.1:8765/sky
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765 --workers 1
