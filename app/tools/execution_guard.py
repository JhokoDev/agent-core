from typing import Any

from app.permissions.permission_service import PermissionService
from app.tools.tool_contract import ToolContract
from app.tools.tool_validator import validar_argumentos


class ExecutionGuard:
    """
    Barreira final entre uma solicitação de execução
    e o handler real de uma ferramenta.
    """

    def __init__(
        self,
        permission_service: PermissionService,
    ):
        self.permission_service = permission_service

    def executar(
        self,
        contexto_id: str,
        ferramenta: ToolContract,
        argumentos: dict[str, Any],
    ) -> Any:
        """
        Executa uma ferramenta somente se todas as
        verificações de segurança forem aprovadas.
        """

        permissao = self.permission_service.avaliar(
            contexto_id=contexto_id,
            ferramenta=ferramenta,
        )

        if permissao.estado == "negada":
            return (
                "Erro de permissão: "
                f"{permissao.motivo}"
            )

        if (
            permissao.estado
            == "aguardando_confirmacao"
        ):
            return (
                f"A ferramenta '{ferramenta.id}' "
                "requer confirmação antes da execução."
            )

        valido, erro = validar_argumentos(
            ferramenta,
            argumentos,
        )

        if not valido:
            return (
                f"Erro de argumentos: {erro}"
            )

        if ferramenta.handler is None:
            return (
                f"A ferramenta '{ferramenta.id}' "
                "não possui handler genérico."
            )

        try:
            return ferramenta.handler(
                argumentos
            )

        except Exception as exc:
            return (
                f"Erro ao executar a ferramenta "
                f"'{ferramenta.id}': {exc}"
            )