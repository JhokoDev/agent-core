from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_", env_file=".env", extra="forbid")
    api_token: SecretStr
    data_dir: Path = Path("data")
    host: Literal["127.0.0.1", "::1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    model_provider: Literal["ollama"] = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = Field(default="qwen3.5:2b", min_length=1, max_length=160)
    context_window: int = Field(default=2048, ge=512, le=8192)
    max_output_tokens: int = Field(default=128, ge=1, le=2048)
    health_timeout: float = Field(default=3, gt=0, le=30)
    generation_timeout: float = Field(default=120, gt=0, le=600)

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
