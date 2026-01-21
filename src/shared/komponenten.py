import os
import streamlit as st

from src.shared.llm_integrations.llm_provider import LLMProvider, LLMProviderHandler
from src.shared.logger import get_logger

log = get_logger(__name__)


def komponenten_config(komponente_pfad: str = __file__) -> str:
    config = st.session_state["config"]
    komponente_name = komponentenname_von_datei(komponente_pfad)
    komponente_config = config.get("komponente", {}).get(komponente_name, {})
    return komponente_config


def komponentenname_von_datei(komponente_pfad) -> str:
    return os.path.basename(komponente_pfad).split(".")[0]


class KomponentenAPI:
    def __init__(self, komponenten_name: str):
        self.komponenten_name = komponenten_name
        self.config: str = komponenten_config(self.komponenten_name)

    def hole_llm_provider_handler(self) -> LLMProviderHandler:
        llm_provider_handler: LLMProviderHandler = st.session_state[
            "llm_provider_handler"
        ]
        return llm_provider_handler

    def streamlit_llm_provider_auswahl(self) -> LLMProvider:

        llm_provider: LLMProvider = None

        llm_provider_handler: LLMProviderHandler = self.hole_llm_provider_handler()

        model = st.selectbox(
            "LLM-Modell, mit dem generiert werden soll",
            llm_provider_handler.hole_models(),
            placeholder="Modell auswählen",
        )

        if model and model != "Modell auswählen":
            llm_provider = llm_provider_handler.hole_provider(model=model)

        return llm_provider

    def text(self, text_key: str):
        # Zuerst in Komponente gucken
        text = self.config.get("text", {}).get(text_key, "")
        if not text:

            # Sonst in App gucken
            app_config = st.session_state["config"]
            text = app_config.get("text", {}).get(text_key, text_key)
        return text
