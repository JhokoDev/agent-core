import math

from app.memory.embedding_provider import EmbeddingProvider
from app.memory.vector_contract import VectorDocument
from app.memory.vector_store import VectorStore


class RAGRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    def buscar(
        self,
        consulta: str,
        limite: int = 5,
    ) -> list[VectorDocument]:
        consulta = consulta.strip()

        if not consulta:
            return []

        if limite <= 0:
            return []

        embedding_consulta = (
            self.embedding_provider.gerar(
                consulta
            )
        )

        documentos = self.vector_store.listar()

        resultados = []

        for documento in documentos:
            similaridade = self._similaridade_cosseno(
                embedding_consulta,
                documento.embedding,
            )

            resultados.append(
                (
                    similaridade,
                    documento,
                )
            )

        resultados.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            documento
            for _, documento in resultados[:limite]
        ]

    def buscar_com_pontuacao(
        self,
        consulta: str,
        limite: int = 5,
    ) -> list[tuple[VectorDocument, float]]:
        consulta = consulta.strip()

        if not consulta:
            return []

        if limite <= 0:
            return []

        embedding_consulta = (
            self.embedding_provider.gerar(
                consulta
            )
        )

        resultados = []

        for documento in self.vector_store.listar():
            similaridade = self._similaridade_cosseno(
                embedding_consulta,
                documento.embedding,
            )

            resultados.append(
                (
                    documento,
                    similaridade,
                )
            )

        resultados.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return resultados[:limite]

    def _similaridade_cosseno(
        self,
        vetor_a: list[float],
        vetor_b: list[float],
    ) -> float:
        if len(vetor_a) != len(vetor_b):
            raise ValueError(
                "Os embeddings precisam possuir "
                "a mesma dimensão."
            )

        produto_escalar = sum(
            a * b
            for a, b in zip(
                vetor_a,
                vetor_b,
            )
        )

        norma_a = math.sqrt(
            sum(
                valor * valor
                for valor in vetor_a
            )
        )

        norma_b = math.sqrt(
            sum(
                valor * valor
                for valor in vetor_b
            )
        )

        if norma_a == 0 or norma_b == 0:
            return 0.0

        return (
            produto_escalar
            / (norma_a * norma_b)
        )