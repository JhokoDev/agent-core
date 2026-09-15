import httpx
from app.config import Settings
from app.models.base import ChatResult, Message, ModelHealth, ProviderError


class OllamaProvider:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.client = httpx.AsyncClient(base_url=settings.ollama_url, trust_env=False,
                                       follow_redirects=False, transport=transport)

    async def health(self) -> ModelHealth:
        status = "ready"
        try:
            response = await self.client.get("/api/tags", timeout=self.settings.health_timeout)
            response.raise_for_status()
            models = response.json()["models"]
            if not isinstance(models, list) or any(not isinstance(m, dict) or not isinstance(m.get("name"), str) for m in models):
                raise ValueError("invalid models")
            if self.settings.model not in {m["name"] for m in models}:
                status = "model_missing"
        except httpx.HTTPError:
            status = "unreachable"
        except (ValueError, KeyError, TypeError):
            status = "invalid_response"
        return ModelHealth(status=status, model=self.settings.model)

    async def chat(self, messages: list[Message]) -> ChatResult:
        if not messages:
            raise ProviderError("empty_messages")
        payload = {"model": self.settings.model, "messages": [m.model_dump() for m in messages],
                   "stream": False, "keep_alive": "1m",
                   "options": {"num_ctx": self.settings.context_window,
                               "num_predict": self.settings.max_output_tokens}}
        try:
            response = await self.client.post("/api/chat", json=payload,
                                              timeout=self.settings.generation_timeout)
            response.raise_for_status()
            body = response.json()
            content = body["message"]["content"]
            if body.get("done") is not True or not isinstance(content, str) or not content.strip():
                raise ValueError("incomplete response")
            return ChatResult(content=content, model=self.settings.model)
        except httpx.HTTPError:
            raise ProviderError("ollama_request_failed") from None
        except (KeyError, TypeError, ValueError):
            raise ProviderError("ollama_invalid_response") from None

    async def aclose(self) -> None:
        await self.client.aclose()
