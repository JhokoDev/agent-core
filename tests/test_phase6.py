from app.permission_contract import PermissionContract
from app.permission_context import PermissionContext
from app.permission_context_registry import (
    PermissionContextRegistry,
)
from app.permission_engine import PermissionEngine
from app.permission_registry import PermissionRegistry
from app.permission_service import PermissionService
from app.execution_guard import ExecutionGuard
from app.tool_permissions import ToolPermissionPolicy
from app.tool_registry import criar_registry_padrao


def criar_ambiente():
    registry = criar_registry_padrao()

    policy = ToolPermissionPolicy()

    permission_registry = PermissionRegistry()

    context_registry = PermissionContextRegistry()

    engine = PermissionEngine(
        policy=policy,
        registry=permission_registry,
    )

    service = PermissionService(
        engine=engine,
        permission_registry=permission_registry,
        context_registry=context_registry,
    )

    guard = ExecutionGuard(
        permission_service=service,
    )

    return {
        "registry": registry,
        "policy": policy,
        "permission_registry": permission_registry,
        "context_registry": context_registry,
        "engine": engine,
        "service": service,
        "guard": guard,
    }


# ==========================================
# 6.1 — Permission Contract
# ==========================================

def testar_permission_contract():
    permissao = PermissionContract(
        contexto_id="skill_teste",
        ferramenta_id="calcular",
        estado="autorizada",
        risco="baixo",
    )

    valido, erro = permissao.validar()

    assert valido
    assert erro == ""


# ==========================================
# 6.2 — Permission Engine
# ==========================================

def testar_permission_engine():
    ambiente = criar_ambiente()

    contexto_id = "skill_teste"

    ambiente["service"].registrar_contexto(
        PermissionContext(
            id=contexto_id,
            tipo="skill",
        )
    )

    ambiente["policy"].definir_permissoes(
        contexto_id,
        ["calcular"],
    )

    ferramenta = ambiente[
        "registry"
    ].obter("calcular")

    assert ferramenta is not None

    permissao = ambiente[
        "engine"
    ].avaliar(
        contexto_id,
        ferramenta,
    )

    assert permissao.estado == "autorizada"


# ==========================================
# 6.3 — Permission Registry
# ==========================================

def testar_permission_registry():
    registry = PermissionRegistry()

    permissao = PermissionContract(
        contexto_id="skill_teste",
        ferramenta_id="calcular",
        estado="autorizada",
    )

    registry.registrar(
        permissao
    )

    assert registry.existe(
        "skill_teste",
        "calcular",
    )

    recuperada = registry.obter(
        "skill_teste",
        "calcular",
    )

    assert recuperada is not None
    assert recuperada.estado == "autorizada"


# ==========================================
# 6.4 — Engine + Registry
# ==========================================

def testar_engine_registra_decisao():
    ambiente = criar_ambiente()

    contexto_id = "skill_teste"

    ambiente["service"].registrar_contexto(
        PermissionContext(
            id=contexto_id,
            tipo="skill",
        )
    )

    ambiente["policy"].definir_permissoes(
        contexto_id,
        ["calcular"],
    )

    ferramenta = ambiente[
        "registry"
    ].obter("calcular")

    permissao = ambiente[
        "engine"
    ].avaliar(
        contexto_id,
        ferramenta,
    )

    registrada = ambiente[
        "permission_registry"
    ].obter(
        contexto_id,
        "calcular",
    )

    assert permissao is registrada


# ==========================================
# 6.5 — Permission Context
# ==========================================

def testar_permission_context():
    contexto = PermissionContext(
        id="skill_codigo",
        tipo="skill",
        origem="services.py",
    )

    valido, erro = contexto.validar()

    assert valido
    assert erro == ""


# ==========================================
# 6.6 — Context Registry
# ==========================================

def testar_context_registry():
    registry = PermissionContextRegistry()

    contexto = PermissionContext(
        id="skill_codigo",
        tipo="skill",
    )

    registry.registrar(
        contexto
    )

    assert registry.existe(
        "skill_codigo"
    )

    recuperado = registry.obter(
        "skill_codigo"
    )

    assert recuperado is not None
    assert recuperado.id == "skill_codigo"


# ==========================================
# 6.7 — Permission Service
# ==========================================

