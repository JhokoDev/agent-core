@echo off
title Agent Core - Iniciando (Background)

echo Limpando processos travados na porta 8000...
powershell -Command "(Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

echo Iniciando o servidor FastAPI (Backend) com logs ativos em server_log.txt...
start /B python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env >> server_log.txt 2>&1

echo.
echo Sistema Agent Core rodando em background!
echo Backend: Porta 8000 (Logs em server_log.txt)
echo.

