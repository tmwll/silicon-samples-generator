from typing import Any
import pandas as pd
from src.komponenten.siliconsamplesgenerator.siliconsamplesgenerator_models import (
    Antwort,
    SiliconSamples,
)
from src.shared.dateien import (
    datei_lesen,
    erstelle_dateipfad,
    dateipfad_relativ,
    ordner_auslesen,
)
from src.shared.generator import (
    format_number,
    parse_chatverlauf,
    tokenverbrauch_summieren,
)
from src.shared.komponenten import KomponentenAPI
import streamlit as st

from src.shared.logger import get_logger

log = get_logger(__name__)


class SiliconSamplesGeneratorAPI(KomponentenAPI):

    def __init__(self):
        super().__init__("siliconsamplesgenerator")

        self.prompts_ordner = erstelle_dateipfad(
            ordnerpfad=self.config["speicherort"]["prompts"]["ordner"], dateiname=""
        )
        self.prompts_datei_intro_ohne_persona_mit_referenzdokumenten: str = self.config[
            "speicherort"
        ]["prompts"]["datei_intro_ohne_persona_mit_referenzdokumenten"]
        self.prompts_datei_intro_ohne_persona_ohne_referenzdokumente: str = self.config[
            "speicherort"
        ]["prompts"]["datei_intro_ohne_persona_ohne_referenzdokumente"]
        self.prompts_datei_intro_mit_persona_mit_referenzdokumenten: str = self.config[
            "speicherort"
        ]["prompts"]["datei_intro_mit_persona_mit_referenzdokumenten"]
        self.prompts_datei_intro_mit_persona_ohne_referenzdokumente: str = self.config[
            "speicherort"
        ]["prompts"]["datei_intro_mit_persona_ohne_referenzdokumente"]

        self.personas_datei = erstelle_dateipfad(
            ordnerpfad=self.config["speicherort"]["personas"]["datei"], dateiname=""
        )

        self.siliconsamples_ordner = erstelle_dateipfad(
            ordnerpfad=self.config["speicherort"]["siliconsamples"]["ordner"],
            dateiname="",
        )

    def siliconsamples(self, dateipfad) -> SiliconSamples:
        return datei_lesen(dateipfad=dateipfad, json_datei=True, cls=SiliconSamples)

    def streamlit_siliconsamples_auswahl(
        self, siliconsamples_ordner, vorausgewaehlt: str = None
    ):
        siliconsamples: SiliconSamples = None

        siliconsamples_dateien = ordner_auslesen(siliconsamples_ordner, "*.json")

        if siliconsamples_dateien:

            siliconsamples_dateien = [
                self.text("siliconsamples_keine_auswahl")
            ] + siliconsamples_dateien

            index = None
            if vorausgewaehlt:
                dateiname = dateipfad_relativ(vorausgewaehlt).name
                if dateiname in siliconsamples_dateien:
                    index = siliconsamples_dateien.index(dateiname)

            auswahl = st.selectbox(
                self.text("siliconsamples_auswahl_info"),
                siliconsamples_dateien,
                index=index,
                placeholder=self.text("siliconsamples_auswahl_waehlen"),
            )

            if auswahl and auswahl != self.text("siliconsamples_keine_auswahl"):
                siliconsamples = self.siliconsamples(
                    erstelle_dateipfad(
                        ordnerpfad=siliconsamples_ordner,
                        dateiname=auswahl,
                        mit_basepath=False,
                    )
                )
        else:
            st.write(self.text("keine_siliconsamples_vorhanden"))
        return siliconsamples

    def streamlit_siliconsamples_anzeigen(self, siliconsamples: SiliconSamples):

        col1, col2, col3 = st.columns(3)

        col1.metric(
            self.text("verbrauchte_tokens"),
            format_number(tokenverbrauch_summieren(siliconsamples.llm.tokenverbrauch)),
            border=True,
            width="content",
        )

        prompt_data = siliconsamples.prompt.get("prompt_data", {})
        persona_nutzen = prompt_data.get("personas_nutzen", False)
        col2.metric(self.text("persona"), persona_nutzen, border=True, width="content")

        if persona_nutzen:
            persona = prompt_data.get("aktuelle_persona", {})


        tab1, tab2 = st.tabs(
            [
                self.text("antworten"),
                self.text("rohdaten")
            ]
        )

        with tab1:

            st.subheader(self.text("antworten"))
            self.streamlit_siliconsamples_dataframe(siliconsamples=siliconsamples)

        with tab2:

            st.subheader(self.text("rohdaten"))
            with st.expander(self.text("fragen")):
                st.write(siliconsamples.fragen)

            with st.expander(self.text("zusammenfassungen")):
                st.write(siliconsamples.zusammenfassungen)

            with st.expander(self.text("chatverlauf")):
                for chatverlauf in siliconsamples.llm.chatverlaeufe:
                    with st.expander(label=f"{chatverlauf.name}"):

                        if all(isinstance(x, list) for x in chatverlauf.chatverlauf):
                            for idx, chatverlauf_tabelle in enumerate(
                                chatverlauf.chatverlauf, start=1
                            ):
                                with st.expander(label=f"Chatverlauf für Tabelle {idx}"):
                                    parsed_chatverlauf = parse_chatverlauf(
                                        chatverlauf=chatverlauf_tabelle
                                    )
                                    self.print_parsed_chatverlauf(
                                        chatverlauf=parsed_chatverlauf
                                    )

                        else:
                            parsed_chatverlauf = parse_chatverlauf(
                                chatverlauf=chatverlauf.chatverlauf
                            )
                            self.print_parsed_chatverlauf(chatverlauf=parsed_chatverlauf)

            with st.expander(self.text("antworten")):
                st.write(siliconsamples.antworten)

            if persona_nutzen:
                with st.expander(self.text("persona_details")):
                    st.write(persona)

    def print_parsed_chatverlauf(self, chatverlauf: list[dict[str, str]]):
        for message in chatverlauf:

            with st.chat_message(message["type"].replace("system", "user")):
                st.markdown(message["content"])

    def streamlit_siliconsamples_dataframe(self, siliconsamples: SiliconSamples):

        # pivot[row][col] = value
        pivot: dict[str, dict[str, str]] = {}

        row = 0
        for frage_id, antwort in siliconsamples.antworten.items():
            for item in antwort.auswahl:
                thema_key = item.thema_key
                thema_name = item.thema_name
                antwortoption = item.option_key

                mutter_frage_id = ""
                mutter_thema_id = ""
                kind_thema_id = ""

                parts = thema_key.split("::")
                if len(parts) > 1:
                    mutter_frage_id = parts[0]
                    if len(parts) > 2:
                        mutter_thema_id = parts[1]
                        kind_thema_id = parts[2]
                    else:
                        kind_thema_id = parts[1]
                else:
                    kind_thema_id = thema_key

                frage = siliconsamples.fragen.get(frage_id)
                frage_text = frage.text
                kind_thema_text = frage.thema_text(kind_thema_id) or ""
                antwortoption_text = frage.option_text(antwortoption) or ""

                pivot[row] = {
                    "Frage-ID": frage_id,
                    "Frage-Text": frage_text,
                    "Mutter-Frage": mutter_frage_id,
                    "Mutter-Thema": mutter_thema_id,
                    "Thema-ID": kind_thema_id,
                    "Thema-Text": kind_thema_text,
                    "Antwortoption-ID": antwortoption,
                    "Antwortoption-Text": antwortoption_text,
                }
                row += 1

        df = pd.DataFrame.from_dict(pivot, orient="index")
        # df.index.name = "Marke"

        # df_numeric = df.apply(pd.to_numeric, errors="coerce")

        st.dataframe(df, hide_index=True)

        # columns, pivot = self.antworten_als_pivot(siliconsamples.antworten)

        # df = pd.DataFrame.from_dict(pivot, orient="index")
        # df = df.reindex(columns=columns)

        # df.index.name = "Marke"

        # df_numeric = df.apply(pd.to_numeric, errors="coerce")

        # df["Summe"] = df_numeric.sum(axis=1)

        # st.dataframe(df)

    def antworten_als_pivot(
        self, antworten: dict[str, Antwort]
    ) -> tuple[list[str], dict[str, dict[str, str]]]:
        """
        Rückgabe:
        - columns: sortierte Spaltennamen (ohne "Marke")
        - pivot: dict[row_id][col] = value
        """
        # pivot[row][col] = value
        pivot: dict[str, dict[str, str]] = {}
        columns = set()

        for _, antwort in antworten.items():
            # frage_id = antwort.frage_id  # aktuell nicht genutzt
            for item in antwort.auswahl:
                thema_key = item.thema_key
                thema_name = item.thema_name
                antwortoption = item.option_key

                # Thema-Key aufsplitten, letztes Element ist der Key des eigentlichen Themas
                parts = thema_key.split("::")
                if len(parts) > 1:
                    col = parts[-1]
                    row_id = thema_name or ""

                    if row_id not in pivot:
                        pivot[row_id] = {}
                    pivot[row_id][col] = antwortoption
                    columns.add(col)

        # Jede Row: [row_id, value_col1, value_col2, ...]
        rows: list[list[str]] = []
        for row_id in sorted(pivot.keys(), key=str):
            row_vals = [pivot[row_id].get(col, "") for col in columns]
            rows.append([row_id] + row_vals)

        return columns, pivot

    def hole_persona_fuer_wiederholung(
        self, personas: list[dict[str, Any]], wiederholung: int
    ):
        persona: dict[str, Any] = None
        if personas:
            persona_index = wiederholung % len(personas)
            persona = personas[persona_index]
        return persona
