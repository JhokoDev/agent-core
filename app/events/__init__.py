from app.events.event_contract import (
    BaseEvent, MessageReceivedEvent, ToolExecutionCompletedEvent, 
    HardwareSensorEvent, AgentMessageEvent, AgentDoneEvent
)
from app.events.command_contract import (
    BaseCommand, ProcessMessageCommand, ExecuteToolCommand, HardwareActionCommand
)
from app.events.event_bus import EventBus
from app.events.event_gateway import EventGateway

# Instâncias Globais da arquitetura orientada a eventos
event_bus = EventBus()
event_gateway = EventGateway(bus=event_bus)

__all__ = [
    "EventBus", "event_bus", "EventGateway", "event_gateway",
    "BaseEvent", "MessageReceivedEvent", "ToolExecutionCompletedEvent", 
    "HardwareSensorEvent", "AgentMessageEvent", "AgentDoneEvent",
    "BaseCommand", "ProcessMessageCommand", "ExecuteToolCommand", "HardwareActionCommand"
]