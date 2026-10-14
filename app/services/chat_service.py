import uuid
from datetime import datetime
from app.infrastructure import storage

class ChatService:
    """Gerencia a persistência e formatação de conversas e contexto."""

    def obter_ou_criar_chat(self, chat_id: str | None) -> dict:
        if chat_id:
            chat = storage.obter_chat(chat_id)
            if chat is not None:
                return chat
                
        # Gera o ID antes para poder passar como argumento separado
        novo_id = chat_id or str(uuid.uuid4())
        
        novo_chat = {
            "id": novo_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
        }
        
        # CORREÇÃO: Passa os dois argumentos (ID e Dados) exigidos pelo storage.py
        storage.salvar_chat(novo_id, novo_chat)
        return novo_chat

    def salvar_chat(self, chat: dict) -> None:
        chat["updated_at"] = datetime.now().isoformat()
        # CORREÇÃO: Passa os dois argumentos (ID e Dados) exigidos pelo storage.py
        storage.salvar_chat(chat["id"], chat)

    def preparar_contexto_limpo(self, mensagens: list[dict], limite: int = 20) -> list[dict]:
        contexto: list[dict] = []
        
        for mensagem in mensagens[-limite:]:
            if not isinstance(mensagem, dict): 
                continue
                
            role = mensagem.get("role")
            content = mensagem.get("content")
            
            if role not in {"system", "user", "assistant", "tool"}: 
                continue
                
            if not isinstance(content, str): 
                continue
                
            contexto.append({
                "role": role, 
                "content": content, 
                "tool_calls": mensagem.get("tool_calls"), 
                "name": mensagem.get("name")
            })
            
        return contexto