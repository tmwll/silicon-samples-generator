# parsing.py
from __future__ import annotations
import random
from typing import List, Optional
from pathlib import Path

from src.shared.logger import get_logger

log = get_logger(__name__)

try:
    # Für untrusted XML empfohlen (optional dependency)
    import defusedxml.ElementTree as ET  # type: ignore
except Exception:  # defusedxml nicht vorhanden → sicherer Fallback
    import xml.etree.ElementTree as ET  # type: ignore

from .models import Frage, Option, Thema
from .utils import stripped_oder_none
from .fragenparserfehler import FragenParserFehler


class Studienkonfigurationslader:
    def __init__(self, pathlike):
        self.pfad = pathlike
        self._fragen: List[Frage] = []

        xml_pfad = Path(pathlike)
        if not xml_pfad.exists():
            raise FragenParserFehler(f"XML-Datei nicht gefunden: {xml_pfad}")

        try:
            xml_baum = ET.parse(xml_pfad)
        except ET.ParseError as e:
            raise FragenParserFehler(f"XML fehlerhaft ({xml_baum}): {e}") from e

        self.xml_baum = xml_baum

        self.lade_fragen()

    @property
    def fragen(self):  # Getter
        return self._fragen

    def xml_datei(self):
        return ET.tostring(self.xml_baum.getroot(), encoding="utf8").decode("utf8")

    def lade_fragen(self):
        """
        Lies eine XML-Datei ein und parse sie zu Domain-Objekten.

        Erwartete XML-Struktur (verkürzt):
        <Fragen>
        <Frage id="...?" uebergeordnete_frage="...?" uebergeordnete_antwortoption="...?">
            <Text>...</Text>
            <Antwortoptionen>
            <Option id="k1">Text</Option>
            ...
            </Antwortoptionen>
            <Themen>
            <Thema id="t1">Text</Thema>
            ...
            </Themen>
        </Frage>
        ...
        </Fragen>
        """

        xml_wurzel = self.xml_baum.getroot()

        for xml_frage in xml_wurzel.findall("Frage"):
            frage = self._parse_frage(xml_frage)
            self._fragen.append(frage)

    def _parse_frage(self, frage: ET.Element) -> Frage:
        frage_id = stripped_oder_none(frage.get("id"))

        log.info(f"Frage {frage_id} verarbeiten")

        if not frage_id:
            raise FragenParserFehler("<Frage> ohne gültiges id-Attribut")

        if frage_id in self._fragen:
            raise FragenParserFehler(
                f"Doppelte Frage-ID beim Laden der Fragen aus XML-Datei: '{frage_id}'"
            )

        uebergeordnete_frage = stripped_oder_none(frage.get("uebergeordnete_frage"))
        uebergeordnete_antwortoption = stripped_oder_none(
            frage.get("uebergeordnete_antwortoption")
        )

        # --- NEU: Limit + Shuffle für Folgefragen ---
        uebergeordnete_themen_limit_element = stripped_oder_none(
            frage.get("uebergeordnete_themen_limit")
        )
        uebergeordnete_themen_limit = None
        if uebergeordnete_themen_limit_element is not None:
            try:
                uebergeordnete_themen_limit = int(uebergeordnete_themen_limit_element)
            except ValueError as e:
                raise FragenParserFehler(
                    f"Frage '{frage_id}': uebergeordnete_themen_limit ist keine Zahl: '{uebergeordnete_themen_limit_element}'"
                ) from e
            if uebergeordnete_themen_limit < 1:
                raise FragenParserFehler(
                    f"Frage '{frage_id}': uebergeordnete_themen_limit muss >= 1 sein"
                )

        uebergeordnete_themen_zufaellig = False
        uebergeordnete_themen_zufaellig_element = stripped_oder_none(
            frage.get("uebergeordnete_themen_zufaellig")
        )
        if uebergeordnete_themen_zufaellig_element is not None:
            v = uebergeordnete_themen_zufaellig_element.strip().lower()
            if v in ("true", "1", "yes", "ja"):
                uebergeordnete_themen_zufaellig = True
            elif v in ("false", "0", "no", "nein"):
                uebergeordnete_themen_zufaellig = False
            else:
                raise FragenParserFehler(
                    f"Frage '{frage_id}': uebergeordnete_themen_zufaellig muss true/false, 1/0, yes/no, ja/nein sein, Ergebnis: '{uebergeordnete_themen_zufaellig_element}'"
                )

        log.info(
            f"Frage '{frage_id}' mit uebergeordnete_themen_zufaellig = {uebergeordnete_themen_zufaellig}, uebergeordnete_themen_limit = {uebergeordnete_themen_limit}"
        )

        # Syntax-Fehler
        if (
            uebergeordnete_themen_limit is not None or uebergeordnete_themen_zufaellig
        ) and not uebergeordnete_frage:
            raise FragenParserFehler(
                f"Frage '{frage_id}': uebergeordnete_themen_* gesetzt, aber uebergeordnete_frage fehlt"
            )

        # Text
        text_element = frage.find("Text")
        if text_element is None:
            raise FragenParserFehler(f"<Text> fehlt in Frage '{frage_id}'")
        text = stripped_oder_none("".join(text_element.itertext()))
        if not text:
            raise FragenParserFehler(f"<Text> leer in Frage '{frage_id}'")

        # Antwortoptionen
        antwortoptionen_element = frage.find("Antwortoptionen")
        if antwortoptionen_element is None:
            raise FragenParserFehler(f"<Antwortoptionen> fehlt in Frage '{frage_id}'")

        antwortoptionen: List[Option] = []
        for antwortoption_element in antwortoptionen_element.findall("Option"):

            antwortoption_id = stripped_oder_none(antwortoption_element.get("id"))
            antwortoption_text = stripped_oder_none(
                "".join(antwortoption_element.itertext())
            )

            if not antwortoption_id or not antwortoption_text:
                raise FragenParserFehler(
                    f"Frage '{frage_id}': Antwortoptionen: Fehlender 'id' oder leerer Text"
                )

            if any(
                antwortoption.id == antwortoption_id
                for antwortoption in antwortoptionen
            ):
                raise FragenParserFehler(
                    f"Frage '{frage_id}': Antwortoptionen: Doppelter 'id' {antwortoption_id}"
                )

            antwortoptionen.append(Option(id=antwortoption_id, text=antwortoption_text))

        if not antwortoptionen:
            raise FragenParserFehler(
                f"Frage '{frage_id}': Keine <Option> innerhalb <Antwortoptionen>"
            )

        # Themen
        themen: List[Thema] = []
        themen_element = frage.find("Themen")
        if themen_element is not None:
            for thema_element in themen_element.findall("Thema"):

                thema_id = stripped_oder_none(thema_element.get("id"))
                thema_text = stripped_oder_none("".join(thema_element.itertext()))

                if not thema_id or not thema_text:
                    raise FragenParserFehler(
                        f"Frage '{frage_id}': Thema: Fehlender 'id' oder leerer Text"
                    )

                if any(thema.id == thema_id for thema in themen):
                    raise FragenParserFehler(
                        f"Frage '{frage_id}': Thema: Doppelter 'id' {thema_id}"
                    )

                # Optionen erstmal leer, entscheiden wir später beim Laden, wo es hinkommt
                themen.append(Thema(id=thema_id, text=thema_text))

        # # Themen shuffeln
        # themen_zufaellig = self._bool_attr(themen_element.get("zufaellig"))
        # if themen_zufaellig:
        #     random.shuffle(themen)
        #     log.info(f"Themen shuffeln, Ergebnis = {themen_zufaellig}")

        return Frage(
            id=frage_id,
            text=text,
            optionen=antwortoptionen,
            themen=themen,
            uebergeordnete_frage_id=uebergeordnete_frage,
            uebergeordnete_antwortoption_id=uebergeordnete_antwortoption,
            uebergeordnete_themen_limit=uebergeordnete_themen_limit,
            uebergeordnete_themen_zufaellig=uebergeordnete_themen_zufaellig,
        )

    @staticmethod
    def _bool_attr(value: Optional[str]) -> bool:
        if value is None:
            return False
        v = value.strip().lower()
        if v in {"1", "true", "ja", "yes", "y", "t"}:
            return True
        if v in {"0", "false", "nein", "no", "n", "f"}:
            return False
        raise FragenParserFehler(
            f"Ungültiger Wert für Attribut 'zufaellig': '{value}' (erwartet true/false)"
        )
