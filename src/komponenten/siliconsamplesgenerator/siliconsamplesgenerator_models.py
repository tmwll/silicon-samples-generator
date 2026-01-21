from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
from langgraph.graph import MessagesState
from src.komponenten.referenzdokumente.referenzdokumente_models import (
    Zusammenfassung,
)
from src.komponenten.studienkonfiguration.studienkonfigurationslader.models import (
    Frage,
    Option,
)
from src.shared.generator import LLM, Prompt

from src.shared.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class AntwortThemaOption:
    thema_key: Optional[str]
    thema_name: Optional[str]
    option_key: str

    def hat_echtes_thema(self) -> bool:
        if not self.thema_key:
            return False
        return True

    @classmethod
    def from_dict(cls, data) -> AntwortThemaOption:
        return cls(
            thema_key=data["thema_key"],
            thema_name=data["thema_name"],
            option_key=data["option_key"],
        )


@dataclass(frozen=True)
class Antwort:
    """Ergebniscontainer für eine Frage.
    - Bei Fragen mit Themen: Liste (thema_key, option_key) je Thema.
    - Bei Fragen ohne Themen: genau ein Eintrag mit thema_key="".
    """

    frage_id: str
    auswahl: Tuple[AntwortThemaOption, ...]

    # TODO Refactoring!
    def filter_themen_nach_antwortoption(self, antwortoption_id: str) -> list[str]:
        # relevante Eltern-Themen (abhängig von geforderter Option)
        gefiltet: list[str] = []

        for a in self.auswahl:
            # Nur echte Themen berücksichtigen (nicht None aus „ohne Thema“)
            if a.hat_echtes_thema:

                # Nur wenn Thema richtig beantwortet wurde
                if a.option_key == antwortoption_id:
                    gefiltet.append(a.thema_key)

        return gefiltet

    @classmethod
    def from_dict(cls, data) -> Antwort:
        auswahl = data.get("auswahl", [])
        if isinstance(auswahl, dict):
            auswahl = [auswahl]

        auswahl = tuple(AntwortThemaOption.from_dict(item) for item in auswahl)

        return cls(
            frage_id=data["frage_id"],
            auswahl=auswahl,
        )


@dataclass(frozen=True)
class ThemenKontext:
    """Beschreibt das aktuell zu stellende Thema (ggf. verschachtelt).

    composite_key kodiert Eltern-/Kind-Bezug: "parentFrageId::parentThemaKey[::childThemaKey]".
    """

    composite_key: str
    parent_frage_id: Optional[str]
    parent_thema_key: Optional[str]
    parent_thema_text: Optional[str]
    child_thema_key: Optional[str]
    child_thema_text: Optional[str]
    # NEU: gerenderter Text pro Kontext
    text_gerendert: str


@dataclass(frozen=True)
class StrukturierteFrage:
    """Rückgabeobjekt für die nächste zu stellende Frage/Teilfrage."""

    frage_id: str
    themenkontexte: Tuple[ThemenKontext, ...]
    antwortoptionen: Tuple[Option, ...]
    rohe_frage: Frage


class SiliconSampleState(MessagesState):
    frage: StrukturierteFrage  # gesamte Frage (für Optionen etc.)
    kontext: ThemenKontext  # genau EIN Kontext (pro Graph-Run)
    kontextwechsel: bool  # Flag: Kontextwechsel erkannt?
    aktueller_kontext_key: Optional[str]  # bisher verarbeiteter Kontext-Key
    letzter_kontext_key: Optional[str]  # bisher verarbeiteter Kontext-Key
    zusammenfassungen: list[Zusammenfassung]
    antworten: dict[str, str]


@dataclass(frozen=True)
class SiliconSamples:
    zusammenfassungen: list[Zusammenfassung]
    fragen: dict[str, Frage]
    antworten: dict[str, Antwort]
    prompt: Prompt
    llm: Optional[LLM]

    @classmethod
    def from_dict(cls, data) -> SiliconSamples:
        zusammenfassungen = data.get("zusammenfassungen", [])
        if isinstance(zusammenfassungen, dict):
            zusammenfassungen = Zusammenfassung.from_dict(zusammenfassungen)

        fragen = data["fragen"]
        if isinstance(fragen, dict):
            fragen = {key: Frage.from_dict(value) for key, value in fragen.items()}

        antworten = data["antworten"]
        if isinstance(antworten, dict):
            antworten = {
                key: Antwort.from_dict(value) for key, value in antworten.items()
            }

        prompt = data.get("prompt", {})
        if isinstance(prompt, Prompt):
            prompt = Prompt.from_dict(prompt)

        llm = data.get("llm", {})
        if isinstance(llm, dict):
            llm = LLM.from_dict(llm)

        return cls(
            zusammenfassungen=zusammenfassungen,
            fragen=fragen,
            antworten=antworten,
            prompt=prompt,
            llm=llm,
        )
