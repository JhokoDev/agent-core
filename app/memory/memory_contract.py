from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


TIPOS_MEMORIA_VALIDOS = {
    "fact",
    "preference",
    "context",
    "summary",
}


@dataclass
class MemoryContract:
    id: str
    conteudo: str
    tipo: str = "context"
    origem: str = "conversation"
    importancia: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    criado_em: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def validar(self) -> tuple[bool, str]:
        if not self.id.strip():
            return False, "A memória precisa possuir um ID."

        if not self.conteudo.strip():
            return False, "A memória precisa possuir conteúdo."

        if self.tipo not in TIPOS_MEMORIA_VALIDOS:
            return False, (
                f"Tipo de memória inválido: '{self.tipo}'."
            )

        if not 0.0 <= self.importancia <= 1.0:
            return False, (
                "A importância deve estar entre 0.0 e 1.0."
            )

        if not isinstance(self.metadata, dict):
            return False, (
                "Os metadados da memória devem ser um objeto."
            )

        return True, ""