from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from langgraph.graph import StateGraph
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.messages.ai import UsageMetadata
import streamlit as st

from src.shared.llm_integrations.llm_provider import LLMProvider
from src.shared.logger import get_logger

log = get_logger(__name__)


class LLMGenerator:
    def __init__(
        self,
        prompt: Prompt,
        llm_provider: LLMProvider,
        state_class: Any,
        thread_prefix,
    ):
        self.prompt = prompt
        self.llm_provider = llm_provider
        self.state_class = state_class
        self.thread_prefix = thread_prefix

        self.graph = StateGraph(self.state_class)

        self.llm_callback = UsageMetadataCallbackHandler()

        self.startzeit = datetime.now()

    def startzeit_formatiert(self):
        return self.startzeit.strftime("%Y%m%d-%H%M%S")

    def thread_id(self):
        return f"{self.thread_prefix}-{self.startzeit_formatiert()}"

    def llm_config_holen(self) -> dict:
        """
        Extrahiert die wichtigsten Parameter aus dem LLM-Objekt als Dict.
        """
        # Je nach LangChain/Pydantic-Version:

        llm_instanz = self.llm_provider.hole_instanz(
            model=self.llm_provider.aktives_model
        )

        if hasattr(llm_instanz, "model_dump"):
            raw = llm_instanz.model_dump()  # Pydantic v2
        elif hasattr(llm_instanz, "dict"):
            raw = llm_instanz.dict()  # Pydantic v1
        else:
            # Fallback: Direkt über Attribute gehen
            raw = {
                "model": getattr(llm_instanz, "model", None),
                "temperature": getattr(llm_instanz, "temperature", None),
                "max_tokens": getattr(llm_instanz, "max_tokens", None),
                "timeout": getattr(llm_instanz, "timeout", None),
                "max_retries": getattr(llm_instanz, "max_retries", None),
            }

        # Dinge rausfiltern, die du nicht speichern willst (Keys sind Beispiele)
        blacklist = {
            # "client",
            # "streaming",
            # "callback_manager",
            # "openai_api_key",
            # "google_api_key",
            "api_key",
        }
        clean = {
            k: v
            for k, v in raw.items()
            if k not in blacklist
            and not k.startswith("_")
            and not k.endswith("_api_key")
        }

        return clean

    def aufrufen(
        self, state, streamlit_fortschritt, run_name: str, reset_tokenverbrauch=False
    ):
        log.info("LLM-Aufruf gestartet")

        if reset_tokenverbrauch:
            self.llm_callback = UsageMetadataCallbackHandler()

        out = self.graph.invoke(
            state,
            config={
                "run_name": run_name,
                "configurable": {
                    "llm_provider": self.llm_provider,
                    "thread_id": self.thread_id(),
                    "streamlit_fortschritt": streamlit_fortschritt,
                    "prompt": self.prompt,
                    "tokenverbrauch": self.llm_tokenverbrauch(),
                },
                "callbacks": [self.llm_callback],
            },
        )
        log.info("LLM-Aufruf beendet")
        return out

    def llm_tokenverbrauch(self) -> dict[str, LLMTokenverbrauch]:
        # Summiert automatisch alle Verbrauche auf
        tokenverbraeuche: dict[str, LLMTokenverbrauch] = {
            key: LLMTokenverbrauch.from_dict(
                {
                    "input_tokens": value.get("input_tokens", 0),
                    "output_tokens": value.get("output_tokens", 0),
                    "total_tokens": value.get("total_tokens", 0),
                    "input_token_details": value.get("input_token_details", {}) or {},
                    "output_token_details": value.get("output_token_details", {}) or {},
                }
            )
            for key, value in self.llm_callback.usage_metadata.items()
        }
        return tokenverbraeuche


def schicke_update_an_user(text):
    log.info(text)
    st.toast(text, duration="infinite")


def hole_llm_provider_aus_graph(config) -> LLMProvider:
    llm_provider: LLMProvider = config.get("configurable", {}).get("llm_provider", {})
    return llm_provider


def hole_llm_instanz_aus_graph(config):
    llm_provider: LLMProvider = hole_llm_provider_aus_graph(config)
    return llm_provider.hole_instanz(model=llm_provider.aktives_model)


def parse_llm_content(response: AIMessage, config):
    llm_provider: LLMProvider = hole_llm_provider_aus_graph(config)
    return llm_provider.parse_content(response=response)


def hole_tokenverbrauch_aus_graph(config) -> int:
    tokenverbrauch: dict[str, LLMTokenverbrauch] = config.get("configurable", {}).get(
        "tokenverbrauch", {}
    )
    return tokenverbrauch_summieren(tokenverbrauch=tokenverbrauch)


