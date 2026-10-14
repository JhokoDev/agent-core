from app.adapters.mqtt_adapter import MqttAdapter
from app.events import event_bus
from app.devices import device_registry
import os

# Pode configurar o IP do seu Mosquitto (ou outro broker) via variáveis de ambiente
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

mqtt_adapter = MqttAdapter(
    bus=event_bus, 
    device_registry=device_registry, 
    broker_url=MQTT_BROKER, 
    port=MQTT_PORT
)

__all__ = ["MqttAdapter", "mqtt_adapter"]