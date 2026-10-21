import os
import json
import asyncio
import httpx
from typing import Any, AsyncGenerator

from app.core.config import Settings
from app.models.base import ChatResult, Message, ModelHealth, ProviderError


def _converter_schema_para_gemini(s: Any) -> Any:
    """Converte esquemas OpenAPI/JSON Schema para a convenção rígida do Google Gemini."""
    if not isinstance(s, dict):
        return s
        
    res = {}
    type_map = {
        "object": "OBJECT",
        "string": "STRING",
        "number": "NUMBER",
        "integer": "INTEGER",
        "boolean": "BOOLEAN",
        "array": "ARRAY"
    }
    
    for k, v in s.items():
        if k == "type" and isinstance(v, str):
            res["type"] = type_map.get(v.lower(), v.upper())
        elif k == "properties" and isinstance(v, dict):
            res["properties"] = {pk: _converter_schema_para_gemini(pv) for pk, pv in v.items()}
        elif k == "items" and isinstance(v, dict):
            res["items"] = _converter_schema_para_gemini(v)
        elif k in ("description", "required", "enum"):
            res[k] = v
            
    return res


class GeminiProvider:
    """
    Provider oficial para nuvem do Google Gemini (Zero Custo via Free Tier do Google AI Studio).
    Suporta Function Calling de alta inteligência e streaming de resposta.
    """

    def __init__(self, settings: Settings, api_key: str | None = None, model: str | None = None):
        from dotenv import load_dotenv
        load_dotenv()
        self.settings = settings
        self.api_key = (
            api_key 
            or os.getenv("GEMINI_API_KEY", "") 
            or os.getenv("AGENT_GEMINI_API_KEY", "") 
            or getattr(settings, "gemini_api_key", "")
        )
        self.model = (
            model 
            or os.getenv("GEMINI_MODEL", "") 
            or os.getenv("AGENT_GEMINI_MODEL", "") 
            or getattr(settings, "gemini_model", "gemini-flash-latest")
            or "gemini-flash-latest"
        )
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def health(self) -> ModelHealth:
        if not self.api_key:
            return ModelHealth(status="unreachable", model=self.model)
        try:
            url = f"{self.base_url}/models/{self.model}?key={self.api_key}"
            resp = await self.client.get(url, timeout=10.0)
            if resp.status_code == 200:
                return ModelHealth(status="ready", model=self.model)
            return ModelHealth(status="unreachable", model=self.model)
        except Exception:
            return ModelHealth(status="unreachable", model=self.model)

    def _preparar_payload(self, messages: list[Message], tools: list[dict] | None = None) -> dict[str, Any]:
        system_prompts: list[str] = []
        contents: list[dict[str, Any]] = []

        for m in messages:
            if m.role == "system":
                if m.content.strip():
                    system_prompts.append(m.content)
            elif m.role == "assistant":
                role_gemini = "model"
                part_text = m.content or ""
                # Se a mensagem do assistente for vazia, garante ao menos um espaço
                if not part_text and not m.tool_calls:
                    part_text = " "
                parts = [{"text": part_text}]
                
                # Se havia tool calls anteriores
                if m.tool_calls:
                    for tc in m.tool_calls:
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        parts.append({
                            "functionCall": {
                                "name": fn.get("name", "ferramenta"),
                                "args": args
                            }
                        })
                contents.append({"role": role_gemini, "parts": parts})
            elif m.role == "tool":
                # Resposta de ferramenta
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"[Resultado de '{m.name or 'ferramenta'}']:\n{m.content}"}]
                })
            else:
                # User
                contents.append({
                    "role": "user",
                    "parts": [{"text": m.content or " "}]
                })

        # Garante alternância estrita de turnos (user -> model -> user -> model)
        contents_limpos: list[dict[str, Any]] = []
        for c in contents:
            if not contents_limpos:
                contents_limpos.append(c)
            else:
                ultimo = contents_limpos[-1]
                if ultimo["role"] == c["role"]:
                    # Mescla as partes do mesmo papel
                    ultimo["parts"].extend(c["parts"])
                else:
                    contents_limpos.append(c)

        # Se começar com 'model', insere um turno inicial de usuário para validar no Gemini
        if contents_limpos and contents_limpos[0]["role"] == "model":
            contents_limpos.insert(0, {"role": "user", "parts": [{"text": "Iniciar."}]})

        payload: dict[str, Any] = {
            "contents": contents_limpos,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048
            }
        }

        if system_prompts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_prompts)}]
            }

        if tools:
            gemini_decls = []
            for t in tools:
                fn = t.get("function", {})
                if not fn:
                    continue
                params = _converter_schema_para_gemini(fn.get("parameters", {}))
                gemini_decls.append({
                    "name": fn.get("name"),
                    "description": fn.get("description", ""),
                    "parameters": params
                })
            if gemini_decls:
                payload["tools"] = [{"functionDeclarations": gemini_decls}]

        return payload

    async def chat(self, messages: list[Message], tools: list[dict] | None = None) -> ChatResult:
        if not messages:
            raise ProviderError("empty_messages")
        if not self.api_key:
            raise ProviderError("gemini_api_key_missing")

        payload = self._preparar_payload(messages, tools)
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        try:
            resp = await self.client.post(url, json=payload, timeout=45.0)
            resp.raise_for_status()
            body = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ProviderError("gemini_rate_limit_exceeded") from e
            raise ProviderError(f"gemini_request_failed_{e.response.status_code}") from e
        except Exception as e:
            raise ProviderError(f"gemini_connection_error: {e}") from e

        content = ""
        tool_calls: list[dict] | None = None

        candidates = body.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                if "text" in p:
                    content += p["text"]
                if "functionCall" in p:
                    fc = p["functionCall"]
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "function": {
                            "name": fc.get("name"),
                            "arguments": fc.get("args", {})
                        }
                    })

        return ChatResult(content=content, model=self.model, tool_calls=tool_calls)

    async def chat_stream(self, messages: list[Message], tools: list[dict] | None = None) -> AsyncGenerator[dict[str, Any], None]:
        """Gera resposta em streaming com efeito cascata no front."""
        resultado = await self.chat(messages, tools)

        if resultado.tool_calls:
            yield {"tipo": "tools", "conteudo": resultado.tool_calls}

        if resultado.content:
            # Emite pequenos pedaços para manter a fluidez de digitação instantânea
            palavras = resultado.content.split(" ")
            for i, palavra in enumerate(palavras):
                token = palavra if i == len(palavras) - 1 else palavra + " "
                yield {"tipo": "texto", "conteudo": token}
                await asyncio.sleep(0.015)

    async def aclose(self) -> None:
        await self.client.aclose()
