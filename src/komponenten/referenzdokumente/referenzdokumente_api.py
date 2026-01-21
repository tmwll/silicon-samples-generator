from dataclasses import asdict
from pathlib import Path
import pandas as pd
from src.komponenten.referenzdokumente.referenzdokumente_models import Zusammenfassung
from src.shared.dateien import (
    datei_lesen,
    erstelle_dateipfad,
    dateipfad_relativ,
    ordner_auslesen,
)
from src.shared.generator import (
    LLMChatverlauf,
    LLMTokenverbrauch,
    format_number,
    parse_chatverlauf,
    tokenverbrauch_summieren,
)
from src.shared.komponenten import KomponentenAPI
import streamlit as st


class ReferenzdokumenteAPI(KomponentenAPI):

    def __init__(self):
        super().__init__("referenzdokumente")

        self.prompts_ordner = erstelle_dateipfad(
            ordnerpfad=self.config["speicherort"]["prompts"]["ordner"], dateiname=""
        )
        self.prompts_datei_text_mit_zahlen = self.config["speicherort"]["prompts"][
            "datei_text_mit_zahlen"
        ]
        self.prompts_datei_text_ohne_zahlen = self.config["speicherort"]["prompts"][
            "datei_text_ohne_zahlen"
        ]
        self.prompts_datei_tabellen_mit_zahlen = self.config["speicherort"]["prompts"][
            "datei_tabellen_mit_zahlen"
        ]
        self.prompts_datei_tabellen_ohne_zahlen = self.config["speicherort"]["prompts"][
            "datei_tabellen_ohne_zahlen"
        ]

        self.pdfs_ordner = erstelle_dateipfad(
            ordnerpfad=self.config["speicherort"]["pdfs"]["ordner"], dateiname=""
        )

        self.urls_datei = erstelle_dateipfad(
            ordnerpfad=self.config["speicherort"]["urls"]["datei"], dateiname=""
        )

        self.zusammenfassungen_ordner = erstelle_dateipfad(
            ordnerpfad=self.config["speicherort"]["zusammenfassungen"]["ordner"],
            dateiname="",
        )

    def zusammenfassung(self, dateipfad) -> list[Zusammenfassung]:
        return datei_lesen(dateipfad=dateipfad, json_datei=True, cls=Zusammenfassung)

    def tokenverbrauch_summieren(self, zusammenfassungen: list[Zusammenfassung]) -> int:
        anzahl_token = 0

        for zusammenfassung in zusammenfassungen:
            tokenverbrauch: dict[str, LLMTokenverbrauch] = (
                zusammenfassung.llm.tokenverbrauch
            )
            anzahl_token += tokenverbrauch_summieren(tokenverbrauch)

        return anzahl_token

    def streamlit_zusammenfassungen_auswahl(
        self, zusammenfassungen_ordner: Path, vorausgewaehlt: str = None
    ):
        zusammenfassungen: list[Zusammenfassung] = []

        zusammenfassungen_dateien = ordner_auslesen(zusammenfassungen_ordner, "*.json")

        if zusammenfassungen_dateien:

            zusammenfassungen_dateien = [
                self.text("zusammenfassungen_keine_auswahl")
            ] + zusammenfassungen_dateien

            index = None
            if vorausgewaehlt:
                dateiname = dateipfad_relativ(dateipfad_relativ(vorausgewaehlt).name)
                if dateiname in zusammenfassungen_dateien:
                    index = zusammenfassungen_dateien.index(dateiname)

            auswahl = st.selectbox(
                self.text("zusammenfassungen_auswahl_info"),
                zusammenfassungen_dateien,
                index=index,
                placeholder=self.text("zusammenfassungen_auswahl_waehlen"),
            )
            if auswahl and auswahl != self.text("zusammenfassungen_keine_auswahl"):
                zusammenfassungen = self.zusammenfassung(
                    erstelle_dateipfad(
                        ordnerpfad=zusammenfassungen_ordner,
                        dateiname=auswahl,
                        mit_basepath=False,
                    )
                )
        else:
            st.write(self.text("keine_zusammenfassungen_vorhanden"))
        return zusammenfassungen

    def streamlit_zusammenfassungen_anzeigen(
        self, zusammenfassungen: list[Zusammenfassung] = [], zeige_tokens=True
    ):
        if zeige_tokens:
            st.metric(
                self.text("verbrauchte_tokens_insgesamt"),
                format_number(
                    self.tokenverbrauch_summieren(zusammenfassungen=zusammenfassungen)
                ),
                border=True,
                width="content",
            )

        for zusammenfassung in zusammenfassungen:
            with st.expander(
                f"{self.text("zusammenfassung")} {zusammenfassung.referenzdokument.name}{self.text("verbrauchte_tokens")}{format_number(tokenverbrauch_summieren(zusammenfassung.llm.tokenverbrauch))}"
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.write(self.text("referenzdokument"))
                    df = pd.DataFrame.from_dict(
                        asdict(zusammenfassung.referenzdokument),
                        orient="index",
                        columns=[self.text("wert")],
                    )
                    df.index.name = self.text("attribut")
                    df = df.astype({df.columns[0]: "string"})
                    st.dataframe(data=df, width="content")

                with col2:
                    st.write(self.text("ausgewaehlte_zusammenfassung"))
                    df = pd.DataFrame.from_dict(
                        asdict(zusammenfassung.zusammenfassung_auswahl),
                        orient="index",
                        columns=[self.text("wert")],
                    )
                    df.index.name = self.text("attribut")
                    st.dataframe(data=df, width="content")

                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
                    [
                        self.text("text_extrahiert"),
                        self.text("text_zusammengefasst"),
                        self.text("tabellen_extrahiert"),
                        self.text("tabellen_zusammengefasst"),
                        self.text("chatverlauf_text"),
                        self.text("chatverlauf_tabellen"),
                    ]
                )

                with tab1:
                    text_extrahiert = zusammenfassung.text_extrahiert.strip()
                    if not text_extrahiert:
                        text_extrahiert = self.text("keine_daten_extrahiert")
                    st.markdown(body=text_extrahiert)

                with tab2:
                    text_zusammengefasst = zusammenfassung.text_zusammengefasst.strip()
                    if not text_zusammengefasst:
                        text_zusammengefasst = self.text("keine_daten_extrahiert")
                    st.markdown(body=text_zusammengefasst)

                with tab3:
                    if not zusammenfassung.tabellen_extrahiert:
                        st.markdown(self.text("keine_daten_extrahiert"))
                    else:
                        for tabelle_extrahiert in zusammenfassung.tabellen_extrahiert:
                            st.markdown(tabelle_extrahiert)

                with tab4:
                    if not zusammenfassung.tabellen_zusammengefasst:
                        st.markdown(self.text("keine_daten_extrahiert"))
                    else:
                        for (
                            tabelle_zusammengefasst
                        ) in zusammenfassung.tabellen_zusammengefasst:
                            st.markdown(tabelle_zusammengefasst)

                with tab5:
                    chatverlaeufe_text = [
                        cv
                        for cv in zusammenfassung.llm.chatverlaeufe
                        if cv.name == "text_zusammengefasst"
                    ]
                    if not chatverlaeufe_text:
                        st.markdown(self.text("keine_daten_extrahiert"))
                    else:
                        self.print_chatverlaeufe(chatverlaeufe=chatverlaeufe_text)

                with tab6:
                    chatverlaeufe_tabellen = [
                        cv
                        for cv in zusammenfassung.llm.chatverlaeufe
                        if cv.name == "tabellen_zusammengefasst"
                    ]
                    if not chatverlaeufe_tabellen:
                        st.markdown(self.text("keine_daten_extrahiert"))
                    else:
                        self.print_chatverlaeufe(chatverlaeufe=chatverlaeufe_tabellen)

    def print_chatverlaeufe(self, chatverlaeufe: list[LLMChatverlauf]):
        for i, chatverlauf in enumerate(chatverlaeufe, start=1):
            if len(chatverlaeufe) > 1:
                with st.expander(label=f"{self.text("chatverlauf")} {i}"):
                    self.print_chatverlauf(chatverlauf=chatverlauf)
            else:
                self.print_chatverlauf(chatverlauf=chatverlauf)

    def print_chatverlauf(self, chatverlauf: LLMChatverlauf):
        parsed_chatverlauf = parse_chatverlauf(chatverlauf=chatverlauf.chatverlauf)
        for message in parsed_chatverlauf:
            message_short = message["content"].strip()
            if message["type"] in ("human", "user"):
                message_short = (
                    message_short
                    if len(message_short) <= 300
                    else message_short[:300] + self.text("text_verkuerzt")
                )
            message_type = message["type"].replace("system", "user")
            with st.chat_message(message_type):
                st.markdown(message_short)
