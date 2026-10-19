@echo off
title Agent Core - Backend (Monitoramento Ativo)

:: 1. Garante que o diretorio de execucao seja sempre a pasta raiz do projeto
cd /d "%~dp0"

:: 2. Verifica se o servico do Ollama esta ativo
echo Verificando servico do Ollama...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [INFO] Ollama nao detectado. Iniciando Ollama em segundo plano...
    start "" ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo [OK] Ollama ativo e respondendo.
)

:: 3. Limpa processos travados na porta 8000
echo Limpando processos travados na porta 8000...
powershell -Command "(Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Where-Object { $_ } | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

:: 4. Inicia o servidor FastAPI na porta 8000 com exibicao de logs em tempo real
echo Iniciando o servidor FastAPI na porta 8000...
echo.
python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env

if errorlevel 1 (
    echo.
    echo [ERRO] O servidor encerrou com falha. Verifique as mensagens acima.
    pause
)