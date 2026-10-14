from app.planner import Planner
from app.planner_contract import (
    PlanStep,
    PlannerContract,
)


planner = Planner()


# 1. Plano simples
plano = planner.planejar(
    "Analisar projeto",
    [
        {
            "descricao": "Ler os arquivos do projeto",
        },
        {
            "descricao": "Identificar possíveis problemas",
        },
        {
            "descricao": "Produzir relatório",
        },
    ],
)

assert isinstance(plano, PlannerContract)
assert plano.objetivo == "Analisar projeto"
assert len(plano.etapas) == 3


# 2. IDs automáticos
assert plano.etapas[0].id == "etapa_1"
assert plano.etapas[1].id == "etapa_2"
assert plano.etapas[2].id == "etapa_3"


# 3. Estado inicial
assert all(
    etapa.estado == "pendente"
    for etapa in plano.etapas
)


# 4. Ferramenta e argumentos
plano_tool = planner.planejar(
    "Calcular resultado",
    [
        {
            "descricao": "Executar cálculo",
            "ferramenta": "calcular",
            "argumentos": {
                "expressao": "127 * 43",
            },
        },
    ],
)

etapa = plano_tool.etapas[0]

assert etapa.ferramenta == "calcular"
assert etapa.argumentos["expressao"] == "127 * 43"


# 5. Plano vazio
plano_vazio = planner.planejar(
    "Objetivo sem etapas"
)

assert isinstance(plano_vazio, PlannerContract)
assert len(plano_vazio.etapas) == 0


# 6. Objetivo vazio
plano_invalido = planner.planejar("")

assert plano_invalido.objetivo == ""
assert len(plano_invalido.etapas) == 0


# 7. Validação de estado
etapa_invalida = PlanStep(
    id="etapa_1",
    descricao="Teste",
    estado="estado_inexistente",
)

plano_estado_invalido = PlannerContract(
    objetivo="Teste",
    etapas=[etapa_invalida],
)

valido, erro = plano_estado_invalido.validar()

assert valido is False
assert "estado inválido" in erro


# 8. IDs duplicados
plano_duplicado = PlannerContract(
    objetivo="Teste",
    etapas=[
        PlanStep(
            id="etapa_1",
            descricao="Primeira",
        ),
        PlanStep(
            id="etapa_1",
            descricao="Segunda",
        ),
    ],
)

valido, erro = plano_duplicado.validar()

assert valido is False
assert "duplicada" in erro


print("=== PHASE 4 — PLANNER ===")
print("[OK] PlannerContract")
print("[OK] PlanStep")
print("[OK] Criação de planos")
print("[OK] IDs automáticos")
print("[OK] Estados das etapas")
print("[OK] Ferramentas e argumentos")
print("[OK] Validação de estados")
print("[OK] Detecção de IDs duplicados")
print("[OK] Plano vazio")
print("================================")
print("PHASE 4.1–4.5: TODOS OS TESTES PASSARAM")