from app.tools.tool_contract import ToolContract


class ToolPermissionPolicy:
    def __init__(self):
        self._permissoes: dict[str, set[str]] = {}

    def definir_permissoes(
        self,
        contexto_id: str,
        ferramentas: list[str],
    ) -> None:
        self._permissoes[contexto_id] = set(ferramentas)

    def permitir(
        self,
        contexto_id: str,
        ferramenta: ToolContract,
    ) -> bool:
        ferramentas_permitidas = self._permissoes.get(
            contexto_id,
            set(),
        )

        return ferramenta.id in ferramentas_permitidas

    def listar_permitidas(
        self,
        contexto_id: str,
    ) -> list[str]:
        return sorted(
            self._permissoes.get(contexto_id, set())
        )

    def remover_contexto(self, contexto_id: str) -> None:
        self._permissoes.pop(contexto_id, None)

    def limpar(self) -> None:
        self._permissoes.clear()

    def carregar_skill(
        self,
        contexto_id: str,
        ferramentas_permitidas: list[str] | None,
    ) -> None:
        self.definir_permissoes(
            contexto_id,
            ferramentas_permitidas or [],
        )