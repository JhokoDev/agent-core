@echo off
title Agent Core - Iniciando (Background)

:: 1. Garante que o diretorio de execucao seja a pasta raiz do projeto
cd /d "%~dp0"

:: 2. Verifica se o servico do Ollama esta ativo
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Iniciando o Ollama em segundo plano...
    start "" ollama serve
    timeout /t 3 /nobreak >nul
)

:: 3. Limpa processos travados na porta 8000
echo Limpando processos travados na porta 8000...
powershell -Command "(Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Where-Object { $_ } | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

:: 4. Inicia o servidor FastAPI (Backend) com logs gravados em server_log.txt
echo Iniciando o servidor FastAPI (Backend) com logs ativos em server_log.txt...
start /B python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env >> server_log.txt 2>&1

echo.
echo Sistema Agent Core rodando em background!
echo Backend: Porta 8000 (Logs em server_log.txt)
echo.
