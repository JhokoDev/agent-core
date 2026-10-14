from app.permissions.permission_context import PermissionContext
from app.permissions.permission_context_registry import PermissionContextRegistry
from app.permissions.permission_contract import PermissionContract
from app.permissions.permission_engine import PermissionEngine
from app.permissions.permission_registry import PermissionRegistry
from app.tools.tool_contract import ToolContract


class PermissionService:
    def __init__(
        self,
        engine: PermissionEngine,
        permission_registry: PermissionRegistry,
        context_registry: PermissionContextRegistry,
    ):
        self.engine = engine
        self.permission_registry = permission_registry
        self.context_registry = context_registry

    def registrar_contexto(
        self,
        contexto: PermissionContext,
    ) -> None:
        self.context_registry.registrar(contexto)

    def avaliar(
        self,
        contexto_id: str,
        ferramenta: ToolContract,
    ) -> PermissionContract:

        contexto = self.context_registry.obter(
            contexto_id
        )

        if contexto is None:
            permissao = PermissionContract(
                contexto_id=contexto_id,
                ferramenta_id=ferramenta.id,
                estado="negada",
                risco=ferramenta.risco,
                requer_confirmacao=ferramenta.requer_confirmacao,
                motivo=(
                    "Contexto de permissão não registrado."
                ),
            )

            self._registrar_permissao(permissao)

            return permissao

        permissao = self.engine.avaliar(
            contexto.id,
            ferramenta,
        )

        return permissao

    def confirmar(
        self,
        contexto_id: str,
        ferramenta_id: str,
    ) -> PermissionContract:

        permissao = self.permission_registry.obter(
            contexto_id,
            ferramenta_id,
        )

        if permissao is None:
            raise ValueError(
                "Permissão não encontrada."
            )

        return self.engine.confirmar(
            permissao
        )

    def obter_permissao(
        self,
        contexto_id: str,
        ferramenta_id: str,
    ) -> PermissionContract | None:
        return self.permission_registry.obter(
            contexto_id,
            ferramenta_id,
        )

    def _registrar_permissao(
        self,
        permissao: PermissionContract,
    ) -> None:
        existente = self.permission_registry.obter(
            permissao.contexto_id,
            permissao.ferramenta_id,
        )

        if existente is not None:
            self.permission_registry.remover(
                permissao.contexto_id,
                permissao.ferramenta_id,
            )

        self.permission_registry.registrar(
            permissao
        )