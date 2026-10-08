@echo off
title SongRequest
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [SongRequest] Creando entorno virtual .venv...
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo ============================================================
echo   Iniciando servidor SongRequest...
echo   Presiona Ctrl+C para detener.
echo ============================================================
.\.venv\Scripts\python.exe run.py
pause
