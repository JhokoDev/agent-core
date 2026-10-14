import httpx
import json
from app.core.config import Settings
from app.models.base import ChatResult, Message, ModelHealth, ProviderError


class OllamaProvider:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.ollama_url, 
            trust_env=False,
            follow_redirects=False, 
            transport=transport
        )

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

    async def chat(self, messages: list[Message], tools: list[dict] | None = None) -> ChatResult:
        if not messages:
            raise ProviderError("empty_messages")
            
        payload = {
            "model": self.settings.model, 
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "stream": False, 
            "keep_alive": "1m",
            "options": {
                "num_ctx": self.settings.context_window,
                "num_predict": self.settings.max_output_tokens
            }
        }
        
        if tools:
            payload["tools"] = tools

        try:
            response = await self.client.post("/api/chat", json=payload, timeout=self.settings.generation_timeout)
            response.raise_for_status()
            body = response.json()
            
            mensagem_resp = body.get("message", {})
            content = mensagem_resp.get("content", "")
            tool_calls = mensagem_resp.get("tool_calls", None)
            reasoning = mensagem_resp.get("thinking") or mensagem_resp.get("reasoning_content")
            
            if body.get("done") is not True:
                raise ValueError("incomplete response")
                
            return ChatResult(content=content, model=self.settings.model, tool_calls=tool_calls, reasoning=reasoning)
            
        except httpx.HTTPError:
            raise ProviderError("ollama_request_failed") from None
        except (KeyError, TypeError, ValueError):
            raise ProviderError("ollama_invalid_response") from None

    async def aclose(self) -> None:
        await self.client.aclose()

    async def chat_stream(self, messages: list[Message], tools: list[dict] | None = None):
        """Novo método que gera o Efeito Cascata (Streaming Real-Time)"""
        if not messages:
            raise ProviderError("empty_messages")
            
        payload = {
            "model": self.settings.model, 
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "stream": True, # A MÁGICA ACONTECE AQUI!
            "keep_alive": "1m",
            "options": {
                "num_ctx": self.settings.context_window,
                "num_predict": self.settings.max_output_tokens
            }
        }
        
        if tools:
            payload["tools"] = tools

        try:
            async with self.client.stream("POST", "/api/chat", json=payload, timeout=self.settings.generation_timeout) as response:
                response.raise_for_status()
                tool_calls_agg = []
                
                async for line in response.aiter_lines():
                    if not line: continue
                    body = json.loads(line)
                    mensagem_resp = body.get("message", {})
                    
                    thinking_chunk = mensagem_resp.get("thinking") or mensagem_resp.get("reasoning_content")
                    if thinking_chunk:
                        yield {"tipo": "thinking", "conteudo": thinking_chunk}

                    chunk = mensagem_resp.get("content", "")
                    if chunk:
                        yield {"tipo": "texto", "conteudo": chunk}
                        
                    if "tool_calls" in mensagem_resp:
                        tool_calls_agg.extend(mensagem_resp["tool_calls"])
                        
                if tool_calls_agg:
                    yield {"tipo": "tools", "conteudo": tool_calls_agg}
                    
        except httpx.HTTPError:
            raise ProviderError("ollama_request_failed") from None
        except (KeyError, TypeError, ValueError):
            raise ProviderError("ollama_invalid_response") from None