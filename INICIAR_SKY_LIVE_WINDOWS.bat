@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Primero iniciá SKY normalmente con INICIAR_WINDOWS.bat
 pause
 exit /b 1
)
.venv\Scripts\python.exe sky_live.py --intervalo 1800
pause
