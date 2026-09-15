from app.config import Settings
from app.models.base import ModelProvider
from app.models.ollama import OllamaProvider


def create_provider(settings: Settings) -> ModelProvider:
    # Seleção por backend; nenhuma decisão por nome/família do modelo.
    factories = {"ollama": OllamaProvider}
    return factories[settings.model_provider](settings)
