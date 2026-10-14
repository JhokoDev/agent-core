from dataclasses import dataclass, field
from typing import Any


ESTADOS_PERMISSAO_VALIDOS = {
    "pendente",
    "autorizada",
    "negada",
    "aguardando_confirmacao",
}


@dataclass
class PermissionContract:
    contexto_id: str
    ferramenta_id: str
    estado: str = "pendente"
    risco: str = "baixo"
    requer_confirmacao: bool = False
    motivo: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def validar(self) -> tuple[bool, str]:
        if not self.contexto_id.strip():
            return False, (
                "A permissão precisa possuir um contexto_id."
            )

        if not self.ferramenta_id.strip():
            return False, (
                "A permissão precisa possuir um ferramenta_id."
            )

        if self.estado not in ESTADOS_PERMISSAO_VALIDOS:
            return False, (
                f"Estado de permissão inválido: "
                f"'{self.estado}'."
            )

        if not self.risco.strip():
            return False, (
                "A permissão precisa possuir um nível de risco."
            )

        if not isinstance(
            self.requer_confirmacao,
            bool,
        ):
            return False, (
                "requer_confirmacao deve ser booleano."
            )

        if not isinstance(self.metadata, dict):
            return False, (
                "Os metadados da permissão devem ser um objeto."
            )

        return True, ""