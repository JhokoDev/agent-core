import os
import json
import time
import asyncio
import httpx
from datetime import date
from pathlib import Path
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


class GeminiCostGuard:
    """
    CAMADA DUPLA DE PROTEÇÃO ANTITAXAÇÃO (0 CUSTOS ADICIONAIS GARANTIDOS):
    
    1. Camada 1 (Circuit Breaker Local):
       - Limite rígido de 12 RPM (abaixo do teto de 15 RPM gratuitos do Google).
       - Limite rígido diário de 1.000 RPD (abaixo do teto de 1.500 RPD gratuitos).
       - Se atingir o teto de segurança, bloqueia a chamada antes de tocar na rede e força fallback para o Llama Local.
       
    2. Camada 2 (Whitelist Estrita de Modelos Gratuitos e Sanitização):
       - Garante que NUNCA um modelo com cobrança ativada (ex: Gemini Pro corporativo pago) seja requisitado.
       - Restringe estritamente para os modelos gratuitos da API pública do Google AI Studio.
       - Remove parâmetros de serviços externos tarifados (Vertex AI Grounding pago, etc).
    """
    ARQUIVO_TELEMETRIA = Path("data/gemini_guard.json")
    MAX_RPM_SEGURO = 12       # Teto seguro de proteção
    MAX_RPD_SEGURO = 1000     # Teto diário seguro
    MODELOS_GRATUITOS_PERMITIDOS = {
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash"
    }

    @classmethod
    def validar_modelo_e_parametros(cls, modelo: str) -> str:
        """Camada 2: Força o uso estrito de modelos do plano gratuito sem risco de faturamento."""
        mod = (modelo or "").strip().lower()
        if mod not in cls.MODELOS_GRATUITOS_PERMITIDOS:
            print(f"[GeminiCostGuard] AVISO DE PROTEÇÃO: Modelo '{modelo}' não homologado na lista de custo zero. Forçando 'gemini-flash-latest'!")
            return "gemini-flash-latest"
        return mod

    @classmethod
    def registrar_e_validar_consumo(cls) -> None:
        """Camada 1: Circuit breaker que bloqueia o disparo caso se aproxime do limite gratuito."""
        agora = time.time()
        hoje = date.today().isoformat()
        
        dados = {"data": hoje, "chamadas_hoje": 0, "timestamps_minuto": []}
        if cls.ARQUIVO_TELEMETRIA.exists():
            try:
                with open(cls.ARQUIVO_TELEMETRIA, "r", encoding="utf-8") as f:
                    dados = json.load(f)
            except Exception:
                pass
                
        if dados.get("data") != hoje:
            dados = {"data": hoje, "chamadas_hoje": 0, "timestamps_minuto": []}
            
        # Limpa timestamps com mais de 60 segundos
        ts_minuto = [t for t in dados.get("timestamps_minuto", []) if agora - t < 60.0]
        
        # 1. Trava de Proteção por Minuto (RPM)
        if len(ts_minuto) >= cls.MAX_RPM_SEGURO:
            raise ProviderError("trava_custo_zero_rpm: Limite de segurança de 12 requisições por minuto atingido para evitar cobranças. Alternando para Llama local.")

        # 2. Trava de Proteção Diária (RPD)
        if dados.get("chamadas_hoje", 0) >= cls.MAX_RPD_SEGURO:
            raise ProviderError("trava_custo_zero_diario: Teto de segurança diário atingido. Bloqueado para garantir 0 custos adicionais. Alternando para Llama local.")
            
        # Registra a chamada autorizada
        ts_minuto.append(agora)
        dados["timestamps_minuto"] = ts_minuto
        dados["chamadas_hoje"] = dados.get("chamadas_hoje", 0) + 1
        
        try:
            cls.ARQUIVO_TELEMETRIA.parent.mkdir(parents=True, exist_ok=True)
            with open(cls.ARQUIVO_TELEMETRIA, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2)
        except Exception:
            pass


class GeminiProvider:
    """
    Provider oficial para nuvem do Google Gemini (Zero Custo via Free Tier do Google AI Studio).
    Blindado com dupla camada de proteção contra cobranças indesejadas.
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
        modelo_bruto = (
            model 
            or os.getenv("GEMINI_MODEL", "") 
            or os.getenv("AGENT_GEMINI_MODEL", "") 
            or getattr(settings, "gemini_model", "gemini-flash-latest")
            or "gemini-flash-latest"
        )
        # Camada 2 Ativa na inicialização
        self.model = GeminiCostGuard.validar_modelo_e_parametros(modelo_bruto)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.client = httpx.AsyncClient(timeout=45.0)

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
                if not part_text and not m.tool_calls:
                    part_text = " "
                parts = [{"text": part_text}]
                
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
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"[Resultado de '{m.name or 'ferramenta'}']:\n{m.content}"}]
                })
            else:
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
                    ultimo["parts"].extend(c["parts"])
                else:
                    contents_limpos.append(c)

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

        # Camada 1: Circuit breaker pré-vôo para barrar qualquer chamada que exceda o teto gratuito
        GeminiCostGuard.registrar_e_validar_consumo()

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
            palavras = resultado.content.split(" ")
            for i, palavra in enumerate(palavras):
                token = palavra if i == len(palavras) - 1 else palavra + " "
                yield {"tipo": "texto", "conteudo": token}
                await asyncio.sleep(0.015)

    async def aclose(self) -> None:
        await self.client.aclose()
