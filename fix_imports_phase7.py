from pathlib import Path


ROOT = Path("app")


SUBSTITUICOES = {
    # AI
    "from app.model_provider import":
        "from app.ai.model_provider import",

    "from app.model_contract import":
        "from app.ai.model_contract import",

    "from app.model_registry import":
        "from app.ai.model_registry import",

    "from app.model_profile import":
        "from app.ai.model_profile import",

    # Memory / RAG
    "from app.memory_contract import":
        "from app.memory.memory_contract import",

    "from app.memory_store import":
        "from app.memory.memory_store import",

    "from app.memory_retrieval import":
        "from app.memory.memory_retrieval import",

    "from app.context_retrieval import":
        "from app.memory.context_retrieval import",

    "from app.document_ingestion import":
        "from app.memory.document_ingestion import",

    "from app.embedding_provider import":
        "from app.memory.embedding_provider import",

    "from app.rag_contract import":
        "from app.memory.rag_contract import",

    "from app.rag_retrieval import":
        "from app.memory.rag_retrieval import",

    "from app.vector_contract import":
        "from app.memory.vector_contract import",

    "from app.vector_store import":
        "from app.memory.vector_store import",

    # Permissions
    "from app.permission_contract import":
        "from app.permissions.permission_contract import",

    "from app.permission_engine import":
        "from app.permissions.permission_engine import",

    "from app.permission_registry import":
        "from app.permissions.permission_registry import",

    "from app.permission_service import":
        "from app.permissions.permission_service import",

    "from app.permission_context import":
        "from app.permissions.permission_context import",

    "from app.permission_context_registry import":
        "from app.permissions.permission_context_registry import",

    # Tools
    "from app.tool_contract import":
        "from app.tools.tool_contract import",

    "from app.tool_registry import":
        "from app.tools.tool_registry import",

    "from app.tool_permissions import":
        "from app.tools.tool_permissions import",

    "from app.tool_validator import":
        "from app.tools.tool_validator import",

    "from app.execution_guard import":
        "from app.tools.execution_guard import",

    "from app.tools import":
        "from app.tools.tools import",

    # Planning
    "from app.planner_contract import":
        "from app.planning.planner_contract import",

    "from app.planner import":
        "from app.planning.planner import",

    # Routing
    "from app.router_contract import":
        "from app.routing.router_contract import",

    "from app.router import":
        "from app.routing.router import",

    # Skills
    "from app.skill_loader import":
        "from app.skills.skill_loader import",

    "from app.skill_frontmatter import":
        "from app.skills.skill_frontmatter import",

    # Core
    "from app.config import":
        "from app.core.config import",

    "from app.logging import":
        "from app.core.logging import",

    "from app.security import":
        "from app.core.security import",

    # Infrastructure
    "from app.database import":
        "from app.infrastructure.database import",

    "from app.storage import":
        "from app.infrastructure.storage import",

    "from app.audio import":
        "from app.infrastructure.audio import",
}


arquivos_alterados = []


for arquivo in ROOT.rglob("*.py"):
    if arquivo.name == "fix_imports_phase7.py":
        continue

    texto = arquivo.read_text(encoding="utf-8")
    original = texto

    for antigo, novo in SUBSTITUICOES.items():
        texto = texto.replace(antigo, novo)

    if texto != original:
        arquivo.write_text(
            texto,
            encoding="utf-8",
        )
        arquivos_alterados.append(arquivo)


print("Arquivos alterados:")

for arquivo in arquivos_alterados:
    print(f"  [OK] {arquivo}")

print()
print(
    f"Total: {len(arquivos_alterados)} arquivo(s) alterado(s)."
)