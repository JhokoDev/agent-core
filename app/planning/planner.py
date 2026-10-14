from app.planning.planner_contract import (
    PlanStep,
    PlannerContract,
)


class Planner:
    """
    Planner determinístico inicial.

    Responsável por transformar uma solicitação
    em uma estrutura de etapas.

    Não executa ferramentas nem modelos.
    """

    def planejar(
        self,
        objetivo: str,
        etapas: list[dict] | None = None,
    ) -> PlannerContract:

        objetivo = objetivo.strip()

        if not objetivo:
            return PlannerContract(
                objetivo="",
                etapas=[],
                metadata={
                    "planner_version": "1.0",
                    "deterministico": True,
                },
            )

        etapas_normalizadas = []

        for indice, dados in enumerate(etapas or [], start=1):
            etapas_normalizadas.append(
                PlanStep(
                    id=dados.get(
                        "id",
                        f"etapa_{indice}"
                    ),
                    descricao=dados.get(
                        "descricao",
                        ""
                    ),
                    ferramenta=dados.get("ferramenta"),
                    argumentos=dados.get(
                        "argumentos",
                        {}
                    ),
                )
            )

        plano = PlannerContract(
            objetivo=objetivo,
            etapas=etapas_normalizadas,
            metadata={
                "planner_version": "1.0",
                "deterministico": True,
                "quantidade_etapas": len(etapas_normalizadas),
            },
        )

        valido, erro = plano.validar()

        if not valido:
            raise ValueError(
                f"Plano inválido: {erro}"
            )

        return plano