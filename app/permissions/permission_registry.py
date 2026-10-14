from app.permissions.permission_contract import PermissionContract


class PermissionRegistry:
    def __init__(self):
        self._permissoes: dict[
            str,
            PermissionContract,
        ] = {}

    def registrar(
        self,
        permissao: PermissionContract,
    ) -> None:
        valido, erro = permissao.validar()

        if not valido:
            raise ValueError(
                f"Permissão inválida: {erro}"
            )

        chave = self._gerar_chave(
            permissao.contexto_id,
            permissao.ferramenta_id,
        )

        if chave in self._permissoes:
            raise ValueError(
                "A permissão já está registrada."
            )

        self._permissoes[chave] = permissao

    def obter(
        self,
        contexto_id: str,
        ferramenta_id: str,
    ) -> PermissionContract | None:
        chave = self._gerar_chave(
            contexto_id,
            ferramenta_id,
        )

        return self._permissoes.get(chave)

    def existe(
        self,
        contexto_id: str,
        ferramenta_id: str,
    ) -> bool:
        return (
            self.obter(
                contexto_id,
                ferramenta_id,
            )
            is not None
        )

    def listar(
        self,
        contexto_id: str | None = None,
    ) -> list[PermissionContract]:
        permissoes = list(
            self._permissoes.values()
        )

        if contexto_id is None:
            return permissoes

        return [
            permissao
            for permissao in permissoes
            if permissao.contexto_id == contexto_id
        ]

    def remover(
        self,
        contexto_id: str,
        ferramenta_id: str,
    ) -> bool:
        chave = self._gerar_chave(
            contexto_id,
            ferramenta_id,
        )

        if chave not in self._permissoes:
            return False

        del self._permissoes[chave]
        return True

    def limpar(self) -> None:
        self._permissoes.clear()

    def _gerar_chave(
        self,
        contexto_id: str,
        ferramenta_id: str,
    ) -> str:
        return f"{contexto_id}:{ferramenta_id}"