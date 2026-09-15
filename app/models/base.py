from typing import Protocol, Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=16000)


class ModelHealth(BaseModel):
    status: Literal["ready", "unreachable", "model_missing", "invalid_response"]
    model: str


class ChatResult(BaseModel):
    content: str
    model: str


class ProviderError(RuntimeError):
    """Erro sanitizado; não carrega corpo da resposta ou credenciais."""


class ModelProvider(Protocol):
    async def health(self) -> ModelHealth: ...
    async def chat(self, messages: list[Message]) -> ChatResult: ...
    async def aclose(self) -> None: ...
