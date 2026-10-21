from datetime import datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, Field

class BaseCommand(BaseModel):
    """Contrato base para qualquer comando emitido no sistema."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    alvo: str = Field(description="Componente ou dispositivo que deve executar a ação.")
    acao: str = Field(description="A ação que deve ser executada.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessMessageCommand(BaseCommand):
    """Comando para o OrchestratorService processar uma mensagem."""
    alvo: str = "orchestrator"
    acao: Literal["process_message"] = "process_message"
    chat_id: str | None = None
    conteudo: str
    skill_id: str | None = None
    imagem_base64: str | None = None
    provedor: str | None = None


class ExecuteToolCommand(BaseCommand):
    """Comando para o ToolService forçar a execução de uma ferramenta (ex: agendamento)."""
    alvo: str = "tool_service"
    acao: Literal["execute_tool"] = "execute_tool"
    ferramenta_id: str
    contexto_id: str
    argumentos: dict[str, Any] = Field(default_factory=dict)


class HardwareActionCommand(BaseCommand):
    """Comando para enviar uma instrução física a um dispositivo (ex: ligar relé)."""
    alvo: str = "hardware_gateway"
    acao: Literal["hardware_action"] = "hardware_action"
    device_id: str
    instrucao: str
    parametros: dict[str, Any] = Field(default_factory=dict)