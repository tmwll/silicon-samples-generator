from langchain_core.messages import AIMessage
from langchain_mistralai import ChatMistralAI
from src.shared.llm_integrations.llm_provider import LLMProvider


class LLMProviderMistral(LLMProvider):
    def __init__(self, models: list[str]):
        super().__init__(models=models)

    def hole_instanz(self, model):
        self.llm_instanz = ChatMistralAI(
            model=model,
            temperature=0,
            max_retries=2,
            # other params...
        )
        return self.llm_instanz

    def parse_content(self, response: AIMessage):
        # https://docs.langchain.com/oss/python/integrations/chat/deepseek
        return response.content
