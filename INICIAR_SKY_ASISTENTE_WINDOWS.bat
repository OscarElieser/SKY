@echo off
setlocal
cd /d "%~dp0"
title SKY - Asistente Personal
if not exist ".venv\Scripts\python.exe" (
    echo [SKY] Creando entorno virtual e instalando librerias...
    py -3 -m venv .venv || python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
if not exist "%USERPROFILE%\.neuralt\device_agent_policy.json" (
    echo [SKY] Primera vez: activando el perfil "multimedia" ^(musica, volumen, apps, avisos^).
    echo       Podes cambiarlo luego con SKY_INICIAR.bat, opcion 9.
    ".venv\Scripts\python.exe" agente_dispositivo.py --perfil multimedia --solo-config
)
echo [SKY] Iniciando agente de dispositivo en 127.0.0.1:8766 ...
start "SKY Agente" /min ".venv\Scripts\python.exe" agente_dispositivo.py
echo [SKY] Iniciando API y panel en http://127.0.0.1:8765/asistente ...
start "" "http://127.0.0.1:8765/asistente"
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
pause
