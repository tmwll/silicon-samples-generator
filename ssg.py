import streamlit as st

from dotenv import load_dotenv, dotenv_values
from src.shared.komponenten import komponentenname_von_datei
from src.shared.llm_integrations.llm_provider import LLMProviderHandler
from src.shared.llm_integrations.llm_provider_deepseek import LLMProviderDeepSeek
from src.shared.llm_integrations.llm_provider_google import LLMProviderGoogle
from src.shared.llm_integrations.llm_provider_mistral import LLMProviderMistral
from src.shared.llm_integrations.llm_provider_openai import LLMProviderOpenAI
from src.shared.logger import setup_logging
from src.shared.toml_config import TOMLConfig

load_dotenv()
setup_logging()

setup_logging()
app_config = TOMLConfig("ssg.toml")

pages: dict = {}

for komponente in app_config.get_section("komponenten"):
    if not komponente.get("active", False):
        continue

    komponente_path = komponente.get("path")
    if not komponente_path:
        continue

    komponente_configfile = komponente.get("config")
    if not komponente_configfile:
        continue

    komponente_name = komponentenname_von_datei(komponente_path)

    app_config.load_config(
        config_file=komponente_configfile,
        namespace=f"komponente.{komponente_name}",
    )

    komponente_page_title = (
        app_config.config.get("komponente", {})
        .get(komponente_name, {})
        .get("page", {})
        .get("title", "")
    )

    if komponente.get("active", False):

        group: str = ""
        if komponente.get("grouped", False):
            group = "Komponenten"

        pages.setdefault(group, []).append(
            st.Page(komponente_path, title=komponente_page_title)
        )

st.session_state["config"] = app_config.config
st.session_state["config"]["dotenv"] = dotenv_values(".env")

st.session_state["llm_provider_handler"] = LLMProviderHandler(
    [
        LLMProviderGoogle(
            models=[
                "gemini-3-pro-preview",
                "gemini-2.0-flash",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
            ]
        ),
        LLMProviderOpenAI(models=["gpt-5-mini", "gpt-5.2"]),
        LLMProviderDeepSeek(models=["deepseek-chat"]),
        LLMProviderMistral(
            models=[
                "mistral-large-latest",
                "mistral-small-2506",
                "ministral-3b-2512",
                "ministral-8b-2512",
            ]
        ),
    ]
)

st.set_page_config(layout="wide")
app = st.navigation(pages, position="sidebar")

app.run()
