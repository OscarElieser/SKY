@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  set "PYTHON=python"
)
if not exist .venv\Scripts\python.exe (
  echo Creando ambiente virtual de SKY...
  %PYTHON% -m venv .venv || goto :fallo
)
echo Instalando o comprobando dependencias...
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto :fallo
echo Iniciando SKY solamente en esta computadora...
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
exit /b %errorlevel%
:fallo
echo Error de instalacion. Comprueba Python 3.11/3.12, Internet y espacio disponible.
pause
exit /b 1
