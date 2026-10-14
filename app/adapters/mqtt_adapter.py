import asyncio
import json
import aiomqtt
from app.events.event_bus import EventBus
from app.events.command_contract import HardwareActionCommand
from app.events.event_contract import HardwareSensorEvent
from app.devices.device_registry import DeviceRegistry

class MqttAdapter:
    """
    Adaptador assíncrono para ligar o Event Bus do Agent Core a uma rede MQTT (IoT).
    """

    def __init__(
        self, 
        bus: EventBus, 
        device_registry: DeviceRegistry,
        broker_url: str = "localhost", 
        port: int = 1883
    ):
        self.bus = bus
        self.registry = device_registry
        self.broker_url = broker_url
        self.port = port
        self._client: aiomqtt.Client | None = None
        self._task: asyncio.Task | None = None

        # Ouve comandos do Event Bus para os reencaminhar para o hardware via MQTT
        self.bus.subscribe("hardware_action", self._handle_hardware_action)

    async def iniciar(self):
        """Inicia a ligação MQTT em background."""
        self._task = asyncio.create_task(self._conectar_e_ouvir())

    async def _conectar_e_ouvir(self):
        """Mantém a ligação MQTT aberta, subscreve tópicos e processa mensagens recebidas."""
        try:
            async with aiomqtt.Client(hostname=self.broker_url, port=self.port) as client:
                self._client = client
                print(f"[MQTT Adapter] Ligado ao broker {self.broker_url}:{self.port}")
                
                # Subscreve o tópico genérico onde os sensores (ESP32/Raspberry) publicam dados
                await client.subscribe("agent/+/sensores/#")
                
                async for message in client.messages:
                    await self._processar_mensagem_mqtt(message)
        except aiomqtt.MqttError as e:
            print(f"[MQTT Adapter] Erro de ligação: {e}. A tentar reconectar em 5s...")
            await asyncio.sleep(5)
            await self.iniciar() # Tenta reconectar

    async def _processar_mensagem_mqtt(self, message: aiomqtt.Message):
        """Converte uma mensagem MQTT recebida num Evento oficial do sistema."""
        try:
            topico = str(message.topic)
            payload_str = message.payload.decode("utf-8") if isinstance(message.payload, bytes) else str(message.payload)
            
            # Formato esperado do tópico: agent/{device_id}/sensores/{sensor_tipo}
            partes = topico.split("/")
            if len(partes) >= 4:
                device_id = partes[1]
                sensor_tipo = partes[3]
                
                dados = json.loads(payload_str)
                leitura = dados.get("valor", dados)
                unidade = dados.get("unidade", None)

                # Cria o evento e injeta no Event Bus
                evento = HardwareSensorEvent(
                    device_id=device_id,
                    sensor_tipo=sensor_tipo,
                    leitura=leitura,
                    unidade=unidade
                )
                await self.bus.publish(evento)
                
        except Exception as e:
            print(f"[MQTT Adapter] Erro ao processar payload MQTT: {e}")

    async def _handle_hardware_action(self, command: HardwareActionCommand):
        """Converte um Comando do Event Bus numa publicação MQTT para o hardware."""
        if not self._client:
            print("[MQTT Adapter] Aviso: Cliente MQTT não está ligado. Comando ignorado.")
            return

        try:
            # Formato do tópico de saída: agent/{device_id}/acoes
            topico_destino = f"agent/{command.device_id}/acoes"
            
            payload = {
                "instrucao": command.instrucao,
                "parametros": command.parametros,
                "command_id": command.id
            }
            
            await self._client.publish(
                topico_destino, 
                payload=json.dumps(payload, ensure_ascii=False)
            )
            print(f"[MQTT Adapter] Comando enviado para {topico_destino}: {command.instrucao}")
        except Exception as e:
            print(f"[MQTT Adapter] Erro ao publicar ação MQTT: {e}")