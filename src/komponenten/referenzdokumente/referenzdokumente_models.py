from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages.utils import AnyMessage

from src.shared.generator import LLM, Prompt


@dataclass(frozen=True)
class Referenzdokument:
    id: str
    art: str  # "PDF" | "URL"
    name: str
    pfad: str
    erstellungsdatum: str

    @classmethod
    def from_dict(cls, data) -> Referenzdokument:
        return cls(
            id=data["id"],
            art=data["art"],
            name=data["name"],
            pfad=data["pfad"],
            erstellungsdatum=data.get("erstellungsdatum", ""),
        )


@dataclass(frozen=True)
class ZusammenfassungAuswahl:
    text_zusammenfassen: bool
    text_zusammenfassen_mit_zahlen: bool
    tabellen_extrahieren: bool
    tabellen_zusammenfassen: bool
    tabellen_zusammenfassen_mit_zahlen: bool

    def soll_vorbereitet_werden(self) -> bool:
        if self.text_zusammenfassen or self.tabellen_extrahieren:
            return True
        return False

    @classmethod
    def from_dict(cls, data) -> ZusammenfassungAuswahl:
        return cls(
            text_zusammenfassen=data["text_zusammenfassen"],
            text_zusammenfassen_mit_zahlen=data["text_zusammenfassen_mit_zahlen"],
            tabellen_extrahieren=data["tabellen_extrahieren"],
            tabellen_zusammenfassen=data["tabellen_zusammenfassen"],
            tabellen_zusammenfassen_mit_zahlen=data[
                "tabellen_zusammenfassen_mit_zahlen"
            ],
        )


@dataclass(frozen=True)
class ReferenzdokumentAuswahl:
    referenzdokument: Referenzdokument
    zusammenfassung_auswahl: ZusammenfassungAuswahl


class ReferenzdokumentState(MessagesState):
    referenzdokument: Referenzdokument
    zusammenfassung_auswahl: ZusammenfassungAuswahl
    aktuelles_referenzdokument: int
    anzahl_referenzdokumente: int
    text_extrahiert: str
    text_zusammengefasst: str
    text_zusammengefasst_messages: Annotated[list[AnyMessage], add_messages]
    tabellen_extrahiert: list[str]
    tabellen_zusammengefasst: list[str]
    tabellen_zusammengefasst_messages: list[Annotated[list[AnyMessage], add_messages]]


@dataclass(frozen=True)
class Zusammenfassung:
    referenzdokument: Referenzdokument
    zusammenfassung_auswahl: ZusammenfassungAuswahl
    erstellungsdatum: str
    text_extrahiert: str
    text_zusammengefasst: str
    tabellen_extrahiert: list[str]
    tabellen_zusammengefasst: list[str]
    prompt: Prompt
    llm: LLM

    @classmethod
    def from_dict(cls, data) -> Zusammenfassung:

        referenzdokument = data.get("referenzdokument")
        if isinstance(referenzdokument, dict):
            referenzdokument = Referenzdokument.from_dict(referenzdokument)

        zusammenfassung_auswahl = data.get("zusammenfassung_auswahl")
        if isinstance(zusammenfassung_auswahl, dict):
            zusammenfassung_auswahl = ZusammenfassungAuswahl.from_dict(
                zusammenfassung_auswahl
            )

        prompt = data.get("prompt", {})
        if isinstance(prompt, dict):
            prompt = Prompt.from_dict(prompt)

        llm = data.get("llm", {})
        if isinstance(llm, dict):
            llm = LLM.from_dict(llm)

        return cls(
            referenzdokument=referenzdokument,
            zusammenfassung_auswahl=zusammenfassung_auswahl,
            erstellungsdatum=data["erstellungsdatum"],
            text_extrahiert=data["text_extrahiert"],
            text_zusammengefasst=data["text_zusammengefasst"],
            tabellen_extrahiert=list(data.get("tabellen_extrahiert", [])),
            tabellen_zusammengefasst=list(data.get("tabellen_zusammengefasst", [])),
            prompt=prompt,
            llm=llm,
        )
