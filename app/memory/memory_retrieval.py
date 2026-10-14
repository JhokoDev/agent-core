import re

from app.memory.memory_contract import MemoryContract
from app.memory.memory_store import MemoryStore


class MemoryRetriever:
    def __init__(self, store: MemoryStore):
        self.store = store

    def buscar(
        self,
        consulta: str,
        limite: int = 5,
    ) -> list[MemoryContract]:
        consulta_normalizada = self._normalizar(
            consulta
        )

        if not consulta_normalizada:
            return []

        if limite <= 0:
            return []

        termos = set(
            consulta_normalizada.split()
        )

        memorias = self.store.listar()
        resultados = []

        for memoria in memorias:
            texto = self._normalizar(
                memoria.conteudo
            )

            palavras = set(
                texto.split()
            )

            correspondencias = len(
                termos & palavras
            )

            if correspondencias == 0:
                continue

            pontuacao = (
                correspondencias
                + memoria.importancia
            )

            resultados.append(
                (
                    pontuacao,
                    memoria,
                )
            )

        resultados.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            memoria
            for _, memoria in resultados[:limite]
        ]

    def buscar_por_tipo(
        self,
        tipo: str,
        limite: int = 5,
    ) -> list[MemoryContract]:
        if limite <= 0:
            return []

        memorias = [
            memoria
            for memoria in self.store.listar()
            if memoria.tipo == tipo
        ]

        memorias.sort(
            key=lambda memoria: memoria.importancia,
            reverse=True,
        )

        return memorias[:limite]

    def _normalizar(
        self,
        texto: str,
    ) -> str:
        texto = texto.lower()

        texto = re.sub(
            r"[^\w\s]",
            " ",
            texto,
            flags=re.UNICODE,
        )

        texto = re.sub(
            r"\s+",
            " ",
            texto,
        )

        return texto.strip()