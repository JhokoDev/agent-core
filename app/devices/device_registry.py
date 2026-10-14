from datetime import datetime
from app.devices.device_contract import DeviceInfo

class DeviceRegistry:
    """
    Registo central de todos os dispositivos conhecidos pelo Agent Core.
    Mantém o estado atual e a data da última comunicação (heartbeat).
    """

    def __init__(self):
        # Mapeia o device_id para o objeto DeviceInfo
        self._devices: dict[str, DeviceInfo] = {}

    def registrar(self, device: DeviceInfo) -> None:
        """Adiciona ou atualiza as configurações de um dispositivo."""
        self._devices[device.id] = device

    def obter(self, device_id: str) -> DeviceInfo | None:
        """Recupera as informações de um dispositivo pelo seu ID."""
        return self._devices.get(device_id)

    def listar_todos(self) -> list[DeviceInfo]:
        """Retorna a lista de todos os dispositivos registados."""
        return list(self._devices.values())

    def atualizar_status(self, device_id: str, status: str) -> bool:
        """Força a atualização do status (online/offline/erro) de um dispositivo."""
        device = self.obter(device_id)
        if device:
            device.status = status
            device.ultima_comunicacao = datetime.now()
            return True
        return False

    def ping(self, device_id: str) -> bool:
        """
        Atualiza a data de última comunicação. 
        Se estava offline, passa a online automaticamente.
        """
        device = self.obter(device_id)
        if device:
            device.ultima_comunicacao = datetime.now()
            if device.status == "offline":
                device.status = "online"
            return True
        return False