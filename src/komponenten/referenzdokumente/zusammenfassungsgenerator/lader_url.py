import logging

from bs4 import BeautifulSoup
import lxml
import html5lib
import pandas as pd
import requests


class URLLader:

    def extrahiere_text(self, url: str) -> str:
        html = ""
        try:
            r = requests.get(url, headers={"User-Agent": "Weblader"}, timeout=20)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            logging.warning(f"Web-Fetch fehlgeschlagen: {url} ({e})")

        soup = BeautifulSoup(html, "lxml")

        texte = []
        for tag in soup.find_all(["p", "li"]):
            s = tag.get_text(separator=" ", strip=True)
            if s and len(s.split()) >= 5:
                texte.append(s)
        text = "\n".join(texte)

        return text

    def extrahiere_tabellen(self, url: str, zeilen) -> list[str]:
        tabellen: list[str] = []
        try:
            dfs = pd.read_html(url, header=None)  # erste Zeile = Header

            for df in dfs:
                if zeilen is None:
                    df_out = df
                elif zeilen >= 0:
                    df_out = df.head(zeilen)
                else:
                    df_out = df.tail(abs(zeilen))  # negative Zahl -> letzte N Zeilen

                tabellen.append(df_out.to_markdown(index=False))
        except ValueError as e:
            logging.warning("Keine Tabellen gefunden")

        return tabellen
