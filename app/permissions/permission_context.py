from dataclasses import dataclass, field
from typing import Any


TIPOS_CONTEXTO_VALIDOS = {
    "skill",
    "chat",
    "agent",
    "system",
}


@dataclass
class PermissionContext:
    id: str
    tipo: str
    origem: str = ""
    descricao: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def validar(self) -> tuple[bool, str]:
        if not self.id.strip():
            return False, (
                "O contexto precisa possuir um ID."
            )

        if self.tipo not in TIPOS_CONTEXTO_VALIDOS:
            return False, (
                f"Tipo de contexto inválido: "
                f"'{self.tipo}'."
            )

        if not isinstance(self.metadata, dict):
            return False, (
                "Os metadados do contexto "
                "devem ser um objeto."
            )

        return True, ""