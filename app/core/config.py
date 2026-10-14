from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Mudámos extra para "ignore" para que variáveis temporárias no .env não quebrem o servidor
    model_config = SettingsConfigDict(env_prefix="AGENT_", env_file=".env", extra="ignore")
    
    api_token: SecretStr
    data_dir: Path = Path("data")
    host: Literal["127.0.0.1", "::1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    model_provider: Literal["ollama"] = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    
    # Modelo Principal
    model: str = Field(default="hf.co/unsloth/gpt-oss-20b-GGUF:Q4_K_M", min_length=1, max_length=160)
    
    # --- VARIÁVEIS EXTRAS QUE FALTAVAM NA CLASSE ---
    model_padrao: str = "hf.co/unsloth/gpt-oss-20b-GGUF:Q4_K_M"
    model_simples: str = "llama3.2:1b"
    model_codigo: str = "hf.co/unsloth/gpt-oss-20b-GGUF:Q4_K_M"
    model_complexo: str = "hf.co/unsloth/gpt-oss-20b-GGUF:Q4_K_M"
    
    llm_api_base: str = "http://127.0.0.1:11434"
    mqtt_broker: str = "127.0.0.1"
    mqtt_port: int = 1883
    # -----------------------------------------------

    context_window: int = Field(default=8192, ge=512, le=16384)
    max_output_tokens: int = Field(default=4096, ge=1, le=8192)
    health_timeout: float = Field(default=5, gt=0, le=30)
    # Modelos de 20B precisam de mais tempo para pensar (aumentado para 300 segundos / 5 minutos)
    generation_timeout: float = Field(default=300, gt=0, le=1200)

    @field_validator("api_token")
    @classmethod
    def validate_token(cls, value: SecretStr) -> SecretStr:
        token = value.get_secret_value()
        if len(token) < 32 or token == "CHANGE_ME" or token.strip() != token:
            raise ValueError("Configure um token aleatório de pelo menos 32 caracteres")
        return value

    @field_validator("ollama_url")
    @classmethod
    def local_ollama_only(cls, value: str) -> str:
        parts = urlsplit(value)
        if (parts.scheme != "http" or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
                or parts.username or parts.password or parts.query or parts.fragment
                or parts.path not in {"", "/"}):
            raise ValueError("Fase 0 aceita Ollama somente no loopback HTTP")
        _ = parts.port
        return value.rstrip("/")

    @property
    def database_path(self) -> Path:
        return self.data_dir / "memory.db"