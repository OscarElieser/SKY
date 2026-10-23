@echo off
rem SKY v12: el asistente forma parte de SKY completo (HUD + agente + voz + API).
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (".venv\Scripts\python.exe" iniciar_sky_autonomo.py) else (py -3 iniciar_sky_autonomo.py)
pause
