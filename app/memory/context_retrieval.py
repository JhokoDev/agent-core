from app.memory.memory_retrieval import MemoryRetriever
from app.memory.rag_retrieval import RAGRetriever


class ContextRetriever:
    def __init__(
        self,
        memory_retriever: MemoryRetriever,
        rag_retriever: RAGRetriever,
    ):
        self.memory_retriever = memory_retriever
        self.rag_retriever = rag_retriever

    def buscar(
        self,
        consulta: str,
        limite_memoria: int = 5,
        limite_rag: int = 5,
    ) -> dict:
        memorias = self.memory_retriever.buscar(
            consulta,
            limite=limite_memoria,
        )

        documentos = self.rag_retriever.buscar(
            consulta,
            limite=limite_rag,
        )

        return {
            "memorias": memorias,
            "documentos": documentos,
        }

    def construir_contexto(
        self,
        contexto: dict,
    ) -> str:
        memorias = contexto.get(
            "memorias",
            [],
        )

        documentos = contexto.get(
            "documentos",
            [],
        )

        partes = []

        if memorias:
            partes.append(
                "Memórias relevantes:"
            )

            for memoria in memorias:
                partes.append(
                    f"- [{memoria.tipo}] "
                    f"{memoria.conteudo}"
                )

        if documentos:
            if partes:
                partes.append("")

            partes.append(
                "Documentos relevantes:"
            )

            for documento in documentos:
                partes.append(
                    f"- [{documento.id}] "
                    f"{documento.conteudo}"
                )

        return "\n".join(partes)