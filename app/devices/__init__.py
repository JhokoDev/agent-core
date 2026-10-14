from app.devices.device_registry import DeviceRegistry
from app.devices.device_service import DeviceService

# Importamos o barramento global que criamos na Fase 8.3
from app.events import event_bus

# Instâncias globais do ecossistema de dispositivos
device_registry = DeviceRegistry()
device_service = DeviceService(registry=device_registry, bus=event_bus)

__all__ = [
    "DeviceRegistry",
    "device_registry",
    "DeviceService",
    "device_service"
]