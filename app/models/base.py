from typing import Protocol, Literal, Any
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(default="")
    name: str | None = None
    tool_calls: list[dict] | None = None


class ModelHealth(BaseModel):
    status: Literal["ready", "unreachable", "model_missing", "invalid_response"]
    model: str


class ChatResult(BaseModel):
    content: str
    model: str
    tool_calls: list[dict] | None = None
    reasoning: str | None = None



class ProviderError(RuntimeError):
    """Erro sanitizado; não carrega corpo da resposta ou credenciais."""


class ModelProvider(Protocol):
    async def health(self) -> ModelHealth: ...
    async def chat(self, messages: list[Message], tools: list[dict] | None = None) -> ChatResult: ...
    async def aclose(self) -> None: ...