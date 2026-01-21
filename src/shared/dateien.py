import json
import os
from pathlib import Path
import platform
import streamlit as st

from src.shared.logger import get_logger

log = get_logger(__name__)


def erstelle_dateipfad(ordnerpfad, dateiname, mit_basepath=True) -> Path:
    if mit_basepath:
        basepath = st.session_state["config"]["dotenv"]["BASEPATH_FILES"]
        basepath = os.path.join(basepath, "")
        ordnerpfad = basepath + ordnerpfad
    return Path(ordnerpfad) / dateiname


def dateipfad_relativ(dateipfad, als_string=False):
    if isinstance(dateipfad, str):
        dateipfad = Path(dateipfad)
    return _dateipfad(
        dateipfad,
        als_string,
    )


def dateipfad_absolut(dateipfad, als_string=False):
    if isinstance(dateipfad, str):
        dateipfad = Path(dateipfad)
    return _dateipfad(dateipfad.absolute, als_string)


def _dateipfad(dateipfad: Path, als_string):
    if als_string:
        dateipfad = str(dateipfad)
    return dateipfad


def datei_lesen(dateipfad: Path, json_datei=False, cls=None) -> str:
    if not dateipfad.is_file():
        raise FileNotFoundError(f"Datei nicht gefunden: {dateipfad.resolve()}")

    with open(dateipfad, "r", encoding="utf-8") as f:

        if json_datei:
            daten = json.load(f)

            # Fall 1: Datei enthält EIN Objekt { ... }
            if isinstance(daten, dict):
                daten = cls.from_dict(daten)

            # Fall 2: Datei enthält eine Liste von Objekten [ { ... }, { ... } ]
            elif isinstance(daten, list):
                daten = [cls.from_dict(item) for item in daten]

            # Irgendwas anderes -> Fehler
            # raise TypeError(f"Unerwarteter JSON-Typ: {type(daten)!r}")

        else:
            daten = f.read()

    return daten


def datei_speichern(dateipfad: Path, items: list) -> None:
    dateipfad.parent.mkdir(parents=True, exist_ok=True)
    with open(dateipfad, "w", encoding="utf-8") as f:
        json.dump(items, f, default=lambda o: o.__dict__, ensure_ascii=False, indent=4)


def datei_erstellungsdatum(dateipfad):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == "Windows":
        return os.path.getctime(dateipfad)
    else:
        stat = os.stat(dateipfad)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


def ordner_auslesen(ordnerpfad: Path, dateitypen: str):
    dateien: list[Path] = []
    for datei in ordnerpfad.rglob(dateitypen):
        dateien.append(datei.relative_to(ordnerpfad))
    return dateien
