@echo off
title Agent Core - Backend (Monitoramento Ativo)

echo Limpando processos travados na porta 8000...
powershell -Command "(Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

echo Iniciando o servidor FastAPI na porta 8000...
python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env