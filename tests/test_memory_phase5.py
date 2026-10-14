import tempfile

from app.memory_contract import MemoryContract
from app.memory_store import MemoryStore
from app.memory_retrieval import MemoryRetriever

from app.rag_contract import DocumentContract
from app.document_ingestion import DocumentIngestion

from app.embedding_provider import (
    HashEmbeddingProvider,
)

from app.vector_contract import VectorDocument
from app.vector_store import VectorStore
from app.rag_retrieval import RAGRetriever

from app.context_retrieval import ContextRetriever


def testar_memory_stack():
    with tempfile.TemporaryDirectory() as diretorio:

        store = MemoryStore(diretorio)
        retriever = MemoryRetriever(store)

        memoria = MemoryContract(
            id="mem_final_001",
            conteudo=(
                "O Agent Core utiliza Python e FastAPI."
            ),
            tipo="fact",
            importancia=0.9,
        )

        store.salvar(memoria)

        recuperada = store.obter(
            "mem_final_001"
        )

        assert recuperada is not None
        assert recuperada.conteudo == (
            memoria.conteudo
        )

        resultados = retriever.buscar(
            "Agent Core Python"
        )

        assert len(resultados) == 1
        assert resultados[0].id == (
            "mem_final_001"
        )


def testar_rag_contract():
    documento = DocumentContract(
        id="doc_final_001",
        nome="README.md",
        conteudo=(
            "# Agent Core\nSistema local de agentes."
        ),
        tipo="markdown",
        origem="local",
    )

    valido, erro = documento.validar()

    assert valido is True
    assert erro == ""


def testar_document_ingestion():
    ingestion = DocumentIngestion()

    documento = ingestion.ingerir_texto(
        texto=(
            "Agent Core possui arquitetura modular."
        ),
        nome="architecture.md",
        tipo="markdown",
    )

    assert documento.nome == (
        "architecture.md"
    )

    assert documento.tipo == "markdown"

    assert "arquitetura modular" in (
        documento.conteudo
    )


def testar_embedding():
    provider = HashEmbeddingProvider(
        dimensao=32
    )

    embedding = provider.gerar(
        "Agent Core"
    )

    assert isinstance(
        embedding,
        list,
    )

    assert len(embedding) == 32

    assert all(
        isinstance(valor, float)
        for valor in embedding
    )


def testar_vector_store():
    with tempfile.TemporaryDirectory() as diretorio:

        store = VectorStore(diretorio)

        documento = VectorDocument(
            id="vec_final_001",
            documento_id="doc_final_001",
            conteudo=(
                "Agent Core utiliza FastAPI."
            ),
            embedding=[
                0.1,
                0.2,
                0.3,
            ],
            metadata={
                "nome": "README.md",
            },
        )

        store.salvar(documento)

        recuperado = store.obter(
            "vec_final_001"
        )

        assert recuperado is not None
        assert recuperado.id == (
            "vec_final_001"
        )


def testar_rag_retrieval():
    with tempfile.TemporaryDirectory() as diretorio:

        store = VectorStore(diretorio)

        provider = HashEmbeddingProvider(
            dimensao=32
        )

        texto = (
            "Agent Core utiliza FastAPI."
        )

        store.salvar(
            VectorDocument(
                id="vec_final_001",
                documento_id="doc_final_001",
                conteudo=texto,
                embedding=provider.gerar(
                    texto
                ),
            )
        )

        retriever = RAGRetriever(
            vector_store=store,
            embedding_provider=provider,
        )

        resultados = retriever.buscar(
            "Agent Core",
            limite=1,
        )

        assert len(resultados) == 1
        assert resultados[0].id == (
            "vec_final_001"
        )


def testar_integracao_memory_rag():
    diretorio_memory = (
        tempfile.TemporaryDirectory()
    )

    diretorio_vectors = (
        tempfile.TemporaryDirectory()
    )

    try:
        memory_store = MemoryStore(
            diretorio_memory.name
        )

        memory_retriever = MemoryRetriever(
            memory_store
        )

        memory_store.salvar(
            MemoryContract(
                id="mem_integracao",
                conteudo=(
                    "O projeto utiliza Python."
                ),
                tipo="fact",
            )
        )

        vector_store = VectorStore(
            diretorio_vectors.name
        )

        provider = HashEmbeddingProvider(
            dimensao=32
        )

        texto_documento = (
            "O Agent Core possui Skills e Tools."
        )

        vector_store.salvar(
            VectorDocument(
                id="vec_integracao",
                documento_id="doc_integracao",
                conteudo=texto_documento,
                embedding=provider.gerar(
                    texto_documento
                ),
                metadata={
                    "nome": "ARCHITECTURE.md",
                },
            )
        )

        rag_retriever = RAGRetriever(
            vector_store=vector_store,
            embedding_provider=provider,
        )

        context_retriever = ContextRetriever(
            memory_retriever=memory_retriever,
            rag_retriever=rag_retriever,
        )

        contexto = context_retriever.buscar(
            "Agent Core Python",
            limite_memoria=5,
            limite_rag=5,
        )

        assert len(
            contexto["memorias"]
        ) >= 1

        assert len(
            contexto["documentos"]
        ) >= 1

        texto_contexto = (
            context_retriever.construir_contexto(
                contexto
            )
        )

        assert (
            "Memórias relevantes:"
            in texto_contexto
        )

        assert (
            "Documentos relevantes:"
            in texto_contexto
        )

    finally:
        diretorio_memory.cleanup()
        diretorio_vectors.cleanup()


def testar_importacoes_principais():
    import app.memory_contract
    import app.memory_store
    import app.memory_retrieval

    import app.rag_contract
    import app.document_ingestion

    import app.embedding_provider
    import app.vector_contract
    import app.vector_store

    import app.rag_retrieval
    import app.context_retrieval


print("=== PHASE 5.10 — FINAL TESTS ===")

testar_memory_stack()
print("[OK] Memory Stack")

testar_rag_contract()
print("[OK] RAG Contract")

testar_document_ingestion()
print("[OK] Document Ingestion")

testar_embedding()
print("[OK] Embedding Provider")

testar_vector_store()
print("[OK] Vector Store")

testar_rag_retrieval()
print("[OK] RAG Retrieval")

testar_integracao_memory_rag()
print("[OK] Memory + RAG integrados")

testar_importacoes_principais()
print("[OK] Importações principais")

print("================================")
print("PHASE 5: TODOS OS TESTES PASSARAM")
print("MEMORY + RAG: CONCLUÍDOS")