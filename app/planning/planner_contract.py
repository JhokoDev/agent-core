from dataclasses import dataclass, field
from typing import Any


ESTADOS_ETAPA_VALIDOS = {
    "pendente",
    "executando",
    "concluida",
    "falhou",
    "cancelada",
}


@dataclass
class PlanStep:
    id: str
    descricao: str
    estado: str = "pendente"
    ferramenta: str | None = None
    argumentos: dict[str, Any] = field(default_factory=dict)
    resultado: Any = None
    erro: str | None = None


@dataclass
class PlannerContract:
    objetivo: str
    etapas: list[PlanStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validar(self) -> tuple[bool, str]:
        if not self.objetivo.strip():
            return False, "O plano precisa possuir um objetivo."

        ids: set[str] = set()

        for etapa in self.etapas:
            if not etapa.id:
                return False, "Toda etapa precisa possuir um ID."

            if etapa.id in ids:
                return False, (
                    f"A etapa '{etapa.id}' está duplicada."
                )

            ids.add(etapa.id)

            if not etapa.descricao.strip():
                return False, (
                    f"A etapa '{etapa.id}' precisa possuir uma descrição."
                )

            if etapa.estado not in ESTADOS_ETAPA_VALIDOS:
                return False, (
                    f"A etapa '{etapa.id}' possui estado inválido: "
                    f"'{etapa.estado}'."
                )

        return True, ""