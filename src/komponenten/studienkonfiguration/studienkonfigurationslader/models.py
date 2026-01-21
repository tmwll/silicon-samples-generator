# models.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple

from .utils import stripped_oder_none

from src.shared.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Option:
    id: str
    text: str

    @classmethod
    def from_dict(cls, data) -> Option:
        return cls(
            id=data["id"],
            text=data["text"],
        )


@dataclass(frozen=True)
class Thema:
    id: str
    text: str

    @classmethod
    def from_dict(cls, data) -> Thema:
        return cls(
            id=data["id"],
            text=data["text"],
        )


@dataclass(frozen=True)
class Frage:
    id: str
    text: str
    optionen: List[Option]
    themen: List[Thema]
    uebergeordnete_frage_id: Optional[str] = None  # id der Mutterfrage
    uebergeordnete_antwortoption_id: Optional[str] = (
        None  # if der notwendigen Antwortoption der Mutterfrage
    )
    uebergeordnete_themen_limit: Optional[int] = None
    uebergeordnete_themen_zufaellig: bool = False

    @property
    def hat_uebergeordnete_frage(self) -> bool:
        if stripped_oder_none(self.uebergeordnete_frage_id):
            return True
        else:
            return False

    @property
    def hat_uebergeordnete_antwortoption(self) -> bool:
        if stripped_oder_none(self.uebergeordnete_antwortoption_id):
            return True
        else:
            return False

    def optionen_fuer(self, thema_key: str | None) -> List[Option]:
        if thema_key:
            for thema in self.themen:
                if thema.id == thema_key and thema.optionen:
                    return thema.optionen
        return self.optionen

    def thema_text(self, thema_key: str) -> str | None:
        for thema in self.themen:
            if thema.id == thema_key:
                return thema.text
        return None

    def option_text(self, option_key: str) -> str | None:
        for option in self.optionen:
            if option.id == option_key:
                return option.text
        return None

    @classmethod
    def from_dict(cls, data: dict) -> "Frage":
        optionen_data = data.get("optionen", [])
        if isinstance(optionen_data, dict):
            optionen_data = [optionen_data]

        themen_data = data.get("themen", [])
        if isinstance(themen_data, dict):
            themen_data = [themen_data]

        optionen = [Option.from_dict(o) for o in optionen_data]
        themen = [Thema.from_dict(t) for t in themen_data]

        return cls(
            id=data["id"],
            text=data["text"],
            optionen=optionen,
            themen=themen,
            uebergeordnete_frage_id=data.get("uebergeordnete_frage_id"),
            uebergeordnete_antwortoption_id=data.get("uebergeordnete_antwortoption_id"),
            uebergeordnete_themen_limit=data.get("uebergeordnete_themen_limit"),
            uebergeordnete_themen_zufaellig=bool(
                data.get("uebergeordnete_themen_zufaellig", False)
            ),
        )
