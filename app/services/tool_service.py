from typing import Any
from app.tools.tool_registry import criar_registry_padrao
from app.tools.tool_permissions import ToolPermissionPolicy
from app.permissions.permission_context import PermissionContext
from app.permissions.permission_context_registry import PermissionContextRegistry
from app.permissions.permission_engine import PermissionEngine
from app.permissions.permission_registry import PermissionRegistry
from app.permissions.permission_service import PermissionService
from app.tools.execution_guard import ExecutionGuard

class ToolService:
    """Isola a lógica de carregamento, permissão e execução de ferramentas."""

    def __init__(self):
        self.registry = criar_registry_padrao()
        self.policy = ToolPermissionPolicy()
        self.perm_registry = PermissionRegistry()
        self.context_registry = PermissionContextRegistry()
        
        self.engine = PermissionEngine(
            policy=self.policy,
            registry=self.perm_registry,
        )
        self.perm_service = PermissionService(
            engine=self.engine,
            permission_registry=self.perm_registry,
            context_registry=self.context_registry,
        )
        self.guard = ExecutionGuard(permission_service=self.perm_service)

    def carregar_permissoes_skill(self, contexto_id: str, ferramentas_permitidas: list[str] | None) -> None:
        todas_ferramentas = list(self.registry._ferramentas.keys())
        ferramentas = ferramentas_permitidas or todas_ferramentas
        if not self.context_registry.existe(contexto_id):
            contexto = PermissionContext(id=contexto_id, tipo="skill")
            self.context_registry.registrar(contexto)
        self.policy.carregar_skill(contexto_id, ferramentas)

    def obter_schemas_da_skill(self, ferramentas_permitidas: list[str] | None) -> list[dict]:
        todas_ferramentas = list(self.registry._ferramentas.keys())
        ferramentas = ferramentas_permitidas or todas_ferramentas
        return self.registry.gerar_schemas_ollama(ferramentas)

    def executar(self, contexto_id: str, ferramenta_id: str, argumentos: dict[str, Any]) -> Any:
        ferramenta = self.registry.obter(ferramenta_id)
        if ferramenta is None:
            raise ValueError(f"Ferramenta '{ferramenta_id}' não encontrada.")
            
        return self.guard.executar(
            contexto_id=contexto_id, 
            ferramenta=ferramenta, 
            argumentos=argumentos
        )