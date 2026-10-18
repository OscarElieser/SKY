@echo off
cd /d "%~dp0"
set SKY_CREATIVE_WORKER=0
python sky_render_worker.py
pause
