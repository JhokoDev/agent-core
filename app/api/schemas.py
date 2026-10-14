from pydantic import BaseModel, Field
from typing import Optional


class AgenteInfo(BaseModel):
    id: str
    nome: str
    icone: str
    tipo: str
    modelo: str
    temperatura: float
    prompt_sistema: str

    # Ferramentas que esta Skill está autorizada a disponibilizar ao modelo.
    # Lista vazia significa que nenhuma ferramenta será disponibilizada.
    ferramentas_permitidas: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    texto: str
    skill_id: Optional[str] = "default"
    tool_id: Optional[str] = None
    chat_id: Optional[str] = None
    imagem_base64: Optional[str] = None
