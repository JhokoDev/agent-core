from app.core.config import Settings
from app.models.base import ModelProvider
from app.models.ollama import OllamaProvider
from app.models.gemini import GeminiProvider


def create_provider(settings: Settings, provider_name: str | None = None) -> ModelProvider:
    factories = {
        "ollama": OllamaProvider,
        "local": OllamaProvider,
        "gemini": GeminiProvider,
        "nuvem": GeminiProvider
    }
    p = (provider_name or settings.model_provider or "ollama").strip().lower()
    factory = factories.get(p, OllamaProvider)
    return factory(settings)
