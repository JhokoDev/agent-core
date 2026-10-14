from dataclasses import dataclass, field
from typing import Any


TIPOS_DOCUMENTO_VALIDOS = {
    "text",
    "markdown",
    "code",
    "pdf",
    "html",
    "json",
}


@dataclass
class DocumentContract:
    id: str
    conteudo: str
    nome: str
    tipo: str = "text"
    origem: str = "local"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validar(self) -> tuple[bool, str]:
        if not self.id.strip():
            return False, "O documento precisa possuir um ID."

        if not self.nome.strip():
            return False, "O documento precisa possuir um nome."

        if not self.conteudo.strip():
            return False, "O documento precisa possuir conteúdo."

        if self.tipo not in TIPOS_DOCUMENTO_VALIDOS:
            return False, (
                f"Tipo de documento inválido: '{self.tipo}'."
            )

        if not isinstance(self.metadata, dict):
            return False, (
                "Os metadados do documento devem ser um objeto."
            )

        return True, ""