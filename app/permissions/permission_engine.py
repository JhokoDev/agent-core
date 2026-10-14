from app.permissions.permission_contract import PermissionContract
from app.permissions.permission_registry import PermissionRegistry
from app.tools.tool_contract import ToolContract
from app.tools.tool_permissions import ToolPermissionPolicy


class PermissionEngine:
    def __init__(
        self,
        policy: ToolPermissionPolicy,
        registry: PermissionRegistry | None = None,
    ):
        self.policy = policy
        self.registry = registry or PermissionRegistry()

    def avaliar(
        self,
        contexto_id: str,
        ferramenta: ToolContract,
    ) -> PermissionContract:

        if not contexto_id.strip():
            permissao = PermissionContract(
                contexto_id=contexto_id,
                ferramenta_id=ferramenta.id,
                estado="negada",
                risco=ferramenta.risco,
                requer_confirmacao=ferramenta.requer_confirmacao,
                motivo="Contexto de execução não informado.",
            )

            self._registrar(permissao)
            return permissao

        permitida = self.policy.permitir(
            contexto_id,
            ferramenta,
        )

        if not permitida:
            permissao = PermissionContract(
                contexto_id=contexto_id,
                ferramenta_id=ferramenta.id,
                estado="negada",
                risco=ferramenta.risco,
                requer_confirmacao=ferramenta.requer_confirmacao,
                motivo=(
                    "A ferramenta não está autorizada "
                    "para este contexto."
                ),
            )

            self._registrar(permissao)
            return permissao

        if ferramenta.requer_confirmacao:
            permissao = PermissionContract(
                contexto_id=contexto_id,
                ferramenta_id=ferramenta.id,
                estado="aguardando_confirmacao",
                risco=ferramenta.risco,
                requer_confirmacao=True,
                motivo=(
                    "A ferramenta exige confirmação "
                    "antes da execução."
                ),
            )

            self._registrar(permissao)
            return permissao

        permissao = PermissionContract(
            contexto_id=contexto_id,
            ferramenta_id=ferramenta.id,
            estado="autorizada",
            risco=ferramenta.risco,
            requer_confirmacao=False,
            motivo="Ferramenta autorizada para execução.",
        )

        self._registrar(permissao)
        return permissao

    def confirmar(
        self,
        permissao: PermissionContract,
    ) -> PermissionContract:

        if permissao.estado != "aguardando_confirmacao":
            raise ValueError(
                "Somente permissões aguardando confirmação "
                "podem ser confirmadas."
            )

        permissao.estado = "autorizada"
        permissao.motivo = (
            "Execução confirmada explicitamente."
        )

        self._registrar(permissao)

        return permissao

    def _registrar(
        self,
        permissao: PermissionContract,
    ) -> None:
        chave_existente = self.registry.obter(
            permissao.contexto_id,
            permissao.ferramenta_id,
        )

        if chave_existente is not None:
            self.registry.remover(
                permissao.contexto_id,
                permissao.ferramenta_id,
            )

        self.registry.registrar(permissao)