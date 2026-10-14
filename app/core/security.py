import os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_correto = os.getenv("AGENT_API_TOKEN")
    if credentials.credentials != token_correto:
        raise HTTPException(status_code=401, detail="Token Inválido. Acesso Negado.")
    return credentials.credentials
