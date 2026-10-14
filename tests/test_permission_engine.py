from app.permission_contract import PermissionContract
from app.permission_engine import PermissionEngine
from app.tool_contract import ToolContract
from app.tool_permissions import ToolPermissionPolicy


def criar_ferramenta(
    ferramenta_id: str,
    risco: str = "baixo",
    confirmacao: bool = False,
) -> ToolContract:
    return ToolContract(
        id=ferramenta_id,
        nome=ferramenta_id,
        descricao="Ferramenta de teste.",
        risco=risco,
        requer_confirmacao=confirmacao,
    )


def criar_engine() -> tuple[
    PermissionEngine,
    ToolPermissionPolicy,
]:
    policy = ToolPermissionPolicy()

    policy.definir_permissoes(
        "skill_teste",
        [
            "calcular",
            "terminal_dinamico",
        ],
    )

    return PermissionEngine(policy), policy


def testar_ferramenta_autorizada():
    engine, _ = criar_engine()

    ferramenta = criar_ferramenta(
        "calcular",
        risco="baixo",
    )

    permissao = engine.avaliar(
        "skill_teste",
        ferramenta,
    )

    assert permissao.estado == "autorizada"
    assert permissao.risco == "baixo"


def testar_ferramenta_nao_autorizada():
    engine, _ = criar_engine()

    ferramenta = criar_ferramenta(
        "ler_arquivo_codigo",
    )

    permissao = engine.avaliar(
        "skill_teste",
        ferramenta,
    )

    assert permissao.estado == "negada"


def testar_confirmacao_obrigatoria():
    engine, _ = criar_engine()

    ferramenta = criar_ferramenta(
        "terminal_dinamico",
        risco="alto",
        confirmacao=True,
    )

    permissao = engine.avaliar(
        "skill_teste",
        ferramenta,
    )

    assert (
        permissao.estado
        == "aguardando_confirmacao"
    )

    assert permissao.requer_confirmacao is True


def testar_confirmacao_autoriza():
    engine, _ = criar_engine()

    ferramenta = criar_ferramenta(
        "terminal_dinamico",
        risco="alto",
        confirmacao=True,
    )

    permissao = engine.avaliar(
        "skill_teste",
        ferramenta,
    )

    permissao = engine.confirmar(permissao)

    assert permissao.estado == "autorizada"
    assert "confirmada" in permissao.motivo


def testar_confirmacao_invalida():
    engine, _ = criar_engine()

    ferramenta = criar_ferramenta(
        "calcular",
    )

    permissao = engine.avaliar(
        "skill_teste",
        ferramenta,
    )

    try:
        engine.confirmar(permissao)
        assert False
    except ValueError:
        pass


def testar_contexto_vazio():
    engine, _ = criar_engine()

    ferramenta = criar_ferramenta(
        "calcular",
    )

    permissao = engine.avaliar(
        "",
        ferramenta,
    )

    assert permissao.estado == "negada"


if __name__ == "__main__":
    testar_ferramenta_autorizada()
    testar_ferramenta_nao_autorizada()
    testar_confirmacao_obrigatoria()
    testar_confirmacao_autoriza()
    testar_confirmacao_invalida()
    testar_contexto_vazio()

    print("=== PHASE 6.2 — PERMISSION ENGINE ===")
    print("[OK] Ferramenta autorizada")
    print("[OK] Ferramenta não autorizada bloqueada")
    print("[OK] Confirmação obrigatória")
    print("[OK] Confirmação autoriza execução")
    print("[OK] Confirmação inválida rejeitada")
    print("[OK] Contexto vazio bloqueado")
    print("PHASE 6.2: TODOS OS TESTES PASSARAM")