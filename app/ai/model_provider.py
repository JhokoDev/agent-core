import os
from abc import ABC, abstractmethod
from typing import Any

import requests

from app.models.base import (
    ChatResult,
    Message,
    ModelHealth,
    ProviderError,
)


class ModelProvider(ABC):
    """
    Interface comum para execução de modelos de IA.
    """

    @abstractmethod
    def gerar(
        self,
        modelo: str,
        mensagens: list[dict],
        temperatura: float = 0.5,
        ferramentas: list[dict] | None = None,
    ) -> dict:
        raise NotImplementedError


class OllamaModelProvider(ModelProvider):
    """
    Provider HTTP para Ollama.
    """

    def __init__(
        self,
        url: str | None = None,
        timeout: int = 300,
    ):
        self.url = url or os.getenv(
            "OLLAMA_URL",
            "http://localhost:11434/api/chat",
        )
        self.timeout = timeout

    def gerar(
        self,
        modelo: str,
        mensagens: list[dict],
        temperatura: float = 0.5,
        ferramentas: list[dict] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "model": modelo,
            "messages": mensagens,
            "stream": False,
            "options": {
                "temperature": temperatura,
            },
        }

        if ferramentas:
            payload["tools"] = ferramentas

        resposta = requests.post(
            self.url,
            json=payload,
            timeout=self.timeout,
        )

        resposta.raise_for_status()

        dados = resposta.json()

        if not isinstance(dados, dict):
            raise RuntimeError(
                "O provedor Ollama retornou uma resposta inválida."
            )

        return dados


def criar_model_provider() -> ModelProvider:
    provider = os.getenv(
        "MODEL_PROVIDER",
        "ollama",
    ).strip().lower()

    if provider == "ollama":
        return OllamaModelProvider()

    raise ValueError(
        f"Model Provider não suportado: '{provider}'."
    )
