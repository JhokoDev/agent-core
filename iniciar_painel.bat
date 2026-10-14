cd /d C:\Projetos\agent-core-main  
python -u -m uvicorn launcher:app --host 0.0.0.0 --port 8001 >> launcher_log.txt 2>&1 

