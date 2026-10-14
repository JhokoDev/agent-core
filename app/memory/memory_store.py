import json
from pathlib import Path

from app.memory.memory_contract import MemoryContract


class MemoryStore:
    """
    Persistência local das memórias do Agent Core.

    Nesta fase utiliza arquivos JSON.
    A implementação pode ser substituída futuramente
    sem alterar o contrato de memória.
    """

    def __init__(
        self,
        diretorio: str | Path = "data/memory",
    ):
        self.diretorio = Path(diretorio)
        self.diretorio.mkdir(
            parents=True,
            exist_ok=True,
        )

    def salvar(
        self,
        memoria: MemoryContract,
    ) -> None:
        valido, erro = memoria.validar()

        if not valido:
            raise ValueError(
                f"Memória inválida: {erro}"
            )

        caminho = self.diretorio / f"{memoria.id}.json"

        caminho.write_text(
            json.dumps(
                {
                    "id": memoria.id,
                    "conteudo": memoria.conteudo,
                    "tipo": memoria.tipo,
                    "origem": memoria.origem,
                    "importancia": memoria.importancia,
                    "metadata": memoria.metadata,
                    "criado_em": memoria.criado_em,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def obter(
        self,
        memoria_id: str,
    ) -> MemoryContract | None:
        caminho = self.diretorio / f"{memoria_id}.json"

        if not caminho.exists():
            return None

        dados = json.loads(
            caminho.read_text(
                encoding="utf-8"
            )
        )

        return MemoryContract(
            id=dados["id"],
            conteudo=dados["conteudo"],
            tipo=dados.get(
                "tipo",
                "context",
            ),
            origem=dados.get(
                "origem",
                "conversation",
            ),
            importancia=dados.get(
                "importancia",
                0.5,
            ),
            metadata=dados.get(
                "metadata",
                {},
            ),
            criado_em=dados.get(
                "criado_em",
                "",
            ),
        )

    def listar(self) -> list[MemoryContract]:
        memorias = []

        for caminho in sorted(
            self.diretorio.glob("*.json")
        ):
            memoria = self.obter(
                caminho.stem
            )

            if memoria is not None:
                memorias.append(memoria)

        return memorias

    def remover(
        self,
        memoria_id: str,
    ) -> bool:
        caminho = self.diretorio / f"{memoria_id}.json"

        if not caminho.exists():
            return False

        caminho.unlink()
        return True

    def limpar(self) -> None:
        for caminho in self.diretorio.glob("*.json"):
            caminho.unlink()