def testar_permission_service():
    ambiente = criar_ambiente()

    contexto_id = "skill_teste"

    ambiente["service"].registrar_contexto(
        PermissionContext(
            id=contexto_id,
            tipo="skill",
        )
    )

    ambiente["policy"].definir_permissoes(
        contexto_id,
        ["calcular"],
    )

    ferramenta = ambiente[
        "registry"
    ].obter("calcular")

    permissao = ambiente[
        "service"
    ].avaliar(
        contexto_id,
        ferramenta,
    )

    assert permissao.estado == "autorizada"


def testar_service_bloqueia_tool():
    ambiente = criar_ambiente()

    contexto_id = "skill_teste"

    ambiente["service"].registrar_contexto(
        PermissionContext(
            id=contexto_id,
            tipo="skill",
        )
    )

    ambiente["policy"].definir_permissoes(
        contexto_id,
        ["calcular"],
    )

    ferramenta = ambiente[
        "registry"
    ].obter(
        "terminal_dinamico"
    )

    permissao = ambiente[
        "service"
    ].avaliar(
        contexto_id,
        ferramenta,
    )

    assert permissao.estado == "negada"


# ==========================================
# 6.8 — Services Integration
# ==========================================

def testar_contexto_registrado():
    ambiente = criar_ambiente()

    contexto_id = "skill_codigo"

    ambiente["service"].registrar_contexto(
        PermissionContext(
            id=contexto_id,
            tipo="skill",
        )
    )

    assert ambiente[
        "context_registry"
    ].existe(contexto_id)


# ==========================================
# 6.9 — Execution Guard
# ==========================================

def testar_guard_execucao_autorizada():
    ambiente = criar_ambiente()

    contexto_id = "skill_teste"

    ambiente["service"].registrar_contexto(
        PermissionContext(
            id=contexto_id,
            tipo="skill",
        )
    )

    ambiente["policy"].definir_permissoes(
        contexto_id,
        ["calcular"],
    )

    ferramenta = ambiente[
        "registry"
    ].obter("calcular")

    resultado = ambiente[
        "guard"
    ].executar(
        contexto_id=contexto_id,
        ferramenta=ferramenta,
        argumentos={
            "expressao": "2 + 2",
        },
    )

    assert resultado is not None


def testar_guard_bloqueia_execucao():
    ambiente = criar_ambiente()

    contexto_id = "skill_teste"

    ambiente["service"].registrar_contexto(
        PermissionContext(
            id=contexto_id,
            tipo="skill",
        )
    )

    ambiente["policy"].definir_permissoes(
        contexto_id,
        ["calcular"],
    )

    ferramenta = ambiente[
        "registry"
    ].obter(
        "terminal_dinamico"
    )

    resultado = ambiente[
        "guard"
    ].executar(
        contexto_id=contexto_id,
        ferramenta=ferramenta,
        argumentos={
            "comando": "teste",
        },
    )

    assert "Erro de permissão" in resultado


def testar_guard_valida_argumentos():
    ambiente = criar_ambiente()

    contexto_id = "skill_teste"

    ambiente["service"].registrar_contexto(
        PermissionContext(
            id=contexto_id,
            tipo="skill",
        )
    )

    ambiente["policy"].definir_permissoes(
        contexto_id,
        ["calcular"],
    )

    ferramenta = ambiente[
        "registry"
    ].obter("calcular")

    resultado = ambiente[
        "guard"
    ].executar(
        contexto_id=contexto_id,
        ferramenta=ferramenta,
        argumentos={},
    )

    assert "Erro de argumentos" in resultado


# ==========================================
# EXECUÇÃO
# ==========================================

if __name__ == "__main__":

    testar_permission_contract()
    print("[OK] Permission Contract")

    testar_permission_engine()
    print("[OK] Permission Engine")

    testar_permission_registry()
    print("[OK] Permission Registry")

    testar_engine_registra_decisao()
    print("[OK] Engine + Registry")

    testar_permission_context()
    print("[OK] Permission Context")

    testar_context_registry()
    print("[OK] Permission Context Registry")

    testar_permission_service()
    print("[OK] Permission Service")

    testar_service_bloqueia_tool()
    print("[OK] Permission Service bloqueia Tool")

    testar_contexto_registrado()
    print("[OK] Services registra contexto")

    testar_guard_execucao_autorizada()
    print("[OK] Execution Guard permite execução")

    testar_guard_bloqueia_execucao()
    print("[OK] Execution Guard bloqueia execução")

    testar_guard_valida_argumentos()
    print("[OK] Execution Guard valida argumentos")

    print()
    print("========================================")
    print("PHASE 6 — PERMISSIONS")
    print("========================================")
    print("TODOS OS TESTES PASSARAM")
    print("PHASE 6: CONCLUÍDA")