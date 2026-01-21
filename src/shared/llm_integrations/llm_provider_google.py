from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from src.shared.llm_integrations.llm_provider import LLMProvider


class LLMProviderGoogle(LLMProvider):
    def __init__(self, models: list[str]):
        super().__init__(models=models)

    def hole_instanz(self, model):
        self.llm_instanz = ChatGoogleGenerativeAI(
            model=model,
            temperature=0,  # Gemini 3.0+ defaults to 1.0
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # other params...
        )
        return self.llm_instanz

    def parse_content(self, response: AIMessage):
        # https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai
        # response.content  # -> [{"type": "text", "text": "Hello!", "extras": {"signature": "EpQFCp...lKx64r"}}]
        # response.text     # -> "Hello!"
        return response.text
