from pydantic import BaseModel, Field
from typing import Any, Literal
from datetime import datetime

class DeviceCapability(BaseModel):
    """Representa uma ação que um dispositivo pode executar (ex: 'ligar_rele', 'ler_temperatura')."""
    nome: str
    descricao: str
    parametros: dict[str, Any] = Field(default_factory=dict)

class DeviceInfo(BaseModel):
    """Contrato que representa um dispositivo físico ou virtual registado no sistema."""
    id: str = Field(description="Identificador único do dispositivo (ex: mac_address ou nome descritivo)")
    nome: str = Field(description="Nome amigável do dispositivo (ex: 'Sensor Sala')")
    tipo: Literal["esp32", "raspberry_pi", "windows_bridge", "kicad", "outros"]
    status: Literal["online", "offline", "erro"] = "offline"
    capacidades: list[DeviceCapability] = Field(default_factory=list)
    ultima_comunicacao: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)