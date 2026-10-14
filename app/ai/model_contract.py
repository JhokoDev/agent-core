from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelContract:
    """
    Representa um modelo de IA de forma independente
    do provider utilizado para executá-lo.
    """

    id: str
    nome: str
    provider: str = "ollama"

    descricao: str = ""

    suporta_tools: bool = False
    suporta_vision: bool = False

    contexto_maximo: int | None = None

    capacidades: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validar(self) -> tuple[bool, str]:
        if not self.id.strip():
            return False, (
                "O modelo precisa possuir um ID."
            )

        if not self.nome.strip():
            return False, (
                "O modelo precisa possuir um nome."
            )

        if not self.provider.strip():
            return False, (
                "O modelo precisa possuir um provider."
            )

        if self.contexto_maximo is not None:
            if self.contexto_maximo <= 0:
                return False, (
                    "O contexto máximo deve ser maior que zero."
                )

        if not isinstance(self.capacidades, list):
            return False, (
                "As capacidades devem ser uma lista."
            )

        if not isinstance(self.metadata, dict):
            return False, (
                "Os metadados devem ser um objeto."
            )

        return True, ""