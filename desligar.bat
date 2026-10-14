@echo off
title Agent Core - Desligar
echo.
echo Encerrando o servidor Agent Core e liberando a porta 8000...
taskkill /F /IM python.exe /T > nul
echo.
echo Todos os processos (Python/FastAPI) foram encerrados.
pause
