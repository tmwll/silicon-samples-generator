import logging

import pandas as pd
import requests


class CSVLader:

    def extrahiere_text(self, pfad: str) -> str:
        text = ""

        return text

    def extrahiere_tabellen(self, pfad: str, zeilen) -> list[str]:
        tabellen: list[str] = []
        try:

            df = pd.read_csv(pfad, sep=";", header=None)
            tabellen.append(df.to_markdown())

        except ValueError as e:
            logging.warning("Keine Tabellen gefunden")

        return tabellen
