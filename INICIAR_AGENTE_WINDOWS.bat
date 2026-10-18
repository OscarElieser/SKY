@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
 .venv\Scripts\python.exe agente_dispositivo.py
) else (
 py -3 agente_dispositivo.py
)
pause
