import asyncio
import shutil
import uuid
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest
from app.core.security import verificar_token
from app.infrastructure import storage
from app.infrastructure import audio

# Importações de Eventos e Dispositivos
from app.events import event_bus, event_gateway
from app.events.command_contract import ProcessMessageCommand
import app.services 

# --- IMPORTAÇÕES DE ADAPTERS E ROUTERS ---
from app.adapters import mqtt_adapter
from app.api.bridge_router import bridge_router
from app.api.life_os_router import life_os_router
from app.api.tasks_router import tasks_router
from app.services.life_os import life_os_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gere o ciclo de vida da aplicação (arranque e encerramento)."""
    # Arranque: Iniciar o Heartbeat proativo do Life OS em segundo plano
    heartbeat_task = asyncio.create_task(life_os_service.iniciar_heartbeat(intervalo_segundos=60))
    print("Agent Core inicializado com suporte MQTT e Life OS Heartbeat ativo!")
    yield
    # Encerramento: Finaliza o heartbeat e limpa tarefas
    life_os_service.parar_heartbeat()
    heartbeat_task.cancel()
    print("A encerrar Agent Core...")

# Passar o lifespan para a instância do FastAPI
app = FastAPI(lifespan=lifespan)

# --- ADICIONAR ROUTERS ---
app.include_router(bridge_router)
app.include_router(life_os_router)
app.include_router(tasks_router)

# ==========================================
# ALIASES DIRETOS DO CHECKLIST LIFE OS
# ==========================================

from app.services.life_os.models import (
    InboxInput, EmergencyPauseRequest, SensorContextRequest,
    BancoNotificacaoWebhook, MultaRequest
)

@app.post("/api/inbox")
async def alias_api_inbox(payload: InboxInput):
    """Endpoint de Captura Rápida Zero-Fricção (alias checklist)."""
    return await life_os_service.inbox.processar_entrada(
        texto=payload.texto,
        audio_base64=payload.audio_base64,
        forcar_sem_trava=payload.forcar_sem_trava
    )

@app.post("/api/system/emergency-pause")
def alias_emergency_pause(req: EmergencyPauseRequest):
    """Pausa as cobranças por motivo de imprevisto/emergência (alias checklist)."""
    try:
        return life_os_service.ativar_modo_emergencia(motivo=req.motivo, duracao_horas=req.duracao_horas)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sensors/context")
async def alias_sensors_context(req: SensorContextRequest):
    """Recebe telemetria do MacroDroid (Wi-Fi, carregador, em_casa) (alias checklist)."""
    return await life_os_service.atualizar_contexto_sensores(req.model_dump())

@app.post("/api/finances/bank-notification")
async def alias_bank_notification(notif: BancoNotificacaoWebhook):
    """Interceptação de notificações de Pix/banco (alias checklist)."""
    return await life_os_service.processar_notificacao_bancaria(
        app_origem=notif.app_origem,
        texto=notif.texto,
        titulo=notif.titulo or ""
    )

@app.get("/api/finances/boxes")
def alias_finances_boxes():
    """Consulta consolidada das 4 Caixas Financeiras (alias checklist)."""
    return life_os_service.obter_saldo_caixas()

@app.post("/api/finances/penalty")
def alias_finances_penalty(req: MultaRequest):
    """Contrato de Ulisses / Multa de Procrastinação (alias checklist)."""
    return life_os_service.aplicar_multa(valor=req.valor, motivo=req.motivo, tarefa_id=req.tarefa_id)



# ==========================================
# ROTAS DA API
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
            imagem_base64=requisicao.imagem_base64,
            provedor=requisicao.provedor
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
