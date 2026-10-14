from pathlib import Path

from app.memory.rag_contract import DocumentContract


EXTENSOES_TIPOS = {
    ".txt": "text",
    ".md": "markdown",
    ".markdown": "markdown",
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".java": "code",
    ".kt": "code",
    ".php": "code",
    ".cpp": "code",
    ".c": "code",
    ".h": "code",
    ".hpp": "code",
    ".html": "html",
    ".htm": "html",
    ".json": "json",
}


class DocumentIngestion:
    def __init__(
        self,
        encoding: str = "utf-8",
    ):
        self.encoding = encoding

    def ingerir_arquivo(
        self,
        caminho: str | Path,
    ) -> DocumentContract:
        caminho = Path(caminho)

        if not caminho.exists():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {caminho}"
            )

        if not caminho.is_file():
            raise ValueError(
                f"O caminho informado não é um arquivo: {caminho}"
            )

        tipo = self._detectar_tipo(caminho)

        if tipo is None:
            raise ValueError(
                f"Extensão não suportada: '{caminho.suffix}'"
            )

        conteudo = caminho.read_text(
            encoding=self.encoding
        )

        documento = DocumentContract(
            id=self._gerar_id(caminho),
            nome=caminho.name,
            conteudo=conteudo,
            tipo=tipo,
            origem=str(caminho),
            metadata={
                "extensao": caminho.suffix.lower(),
                "nome_arquivo": caminho.name,
                "caminho": str(caminho),
            },
        )

        valido, erro = documento.validar()

        if not valido:
            raise ValueError(
                f"Documento inválido: {erro}"
            )

        return documento

    def ingerir_texto(
        self,
        texto: str,
        nome: str,
        tipo: str = "text",
        origem: str = "manual",
    ) -> DocumentContract:
        documento = DocumentContract(
            id=self._gerar_id_nome(nome),
            nome=nome,
            conteudo=texto,
            tipo=tipo,
            origem=origem,
            metadata={
                "nome_arquivo": nome,
            },
        )

        valido, erro = documento.validar()

        if not valido:
            raise ValueError(
                f"Documento inválido: {erro}"
            )

        return documento

    def _detectar_tipo(
        self,
        caminho: Path,
    ) -> str | None:
        return EXTENSOES_TIPOS.get(
            caminho.suffix.lower()
        )

    def _gerar_id(
        self,
        caminho: Path,
    ) -> str:
        return self._gerar_id_nome(
            str(caminho.resolve())
        )

    def _gerar_id_nome(
        self,
        valor: str,
    ) -> str:
        import hashlib

        return hashlib.sha256(
            valor.encode("utf-8")
        ).hexdigest()[:16]