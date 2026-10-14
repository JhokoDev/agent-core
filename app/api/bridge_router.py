from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any

from app.core.security import verificar_token
from app.events import event_bus
from app.events.event_contract import MessageReceivedEvent
from app.events.command_contract import ProcessMessageCommand

bridge_router = APIRouter(prefix="/bridge", tags=["Agent Bridge"])

class BridgePayload(BaseModel):
    """Schema genérico para injetar comandos via HTTP Bridge."""
    acao: str
    chat_id: str | None = None
    conteudo: str | None = None
    parametros: dict[str, Any] | None = None

@bridge_router.post("/comandos", dependencies=[Depends(verificar_token)])
async def receber_comando_externo(payload: BridgePayload):
    """
    Permite que sistemas externos (Windows Bridge, scripts) 
    injetem comandos diretamente no cérebro do Agente.
    """
    try:
        if payload.acao == "process_message":
            if not payload.conteudo:
                raise HTTPException(status_code=400, detail="O conteúdo é obrigatório para process_message")
                
            comando = ProcessMessageCommand(
                chat_id=payload.chat_id,
                conteudo=payload.conteudo
            )
            # Injeta no barramento. O Orchestrator vai ouvi-lo instantaneamente!
            await event_bus.publish(comando)
            return {"status": "sucesso", "mensagem": "Comando injetado no Event Bus."}
            
        else:
            raise HTTPException(status_code=400, detail=f"Ação não suportada pela bridge: {payload.acao}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na Bridge: {e}")