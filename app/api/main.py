from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
import shutil
import uuid
import os
from contextlib import asynccontextmanager

from app.api.schemas import ChatRequest
from app.core.security import verificar_token
from app.infrastructure import storage
from app.infrastructure import audio

# Importações de Eventos e Dispositivos
from app.events import event_bus, event_gateway
from app.events.command_contract import ProcessMessageCommand
import app.services 

# --- NOVAS IMPORTAÇÕES DAS FASES 8.6 e 8.7 ---
from app.adapters import mqtt_adapter
from app.api.bridge_router import bridge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gere o ciclo de vida da aplicação (arranque e encerramento)."""
    # Arranque: Iniciar o adaptador MQTT em background
    # await mqtt_adapter.iniciar()
    print("Agent Core inicializado com suporte MQTT!")
    yield
    # Encerramento: Aqui limparíamos as ligações se necessário
    print("A encerrar Agent Core...")

# Passar o lifespan para a instância do FastAPI
app = FastAPI(lifespan=lifespan)

# --- ADICIONAR O ROUTER DA BRIDGE ---
app.include_router(bridge_router)


# ==========================================
# ROTAS DA API (Mantém-se idênticas ao ficheiro anterior)
# ==========================================

@app.get("/agentes", dependencies=[Depends(verificar_token)])
async def listar_agentes():
    return storage.listar_todos_agentes()  

@app.get("/chats", dependencies=[Depends(verificar_token)])
async def listar_chats():
    return storage.listar_historico_chats()  

@app.get("/chats/{chat_id}", dependencies=[Depends(verificar_token)])
async def carregar_chat(chat_id: str):
    chat = storage.obter_chat(chat_id)  
    if not chat:
        raise HTTPException(status_code=404, detail="Chat não encontrado.")
    return chat

@app.post("/chat", dependencies=[Depends(verificar_token)])
async def chat(requisicao: ChatRequest):
    try:
        chat_id = requisicao.chat_id or str(uuid.uuid4())
        comando = ProcessMessageCommand(
            chat_id=chat_id,
            conteudo=requisicao.texto,
            skill_id=requisicao.skill_id,
            imagem_base64=requisicao.imagem_base64
        )
        await event_bus.publish(comando)
        return StreamingResponse(
            event_gateway.stream_chat(chat_id=chat_id), 
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Processamento: {e}")

@app.post("/transcrever", dependencies=[Depends(verificar_token)])
async def transcrever(arquivo: UploadFile = File(...)):
    try:
        caminho_temp = f"temp_audio_{arquivo.filename}"
        with open(caminho_temp, "wb") as buffer:
            shutil.copyfileobj(arquivo.file, buffer)
        texto_extraido = audio.transcrever_audio(caminho_temp)
        return {"texto": texto_extraido}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao processar áudio: {e}")