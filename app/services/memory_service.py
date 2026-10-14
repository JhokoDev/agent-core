from typing import Any
from app.memory.memory_store import MemoryStore
from app.memory.memory_retrieval import MemoryRetriever

class MemoryService:
    """Gerencia a leitura e escrita de memórias do Agent Core."""

    def __init__(self):
        self.store = MemoryStore()
        self.retriever = MemoryRetriever(self.store)

    def salvar(self, conteudo: str, tipo: str = "fato", metadata: dict[str, Any] | None = None) -> Any:
        return self.store.salvar(
            conteudo=conteudo,
            tipo=tipo,
            metadata=metadata or {}
        )

    def buscar(self, consulta: str, limite: int = 5) -> list[Any]:
        return self.retriever.buscar(consulta, limite=limite)

    def formatar_contexto(self, consulta: str, limite: int = 5) -> str:
        memorias = self.buscar(consulta, limite)
        if not memorias:
            return ""

        linhas_memoria = []
        for memoria in memorias:
            if isinstance(memoria, dict):
                conteudo = memoria.get("conteudo", memoria.get("content", ""))
            else:
                conteudo = getattr(memoria, "conteudo", getattr(memoria, "content", ""))
                
            if conteudo:
                linhas_memoria.append(f"- {conteudo}")
                
        if linhas_memoria:
            return "Memórias relevantes:\n" + "\n".join(linhas_memoria)
        
        return ""