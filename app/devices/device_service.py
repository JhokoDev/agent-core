from app.devices.device_registry import DeviceRegistry
from app.events.event_bus import EventBus
from app.events.event_contract import HardwareSensorEvent

class DeviceService:
    """
    Serviço que reage a eventos do sistema para gerir automaticamente 
    o estado e a disponibilidade dos dispositivos no Registry.
    """

    def __init__(self, registry: DeviceRegistry, bus: EventBus):
        self.registry = registry
        self.bus = bus
        
        # Ouve os eventos de sensores. Se um sensor enviou dados, 
        # significa que o dispositivo está vivo (Ping automático).
        self.bus.subscribe("hardware_sensor", self._handle_hardware_sensor)

    async def _handle_hardware_sensor(self, event: HardwareSensorEvent) -> None:
        """Atualiza o 'heartbeat' do dispositivo sempre que ele envia um evento."""
        device_id = event.device_id
        
        # Se o dispositivo existir no registo, atualiza a última comunicação
        sucesso = self.registry.ping(device_id)
        
        if not sucesso:
            print(f"[DeviceService] Aviso: Recebida leitura de sensor de dispositivo não registado: '{device_id}'")