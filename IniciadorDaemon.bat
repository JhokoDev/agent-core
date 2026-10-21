@echo off
cd /d "%~dp0"
echo ========================================================
echo   AGENT CORE · SISTEMA DE DOIS CEREBROS (8000 + 8001)
echo ========================================================

echo 1. Iniciando Guardiao Imutavel (Porta 8001)...
start "" /B python -u watchdog_supervisor.py

timeout /t 2 /nobreak >nul

echo 2. Iniciando Agente Operacional (Porta 8000)...
start "" /B python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env

echo.
echo [OK] Servidores inicializados em segundo plano com sucesso.
