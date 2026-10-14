from datetime import datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, Field

class BaseEvent(BaseModel):
    """Contrato base para qualquer evento emitido no sistema."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    origem: str = Field(description="Qual componente/dispositivo emitiu este evento.")
    tipo: str = Field(description="O tipo de evento para roteamento no Event Bus.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageReceivedEvent(BaseEvent):
    """Emitido quando uma nova mensagem chega ao sistema (via API, MQTT, etc)."""
    tipo: Literal["message_received"] = "message_received"
    chat_id: str | None = None
    conteudo: str
    skill_id: str | None = None
    imagem_base64: str | None = None


class ToolExecutionCompletedEvent(BaseEvent):
    """Emitido quando uma ferramenta termina a sua execução com sucesso ou erro."""
    tipo: Literal["tool_execution_completed"] = "tool_execution_completed"
    ferramenta_id: str
    contexto_id: str
    sucesso: bool
    resultado: Any | None = None
    erro: str | None = None


class HardwareSensorEvent(BaseEvent):
    """Emitido quando um sensor físico (ESP, Raspberry Pi) envia dados."""
    tipo: Literal["hardware_sensor"] = "hardware_sensor"
    device_id: str
    sensor_tipo: str
    leitura: Any
    unidade: str | None = None


class AgentChunkEvent(BaseEvent):
    """Emitido em tempo real para cada fragmento de texto ou raciocínio gerado pelo modelo."""
    origem: str = "orchestrator"
    tipo: Literal["agent_chunk"] = "agent_chunk"
    chat_id: str
    content: str = ""
    thinking: str | None = None


class AgentMessageEvent(BaseEvent):
    """Emitido quando o Agent Core gera uma resposta ou um chunk de texto."""
    origem: str = "orchestrator"
    tipo: Literal["agent_message"] = "agent_message"
    chat_id: str
    content: str
    model: str | None = None
    route: str | None = None
    skill: str | None = None
    confidence: float | None = None
    reason: str | None = None
    router_metadata: dict | None = None
    plan: dict | None = None
    reasoning: str | None = None


class AgentDoneEvent(BaseEvent):
    """Emitido para sinalizar o fim de uma resposta em streaming."""
    origem: str = "orchestrator"
    tipo: Literal["agent_done"] = "agent_done"
    chat_id: str