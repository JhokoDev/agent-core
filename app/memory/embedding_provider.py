from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):

    @abstractmethod
    def gerar(
        self,
        texto: str,
    ) -> list[float]:
        raise NotImplementedError



class HashEmbeddingProvider(
    EmbeddingProvider
):
    def __init__(
        self,
        dimensao: int = 32,
    ):
        self.dimensao = dimensao

    def gerar(
        self,
        texto: str,
    ) -> list[float]:
        import hashlib

        valores = []

        for indice in range(
            self.dimensao
        ):
            digest = hashlib.sha256(
                f"{indice}:{texto}".encode(
                    "utf-8"
                )
            ).digest()

            valor = int.from_bytes(
                digest[:4],
                byteorder="big",
            )

            valores.append(
                valor / 4_294_967_295
            )

        return valores

def criar_embedding_provider():
    return HashEmbeddingProvider()