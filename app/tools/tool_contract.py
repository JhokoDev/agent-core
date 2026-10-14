from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolContract:
    id: str
    nome: str
    descricao: str
    categoria: str = "geral"
    risco: str = "baixo"
    argumentos: dict[str, Any] = field(default_factory=dict)
    requer_confirmacao: bool = False
    handler: Callable[[dict], Any] | None = None