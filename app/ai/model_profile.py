from app.ai.model_contract import ModelContract


def criar_modelos_padrao() -> list[ModelContract]:
    """
    Cria os modelos inicialmente suportados pelo Agent Core.

    Llama 3.2 permanece como modelo principal.
    Qwen fica disponível como modelo opcional.
    """

    return [
        ModelContract(
            id="llama3.2:1b",
            nome="Llama 3.2 1B",
            provider="ollama",
            descricao=(
                "Modelo principal para tarefas gerais "
                "e processamento local."
            ),
            suporta_tools=True,
            suporta_vision=False,
            contexto_maximo=4096,
            capacidades=[
                "conversa",
                "classificacao",
                "resumo",
                "extracao",
                "tools",
            ],
        ),
        ModelContract(
            id="qwen",
            nome="Qwen",
            provider="ollama",
            descricao=(
                "Modelo opcional para tarefas técnicas "
                "e programação."
            ),
            suporta_tools=True,
            suporta_vision=False,
            capacidades=[
                "codigo",
                "analise_tecnica",
                "tools",
            ],
        ),
    ]