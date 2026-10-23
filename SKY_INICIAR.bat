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
echo  [0] ASISTENTE PERSONAL SKY (agente + API + panel con voz)
echo  [1] Iniciar Metaverso y API (Puerto 8765)
echo  [2] Iniciar Panel de Control Streamlit (Puerto 8501)
echo  [3] Iniciar Estudio Creativo de Video (Puerto 8765)
echo  [4] Iniciar Estudio Office de Documentos (Puerto 8765)
echo  [5] Iniciar Agente de Dispositivo Local (Puerto 8766)
echo  [6] Ejecutar Diagnostico de Modulos (Preflight)
echo  [7] Ejecutar Suite de Pruebas (Pytest)
echo  [8] Salir
echo  [9] Permisos del asistente (perfil basico / multimedia / completo)
echo.
echo ==============================================================
set /p opt="Selecciona una opcion (0-9): "

if "%opt%"=="0" goto opt_asistente
if "%opt%"=="1" goto opt_metaverso
if "%opt%"=="2" goto opt_streamlit
if "%opt%"=="3" goto opt_creative
if "%opt%"=="4" goto opt_office
if "%opt%"=="5" goto opt_agente
if "%opt%"=="6" goto opt_preflight
if "%opt%"=="7" goto opt_tests
if "%opt%"=="8" goto opt_salir
if "%opt%"=="9" goto opt_permisos
goto menu

:opt_asistente
call "%~dp0INICIAR_SKY_ASISTENTE_WINDOWS.bat"
goto menu

:opt_permisos
".venv\Scripts\python.exe" agente_dispositivo.py --ver-politica
echo.
echo  [b] basico   - estado, webs y 4 apps (confirmando cada accion)
echo  [m] multimedia - + musica, volumen, Spotify/YouTube, apps y avisos (automaticos)
echo  [c] completo - + archivos, capturas, portapapeles y bloqueo
set /p perf="Perfil (b/m/c, Enter para volver): "
if /i "%perf%"=="b" ".venv\Scripts\python.exe" agente_dispositivo.py --perfil basico --solo-config
if /i "%perf%"=="m" ".venv\Scripts\python.exe" agente_dispositivo.py --perfil multimedia --solo-config
if /i "%perf%"=="c" ".venv\Scripts\python.exe" agente_dispositivo.py --perfil completo --solo-config
pause
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
