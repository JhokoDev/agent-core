from app.ai.model_contract import ModelContract


class ModelRegistry:
    """
    Registro central dos modelos disponíveis no Agent Core.
    """

    def __init__(self):
        self._modelos: dict[str, ModelContract] = {}

    def registrar(
        self,
        modelo: ModelContract,
    ) -> None:
        valido, erro = modelo.validar()

        if not valido:
            raise ValueError(
                f"Modelo inválido: {erro}"
            )

        if modelo.id in self._modelos:
            raise ValueError(
                f"O modelo '{modelo.id}' já está registrado."
            )

        self._modelos[modelo.id] = modelo

    def obter(
        self,
        modelo_id: str,
    ) -> ModelContract | None:
        return self._modelos.get(modelo_id)

    def selecionar(
        self,
        modelo_id: str,
        fallback_id: str = "llama3.2:1b",
    ) -> tuple[ModelContract, bool]:
        """
        Seleciona um modelo registrado.

        Retorna:
            (modelo, fallback_utilizado)
        """

        modelo = self.obter(modelo_id)

        if modelo is not None:
            return modelo, False

        fallback = self.obter(fallback_id)

        if fallback is None:
            raise ValueError(
                f"O modelo '{modelo_id}' não está registrado "
                f"e o fallback '{fallback_id}' também não está disponível."
            )

        return fallback, True

    def existe(
        self,
        modelo_id: str,
    ) -> bool:
        return modelo_id in self._modelos

    def listar(self) -> list[ModelContract]:
        return list(self._modelos.values())

    def remover(
        self,
        modelo_id: str,
    ) -> bool:
        if modelo_id not in self._modelos:
            return False

        del self._modelos[modelo_id]
        return True

    def limpar(self) -> None:
        self._modelos.clear()


def criar_registry_padrao() -> ModelRegistry:
    from app.ai.model_profile import criar_modelos_padrao

    registry = ModelRegistry()

    for modelo in criar_modelos_padrao():
        registry.registrar(modelo)

    return registry
