from app.permissions.permission_context import PermissionContext


class PermissionContextRegistry:
    def __init__(self):
        self._contextos: dict[str, PermissionContext] = {}

    def registrar(
        self,
        contexto: PermissionContext,
    ) -> None:
        valido, erro = contexto.validar()

        if not valido:
            raise ValueError(
                f"Contexto inválido: {erro}"
            )

        if contexto.id in self._contextos:
            # Idempotente: atualiza o contexto existente sem erro em turnos subsequentes do chat
            self._contextos[contexto.id] = contexto
            return

        self._contextos[contexto.id] = contexto

    def obter(
        self,
        contexto_id: str,
    ) -> PermissionContext | None:
        return self._contextos.get(contexto_id)

    def existe(
        self,
        contexto_id: str,
    ) -> bool:
        return contexto_id in self._contextos

    def listar(
        self,
        tipo: str | None = None,
    ) -> list[PermissionContext]:
        contextos = list(
            self._contextos.values()
        )

        if tipo is None:
            return contextos

        return [
            contexto
            for contexto in contextos
            if contexto.tipo == tipo
        ]

    def remover(
        self,
        contexto_id: str,
    ) -> bool:
        if contexto_id not in self._contextos:
            return False

        del self._contextos[contexto_id]
        return True

    def limpar(self) -> None:
        self._contextos.clear()