@echo off
setlocal
cd /d "%~dp0"
title SKY IA - Centro de Control

if not exist ".venv\Scripts\python.exe" (
    echo [SKY] Creando entorno virtual e instalando librerias...
    py -3 -m venv .venv || python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

:menu
cls
echo ==============================================================
echo                    SKY IA - CENTRO DE CONTROL
echo ==============================================================
echo.
echo  [0] SKY COMPLETO  (HUD + agente + voz + API, recomendado)
echo  [1] Solo API y modulos web (Puerto 8765)
echo  [2] Panel clasico Streamlit (Puerto 8501)
echo  [3] Estudio Creativo de Video
echo  [4] Office Studio (Word, Excel, PowerPoint, PDF)
echo  [5] Solo agente del equipo (Puerto 8766)
echo  [6] Permisos de SKY (basico / multimedia / completo)
echo  [7] Diagnostico de servicios, puertos y modulos
echo  [8] Iniciar SKY automaticamente con Windows
echo  [9] Ejecutar pruebas (pytest)
echo  [I] SKY Interprete: codigo en tu PC con Open Interpreter (confirma cada paso)
echo  [X] Salir
echo.
echo ==============================================================
set "opt="
set /p opt="Selecciona una opcion: "

if "%opt%"=="0" goto opt_completo
if "%opt%"=="1" goto opt_api
if "%opt%"=="2" goto opt_streamlit
if "%opt%"=="3" goto opt_creative
if "%opt%"=="4" goto opt_office
if "%opt%"=="5" goto opt_agente
if "%opt%"=="6" goto opt_permisos
if "%opt%"=="7" goto opt_status
if "%opt%"=="8" goto opt_startup
if "%opt%"=="9" goto opt_tests
if /i "%opt%"=="i" goto opt_interprete
if /i "%opt%"=="x" goto opt_salir
goto menu

:opt_completo
if not exist "%USERPROFILE%\.neuralt\device_agent_policy.json" (
    echo [SKY] Primera vez: perfil "multimedia" ^(apps, musica, volumen, webs, avisos y tareas sin pedir clic^).
    echo       Cambialo cuando quieras con la opcion 6.
    ".venv\Scripts\python.exe" agente_dispositivo.py --perfil multimedia --solo-config
)
echo [SKY] Iniciando SKY completo. La interfaz se abre en http://127.0.0.1:8765/
".venv\Scripts\python.exe" iniciar_sky_autonomo.py
pause
goto menu

:opt_api
start "" "http://127.0.0.1:8765/"
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
pause
goto menu

:opt_streamlit
start "" "http://127.0.0.1:8501"
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
pause
goto menu

:opt_creative
start "" "http://127.0.0.1:8765/creative"
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
pause
goto menu

:opt_office
start "" "http://127.0.0.1:8765/office"
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
pause
goto menu

:opt_agente
".venv\Scripts\python.exe" agente_dispositivo.py
pause
goto menu

:opt_permisos
".venv\Scripts\python.exe" agente_dispositivo.py --ver-politica
echo.
echo  [b] basico     - apps, musica, volumen, webs, avisos y tareas (pide clic salvo musica/volumen)
echo  [m] multimedia - lo mismo, sin pedir clic para lo cotidiano
echo  [c] completo   - + ventanas, carpetas y documentos, notas, escribir texto,
echo                   capturas, portapapeles y bloqueo (estos siempre piden clic)
set "perf="
set /p perf="Perfil (b/m/c, Enter para volver): "
if /i "%perf%"=="b" ".venv\Scripts\python.exe" agente_dispositivo.py --perfil basico --solo-config
if /i "%perf%"=="m" ".venv\Scripts\python.exe" agente_dispositivo.py --perfil multimedia --solo-config
if /i "%perf%"=="c" ".venv\Scripts\python.exe" agente_dispositivo.py --perfil completo --solo-config
echo [SKY] Reinicia SKY (opcion 0) para aplicar los permisos.
pause
goto menu

:opt_status
".venv\Scripts\python.exe" iniciar_sky_autonomo.py --status
echo.
".venv\Scripts\python.exe" sky_preflight.py
pause
goto menu

:opt_startup
".venv\Scripts\python.exe" iniciar_sky_autonomo.py --install-startup
pause
goto menu

:opt_tests
".venv\Scripts\python.exe" -m pytest tests
pause
goto menu

:opt_interprete
".venv\Scripts\python.exe" -c "import interpreter" 2>nul || ".venv\Scripts\python.exe" -m pip install open-interpreter
".venv\Scripts\python.exe" sky_interprete.py
pause
goto menu

:opt_salir
echo Saliendo de SKY...
EXIT /B 0
