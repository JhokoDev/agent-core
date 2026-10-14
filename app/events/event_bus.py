import asyncio
from typing import Callable, Any
from app.events.event_contract import BaseEvent
from app.events.command_contract import BaseCommand

class EventBus:
    """
    Barramento interno de eventos pub/sub em memória.
    Desacopla a emissão de comandos/eventos da sua execução.
    """

    def __init__(self):
        # Mapeia a string de roteamento (ex: 'message_received' ou 'process_message')
        # para uma lista de funções (handlers) que querem ouvir esse evento.
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, routing_key: str, handler: Callable) -> None:
        """Regista um handler para ouvir uma chave de roteamento específica."""
        if routing_key not in self._subscribers:
            self._subscribers[routing_key] = []
            
        if handler not in self._subscribers[routing_key]:
            self._subscribers[routing_key].append(handler)

    def unsubscribe(self, routing_key: str, handler: Callable) -> None:
        """Remove um handler previamente registado."""
        if routing_key in self._subscribers:
            if handler in self._subscribers[routing_key]:
                self._subscribers[routing_key].remove(handler)

    async def publish(self, evento_ou_comando: BaseEvent | BaseCommand) -> None:
        """
        Publica um evento ou comando no barramento.
        Os handlers são executados em background sem bloquear o chamador.
        """
        # A chave de roteamento é 'tipo' (para eventos) ou 'acao' (para comandos)
        routing_key = getattr(
            evento_ou_comando, 
            "tipo", 
            getattr(evento_ou_comando, "acao", None)
        )

        if not routing_key:
            print(f"[EventBus] Aviso: Objeto sem chave de roteamento ignorado: {evento_ou_comando}")
            return

        handlers = self._subscribers.get(routing_key, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Executa handlers async como tarefas de background
                    asyncio.create_task(handler(evento_ou_comando))
                else:
                    # Executa handlers síncronos imediatamente
                    # (Em sistemas muito pesados, poderíamos atirar isto para um ThreadPoolExecutor)
                    handler(evento_ou_comando)
            except Exception as e:
                print(f"[EventBus] Erro ao executar handler para '{routing_key}': {e}")