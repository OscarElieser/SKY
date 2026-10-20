@echo off
setlocal
cd /d "%~dp0"
title SKY IA UNIVERSAL - Centro de Control

if not exist ".venv\Scripts\python.exe" (
    echo [SKY] Creando entorno virtual e instalando librerias...
    py -3 -m venv .venv || python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

:menu
cls
echo ==============================================================
echo                 SKY IA UNIVERSAL - PANEL DE CONTROL           
echo ==============================================================
echo.
echo  [1] Iniciar Metaverso y API (Puerto 8765)
echo  [2] Iniciar Panel de Control Streamlit (Puerto 8501)
echo  [3] Iniciar Estudio Creativo de Video (Puerto 8765)
echo  [4] Iniciar Estudio Office de Documentos (Puerto 8765)
echo  [5] Iniciar Agente de Dispositivo Local
echo  [6] Ejecutar Diagnostico de Modulos (Preflight)
echo  [7] Ejecutar Suite de Pruebas (Pytest)
echo  [8] Salir
echo.
echo ==============================================================
set /p opt="Selecciona una opcion (1-8): "

if "%opt%"=="1" goto opt_metaverso
if "%opt%"=="2" goto opt_streamlit
if "%opt%"=="3" goto opt_creative
if "%opt%"=="4" goto opt_office
if "%opt%"=="5" goto opt_agente
if "%opt%"=="6" goto opt_preflight
if "%opt%"=="7" goto opt_tests
if "%opt%"=="8" goto opt_salir
goto menu

:opt_metaverso
echo [SKY] Iniciando Metaverso en http://127.0.0.1:8765/sky ...
start "" "http://127.0.0.1:8765/sky"
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
pause
goto menu

:opt_streamlit
echo [SKY] Iniciando Panel Streamlit en http://127.0.0.1:8501 ...
start "" "http://127.0.0.1:8501"
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
pause
goto menu

:opt_creative
echo [SKY] Abriendo Estudio Creativo en http://127.0.0.1:8765/creative ...
start "" "http://127.0.0.1:8765/creative"
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
pause
goto menu

:opt_office
echo [SKY] Abriendo Office Studio en http://127.0.0.1:8765/office ...
start "" "http://127.0.0.1:8765/office"
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
pause
goto menu

:opt_agente
echo [SKY] Iniciando agente de dispositivo...
".venv\Scripts\python.exe" agente_dispositivo.py
pause
goto menu

:opt_preflight
echo [SKY] Ejecutando diagnostico preflight...
".venv\Scripts\python.exe" sky_preflight.py
pause
goto menu

:opt_tests
echo [SKY] Ejecutando pruebas automatizadas...
".venv\Scripts\python.exe" -m pytest tests
pause
goto menu

:opt_salir
echo Saliendo de SKY...
EXIT /B 0
