import asyncio
import json
from typing import AsyncGenerator
from app.events.event_contract import BaseEvent, AgentChunkEvent, AgentMessageEvent, AgentDoneEvent
from app.events.event_bus import EventBus

class EventGateway:
    """
    Ponte entre o Event Bus interno e os clientes externos (API, WebSockets).
    Gere o ciclo de vida do streaming de respostas para cada chat ativo.
    """

    def __init__(self, bus: EventBus):
        self.bus = bus
        self.queues: dict[str, asyncio.Queue] = {}
        
        # Ouve ativamente os eventos de resposta gerados pelo Agent Core
        self.bus.subscribe("agent_chunk", self._handle_agent_event)
        self.bus.subscribe("agent_message", self._handle_agent_event)
        self.bus.subscribe("agent_done", self._handle_agent_event)

    async def _handle_agent_event(self, event: BaseEvent) -> None:
        """Encaminha o evento recebido para a fila correta com base no chat_id."""
        chat_id = getattr(event, "chat_id", None)
        if chat_id and chat_id in self.queues:
            await self.queues[chat_id].put(event)

    async def stream_chat(self, chat_id: str) -> AsyncGenerator[str, None]:
        """Consome a fila de um chat específico e converte para SSE."""
        self.queues[chat_id] = asyncio.Queue()
        
        try:
            while True:
                event = await self.queues[chat_id].get()
                
                if isinstance(event, AgentChunkEvent):
                    data = {
                        "type": "chunk",
                        "content": event.content,
                        "thinking": event.thinking,
                        "chat_id": event.chat_id,
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                elif isinstance(event, AgentMessageEvent):
                    data = {
                        "type": "message",
                        "content": event.content,
                        "model": event.model,
                        "route": event.route,
                        "skill": event.skill,
                        "confidence": event.confidence,
                        "reason": event.reason,
                        "router_metadata": event.router_metadata,
                        "plan": event.plan,
                        "reasoning": event.reasoning,
                        "provedor": getattr(event, "provedor", None),
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                
                elif isinstance(event, AgentDoneEvent):
                    data = {"type": "done", "chat_id": event.chat_id}
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    break
        finally:
            if chat_id in self.queues:
                del self.queues[chat_id]