@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No existe .venv. Ejecuta primero SKY_INICIAR.bat.
    exit /b 1
)
echo [SKY] Panel local: http://127.0.0.1:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
