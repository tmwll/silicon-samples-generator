from __future__ import annotations
from abc import abstractmethod
from langchain_core.messages import AIMessage


class LLMProvider:
    def __init__(self, models: list[str]):
        self.models: list[str] = models

    def hole_models(self) -> list[str]:
        return self.models

    def aktiviere_model(self, model: str):
        self.aktives_model = model

    @abstractmethod
    def hole_instanz(self, model: str):
        """Muss vom Kind implementiert werden."""
        raise NotImplementedError

    @abstractmethod
    def parse_content(self, response: AIMessage) -> str:
        """Muss vom Kind implementiert werden."""
        raise NotImplementedError


class LLMProviderHandler:

    provider_models: dict[str, LLMProvider] = {}

    def __init__(self, llm_provider: list[LLMProvider]):
        for provider in llm_provider:
            models = provider.hole_models()
            for model in models:
                self.provider_models[model] = provider

    def hole_provider(self, model: str) -> LLMProvider:
        try:
            provider: LLMProvider = self.provider_models[model]
            provider.aktiviere_model(model=model)
            return provider
        except KeyError as e:
            raise KeyError(
                f"Unbekanntes Modell: {model}. Verfügbar: {list(self.provider_models)}"
            ) from e

    def hole_models(self) -> list[str]:
        return list(self.provider_models)
