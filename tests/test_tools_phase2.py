from app.tool_registry import criar_registry_padrao
from app.tool_permissions import ToolPermissionPolicy
from app.tool_validator import validar_argumentos


def main():
    print("\n=== PHASE 2.8 — TOOL SYSTEM TESTS ===\n")

    registry = criar_registry_padrao()

    # ==========================================================
    # 1. REGISTRY
    # ==========================================================

    ferramentas = registry.listar()

    esperadas = {
        "obter_hora_atual",
        "calcular",
        "ler_arquivo_codigo",
        "controlar_computador",
        "terminal_dinamico",
        "interagir_ecra",
    }

    ids = {f.id for f in ferramentas}

    assert ids == esperadas
    assert len(ferramentas) == 6

    print("[OK] Registry possui as 6 ferramentas esperadas.")

    # ==========================================================
    # 2. DUPLICAÇÃO
    # ==========================================================

    ferramenta_calcular = registry.obter("calcular")

    try:
        registry.registrar(ferramenta_calcular)
        raise AssertionError(
            "Registry aceitou ferramenta duplicada."
        )
    except ValueError:
        print("[OK] Registry rejeita ferramentas duplicadas.")

    # ==========================================================
    # 3. SCHEMA OLLAMA
    # ==========================================================

    schemas = registry.gerar_schemas_ollama(
        [
            "calcular",
            "interagir_ecra",
        ]
    )

    assert len(schemas) == 2

    calcular_schema = next(
        schema
        for schema in schemas
        if schema["function"]["name"] == "calcular"
    )

    assert (
        calcular_schema["function"]["parameters"]["properties"]
        ["expressao"]["type"]
        == "string"
    )

    assert (
        "expressao"
        in calcular_schema["function"]["parameters"]["required"]
    )

    tela_schema = next(
        schema
        for schema in schemas
        if schema["function"]["name"] == "interagir_ecra"
    )

    assert (
        "acao"
        in tela_schema["function"]["parameters"]["properties"]
    )

    print("[OK] Schemas Ollama foram gerados corretamente.")

    # ==========================================================
    # 4. VALIDATOR — ARGUMENTOS VÁLIDOS
    # ==========================================================

    valido, erro = validar_argumentos(
        ferramenta_calcular,
        {
            "expressao": "127 * 43"
        }
    )

    assert valido is True
    assert erro == ""

    print("[OK] Validator aceita argumentos válidos.")

    # ==========================================================
    # 5. VALIDATOR — ARGUMENTO AUSENTE
    # ==========================================================

    valido, erro = validar_argumentos(
        ferramenta_calcular,
        {}
    )

    assert valido is False
    assert "expressao" in erro

    print("[OK] Validator rejeita argumento obrigatório ausente.")

    # ==========================================================
    # 6. VALIDATOR — TIPO INCORRETO
    # ==========================================================

    valido, erro = validar_argumentos(
        ferramenta_calcular,
        {
            "expressao": 127
        }
    )

    assert valido is False

    print("[OK] Validator rejeita tipo incorreto.")

    # ==========================================================
    # 7. EXECUÇÃO REAL
    # ==========================================================

    resultado = ferramenta_calcular.handler(
        {
            "expressao": "127 * 43"
        }
    )

    assert "5461" in resultado

    print("[OK] Handler da calculadora executa corretamente.")

    # ==========================================================
    # 8. PERMISSION POLICY — PERMITIDO
    # ==========================================================

    policy = ToolPermissionPolicy()

    policy.definir_permissoes(
        "skill_teste",
        [
            "calcular",
            "obter_hora_atual",
        ]
    )

    assert policy.permitir(
        "skill_teste",
        ferramenta_calcular
    ) is True

    print("[OK] Permission Policy permite ferramenta autorizada.")

    # ==========================================================
    # 9. PERMISSION POLICY — NEGADO
    # ==========================================================

    ferramenta_terminal = registry.obter(
        "terminal_dinamico"
    )

    assert ferramenta_terminal is not None

    assert policy.permitir(
        "skill_teste",
        ferramenta_terminal
    ) is False

    print("[OK] Permission Policy bloqueia ferramenta não autorizada.")

    # ==========================================================
    # 10. FERRAMENTA DE ALTO RISCO
    # ==========================================================

    assert (
        ferramenta_terminal.risco
        == "alto"
    )

    assert (
        ferramenta_terminal.requer_confirmacao
        is True
    )

    print("[OK] Ferramentas de alto risco possuem confirmação.")

    # ==========================================================
    # 11. FERRAMENTA DE BAIXO RISCO
    # ==========================================================

    assert (
        ferramenta_calcular.risco
        == "baixo"
    )

    assert (
        ferramenta_calcular.requer_confirmacao
        is False
    )

    print("[OK] Ferramentas de baixo risco estão configuradas.")

    # ==========================================================
    # 12. HANDLERS
    # ==========================================================

    assert (
        registry.obter(
            "calcular"
        ).handler is not None
    )

    assert (
        registry.obter(
            "obter_hora_atual"
        ).handler is not None
    )

    assert (
        registry.obter(
            "ler_arquivo_codigo"
        ).handler is not None
    )

    assert (
        registry.obter(
            "terminal_dinamico"
        ).handler is not None
    )

    assert (
        registry.obter(
            "interagir_ecra"
        ).handler is not None
    )

    print("[OK] Handlers das ferramentas migradas estão conectados.")

    # ==========================================================
    # 13. FERRAMENTA ESPECIAL
    # ==========================================================

    controlar_pc = registry.obter(
        "controlar_computador"
    )

    assert controlar_pc is not None

    assert controlar_pc.handler is None
    assert controlar_pc.requer_confirmacao is True
    assert controlar_pc.risco == "alto"

    print("[OK] controlar_computador mantém tratamento especial.")

    # ==========================================================
    # FINAL
    # ==========================================================

    print(
        "\n=========================================="
    )
    print(
        "PHASE 2.8: TODOS OS TESTES PASSARAM"
    )
    print(
        "==========================================\n"
    )


if __name__ == "__main__":
    main()