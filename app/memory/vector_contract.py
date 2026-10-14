from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorDocument:
    id: str
    documento_id: str
    conteudo: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def validar(self) -> tuple[bool, str]:
        if not self.id.strip():
            return False, "O vetor precisa possuir um ID."

        if not self.documento_id.strip():
            return False, (
                "O vetor precisa possuir um documento_id."
            )

        if not self.conteudo.strip():
            return False, (
                "O vetor precisa possuir conteúdo."
            )

        if not isinstance(self.embedding, list):
            return False, (
                "O embedding deve ser uma lista."
            )

        if not self.embedding:
            return False, (
                "O embedding não pode estar vazio."
            )

        if not all(
            isinstance(valor, (int, float))
            and not isinstance(valor, bool)
            for valor in self.embedding
        ):
            return False, (
                "Todos os valores do embedding "
                "devem ser numéricos."
            )

        if not isinstance(self.metadata, dict):
            return False, (
                "Os metadados devem ser um objeto."
            )

        return True, ""