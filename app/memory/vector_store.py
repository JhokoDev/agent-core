import json
from pathlib import Path

from app.memory.vector_contract import VectorDocument


class VectorStore:
    def __init__(
        self,
        diretorio: str | Path = "data/vectors",
    ):
        self.diretorio = Path(diretorio)
        self.diretorio.mkdir(
            parents=True,
            exist_ok=True,
        )

    def salvar(
        self,
        documento: VectorDocument,
    ) -> None:
        valido, erro = documento.validar()

        if not valido:
            raise ValueError(
                f"Vetor inválido: {erro}"
            )

        caminho = (
            self.diretorio
            / f"{documento.id}.json"
        )

        caminho.write_text(
            json.dumps(
                {
                    "id": documento.id,
                    "documento_id": documento.documento_id,
                    "conteudo": documento.conteudo,
                    "embedding": documento.embedding,
                    "metadata": documento.metadata,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def obter(
        self,
        vetor_id: str,
    ) -> VectorDocument | None:
        caminho = (
            self.diretorio
            / f"{vetor_id}.json"
        )

        if not caminho.exists():
            return None

        dados = json.loads(
            caminho.read_text(
                encoding="utf-8"
            )
        )

        return VectorDocument(
            id=dados["id"],
            documento_id=dados["documento_id"],
            conteudo=dados["conteudo"],
            embedding=dados["embedding"],
            metadata=dados.get(
                "metadata",
                {},
            ),
        )

    def listar(self) -> list[VectorDocument]:
        documentos = []

        for caminho in sorted(
            self.diretorio.glob("*.json")
        ):
            documento = self.obter(
                caminho.stem
            )

            if documento is not None:
                documentos.append(documento)

        return documentos

    def remover(
        self,
        vetor_id: str,
    ) -> bool:
        caminho = (
            self.diretorio
            / f"{vetor_id}.json"
        )

        if not caminho.exists():
            return False

        caminho.unlink()
        return True

    def limpar(self) -> None:
        for caminho in self.diretorio.glob(
            "*.json"
        ):
            caminho.unlink()