def tokenverbrauch_summieren(tokenverbrauch: dict[str, LLMTokenverbrauch]) -> int:
    anzahl_token = 0

    for key, value in tokenverbrauch.items():
        anzahl_token += value.get("total_tokens", 0)

    return anzahl_token


def format_number(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def hole_prompt_aus_graph(prompt_name: str, config, prompt_data: dict[str, Any] = {}):
    prompt: Prompt = config.get("configurable", {}).get("prompt", {})

    # Gewünschten Prompt holen
    alle_prompts: dict[str, str] = prompt.prompts
    prompt_template = alle_prompts.get(prompt_name, None)

    # Prompt mit Daten parsen
    return prompt_template.format_map(SafeDict(prompt_data))


def hole_prompt_data_aus_graph(prompt_data_name, config):
    prompt: Prompt = config.get("configurable", {}).get("prompt", {})
    prompt_data: dict[str, str] = prompt.prompt_data
    return prompt_data.get(prompt_data_name, None)


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"  # lässt den Platzhalter unverändert


@dataclass(frozen=True)
class Prompt:
    prompts: dict[str, str]
    prompt_data: dict[str, Any]

    @classmethod
    def from_dict(cls, data) -> Prompt:

        return cls(
            prompts=data.get("prompts", {}),
            prompt_data=data.get("prompt_data", {}),
        )


@dataclass(frozen=True)
class LLMTokenverbrauch(UsageMetadata):

    @classmethod
    def from_dict(cls, data) -> LLMTokenverbrauch:
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            input_token_details=data.get("input_token_details", {}),
            output_token_details=data.get("output_token_details", {}),
        )


@dataclass(frozen=True)
class LLMChatverlauf:
    name: str
    chatverlauf: list[Any]

    @classmethod
    def from_dict(cls, data) -> LLMChatverlauf:
        return cls(
            name=data["name"],
            chatverlauf=list(data.get("chatverlauf", [])),
        )


@dataclass(frozen=True)
class LLM:
    konfiguration: dict[str, Any]
    tokenverbrauch: dict[str, LLMTokenverbrauch]
    chatverlaeufe: list[LLMChatverlauf]

    @classmethod
    def from_dict(cls, data) -> LLM:

        tokenverbrauch = {
            key: LLMTokenverbrauch.from_dict(value)
            for key, value in data.get("tokenverbrauch", []).items()
        }
        chatverlaeufe = [
            LLMChatverlauf.from_dict(item) for item in data.get("chatverlaeufe", [])
        ]

        return cls(
            konfiguration=data.get("konfiguration", {}),
            chatverlaeufe=chatverlaeufe,
            tokenverbrauch=tokenverbrauch,
        )


def parse_content(msg: dict[str, Any]) -> str:
    """
    Regeln:
    - Wenn content ein String ist: direkt zurückgeben
    - Wenn content ein Dict ist: den String aus dem Key holen, der so heißt wie msg["type"]
      (z.B. type="ai" -> content["ai"])
    - Wenn content eine Liste ist: typische Blockformate (z.B. [{"type":"text","text":"..."}]) zusammenführen
    - Fallback: str(content)
    """
    msg_type = msg.get("type")
    content = msg.get("content")

    # 1) content ist schon ein String
    if isinstance(content, str):
        return content

    # 2) content ist ein Dict -> Key anhand msg["type"]
    if isinstance(content, dict):
        if isinstance(msg_type, str) and msg_type in content:
            val = content[msg_type]
            return val if isinstance(val, str) else str(val)
        # optionaler Fallback, falls key fehlt
        return str(content)

    # 3) content ist eine Liste (z.B. multimodale/Block-Outputs)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # häufig: {"type":"text","text":"..."}
                if "text" in item and isinstance(item["text"], str):
                    parts.append(item["text"])
                # optional: andere mögliche Felder
                elif "content" in item and isinstance(item["content"], str):
                    parts.append(item["content"])
                else:
                    # wenn du lieber "unbekanntes" ignorieren willst: continue
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)

    # 4) sonstiges (None, int, etc.)
    return "" if content is None else str(content)


def parse_chatverlauf(chatverlauf: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Gibt eine Liste mit {"type": ..., "content": ...} zurück, sauber geparst.
    """
    out: list[dict[str, str]] = []
    for msg in chatverlauf:
        out.append(
            {
                "type": str(msg.get("type", "")),
                "content": parse_content(msg),
            }
        )
    return out
