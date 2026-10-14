from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouterContract:
    """
    Resultado normalizado da decisão do Router.

    O Router não executa a solicitação.
    Ele apenas determina qual fluxo deve processá-la.
    """

    rota: str

    modelo: str | None = None

    skill_id: str | None = None

    motivo: str = ""

    confianca: float | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )