import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SKILLS_DIR = BASE_DIR / "skills"
TOOLS_DIR = BASE_DIR / "tools"
PROJETOS_DIR = BASE_DIR / "projetos"

for directory in (DATA_DIR, SKILLS_DIR, TOOLS_DIR, PROJETOS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

def carregar_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None

def salvar_json(path: Path, data: dict[str, Any]) -> None:
    temporary_path = path.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    temporary_path.replace(path)

def formatar_data(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y às %H:%M")

def tamanho_arquivo(path: Path) -> str:
    size = path.stat().st_size
    if size < 1024: return f"{size} B"
    if size < 1024 * 1024: return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"

def validar_id_skill(skill_id: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,49}", skill_id))

def listar_chats() -> list[Path]:
    try: return sorted(DATA_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    except OSError: return []

def listar_skills() -> list[Path]:
    try: return sorted(SKILLS_DIR.rglob("*.md"), key=lambda path: str(path).casefold())
    except OSError: return []

def listar_tools() -> list[Path]:
    try: return sorted((path for path in TOOLS_DIR.iterdir() if path.is_file()), key=lambda path: path.name.casefold())
    except OSError: return []

def listar_projetos() -> list[Path]:
    try: return sorted((path for path in PROJETOS_DIR.iterdir() if path.is_file()), key=lambda path: path.name.casefold())
    except OSError: return []

def caminho_relativo(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")

def renderizar_conteudo(content: Any) -> str:
    if isinstance(content, str): return content
    return json.dumps(content, ensure_ascii=False, indent=2)

def rotulo_chat(path: Path, chat: dict[str, Any] | None = None) -> str:
    chat = chat or carregar_json(path) or {}
    title = str(chat.get("titulo") or "Sem título").strip() or "Sem título"
    messages = chat.get("mensagens")
    quantity = len(messages) if isinstance(messages, list) else 0
    return f"{title} · {formatar_data(path.stat().st_mtime)} · {quantity} mensagens"

def obter_analytics() -> dict:
    chats = listar_chats()
    dados, total_prompt, total_resp = [], 0, 0
    
    for path in chats:
        chat = carregar_json(path)
        if not chat: continue
        
        chat_prompt = chat_resp = 0
        for msg in chat.get("mensagens", []):
            meta = msg.get("meta", {})
            chat_prompt += meta.get("tokens_prompt", 0)
            chat_resp += meta.get("tokens_resposta", 0)
        
        if chat_prompt > 0 or chat_resp > 0:
            dados.append({
                "Chat": str(chat.get("titulo") or "Sem título")[:30],
                "Tokens Prompt": chat_prompt,
                "Tokens Resposta": chat_resp
            })
            total_prompt += chat_prompt
            total_resp += chat_resp
            
    return {"dados": dados, "total_prompt": total_prompt, "total_resposta": total_resp}