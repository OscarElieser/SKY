@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [SKY] Instalando las dependencias del motor...
  py -3.12 -m venv .venv || py -3 -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,httpx" >nul 2>&1 || ".venv\Scripts\python.exe" -m pip install "fastapi>=0.115,<1" "uvicorn>=0.34,<1" "httpx>=0.27,<1"
echo [SKY] La clave esta en local_data\sky_api_token.txt (se crea al iniciar)
echo [SKY] Abri http://127.0.0.1:8765
".venv\Scripts\python.exe" -m uvicorn metaverse.api:app --host 127.0.0.1 --port 8765
pause
