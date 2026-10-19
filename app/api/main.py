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

# ==========================================================
# ROTAS DE NOTAS (Unificadas com Capability Hub)
# ==========================================================

from app.services.capability_hub_service import capability_hub

@app.get("/notas")
@app.get("/api/notas")
async def listar_notas_fastapi(q: str = None, query: str = None, offset: int = 0, limit: int = 20):
    termo = q or query
    if termo:
        res = capability_hub.gerenciar_nota(acao="pesquisar", query=termo, offset=offset, limit=limit)
    else:
        res = capability_hub.gerenciar_nota(acao="listar", offset=offset, limit=limit)
    return {"notes": res.get("notas", []), "total": res.get("total", 0)}

@app.post("/notas")
@app.post("/api/notas")
async def criar_nota_fastapi(payload: dict):
    texto = (payload.get("text") or payload.get("texto") or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto da nota é obrigatório.")
    res = capability_hub.gerenciar_nota(acao="salvar", texto=texto)
    if res.get("sucesso"):
        return res.get("nota")
    raise HTTPException(status_code=500, detail=res.get("erro", "Erro ao salvar nota."))

@app.put("/notas/{nota_id}")
@app.put("/api/notas/{nota_id}")
async def atualizar_nota_fastapi(nota_id: int, payload: dict):
    texto = (payload.get("text") or payload.get("texto") or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto da nota é obrigatório.")
    res = capability_hub.gerenciar_nota(acao="editar", texto=texto, nota_id=nota_id)
    if res.get("sucesso"):
        return {"ok": True, "note": res.get("nota")}
    raise HTTPException(status_code=404, detail=res.get("erro", "Nota não encontrada."))

@app.delete("/notas/{nota_id}")
@app.delete("/api/notas/{nota_id}")
async def excluir_nota_fastapi(nota_id: int):
    res = capability_hub.gerenciar_nota(acao="excluir", nota_id=nota_id)
    if res.get("sucesso"):
        return {"ok": True, "status": "removido", "id": nota_id}
    raise HTTPException(status_code=404, detail="Nota não encontrada.")