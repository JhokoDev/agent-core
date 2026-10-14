from app.services.orchestrator_service import OrchestratorService
from app.events import event_bus

orchestrator = OrchestratorService()

# O Orchestrator reage a Comandos emitidos no Event Bus
event_bus.subscribe("process_message", orchestrator.handle_process_message)