@echo off  
timeout /t 10 /nobreak  
cd /d C:\Projetos\agent-core-main  
start "Lancador" /B python -m uvicorn launcher:app --host 0.0.0.0 --port 8001  
cd /d C:\Projetos\agent-core-main\painel-core  
start "PainelCore" /B npm run dev  
