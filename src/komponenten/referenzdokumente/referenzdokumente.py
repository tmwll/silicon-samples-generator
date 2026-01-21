from typing import Any
import pandas as pd
import streamlit as st

from datetime import datetime

from src.komponenten.referenzdokumente.referenzdokumente_models import (
    ReferenzdokumentAuswahl,
    ZusammenfassungAuswahl,
    Referenzdokument,
    Zusammenfassung,
)
from src.komponenten.referenzdokumente.referenzdokumente_api import ReferenzdokumenteAPI
from src.komponenten.referenzdokumente.zusammenfassungsgenerator.zusammenfassungsgenerator import (
    Zusammenfassungsgenerator,
)
from src.shared.dateien import (
    datei_erstellungsdatum,
    datei_lesen,
    datei_speichern,
    erstelle_dateipfad,
    dateipfad_relativ,
    ordner_auslesen,
)
from src.shared.generator import Prompt
from src.shared.llm_integrations.llm_provider import LLMProvider

api = ReferenzdokumenteAPI()
config = api.config

##########
###
### Session Bereich Start
###
##########


session_key = api.komponenten_name

if f"{session_key}.gestartet" not in st.session_state:
    st.session_state[f"{session_key}.gestartet"] = False

if f"{session_key}.fertig" not in st.session_state:
    st.session_state[f"{session_key}.fertig"] = False

if f"{session_key}.ergebnis" not in st.session_state:
    st.session_state[f"{session_key}.ergebnis"] = None


# Button Start
def starten():
    st.session_state[f"{session_key}.gestartet"] = True
    st.session_state[f"{session_key}.fertig"] = False
    # Dann weiter mit rerun vom Button --> "if gestartet:" greift


# Button Abbruch
def abbrechen():
    to_delete = [k for k in st.session_state.keys() if k.startswith(session_key + ".")]
    for k in to_delete:
        del st.session_state[k]
    # Dann weiter mit Rerun vom Button


# Trigger, wenn Routine fertig
def fertig(ergebnis: Any):
    st.session_state[f"{session_key}.gestartet"] = False
    st.session_state[f"{session_key}.fertig"] = True
    st.session_state[f"{session_key}.ergebnis"] = ergebnis
    # Dann weiter mit manuellem Rerun
    st.rerun()


# Resetten ohne Rerun/Abbrechnen
def reset():
    st.session_state[f"{session_key}.gestartet"] = False
    st.session_state[f"{session_key}.fertig"] = False
    # st.session_state[f"{session_key}.ergebnis"] = None


# Status für Ergebnisanzeige
prozess_gestartet = st.session_state[f"{session_key}.gestartet"]
prozess_fertig = st.session_state[f"{session_key}.fertig"]


##########
###
### Session Bereich Ende
###
##########

# Anwendungstitel
st.title(config["page"]["title"])

with st.sidebar:

    prompts_ordner = st.text_input(
        api.text("prompts_ordner_name"),
        help=api.text("prompts_ordner_beschreibung"),
        value=api.prompts_ordner,
    )

    # Prompt: Text mit Zahlen
    prompt_datei_text_mit_zahlen = erstelle_dateipfad(
        ordnerpfad=prompts_ordner,
        dateiname=api.prompts_datei_text_mit_zahlen,
        mit_basepath=False,
    )
    prompt_text_mit_zahlen = datei_lesen(prompt_datei_text_mit_zahlen)

    # Prompt: Text ohne Zahlen
    prompt_datei_text_ohne_zahlen = erstelle_dateipfad(
        ordnerpfad=prompts_ordner,
        dateiname=api.prompts_datei_text_ohne_zahlen,
        mit_basepath=False,
    )
    prompt_text_ohne_zahlen = datei_lesen(prompt_datei_text_ohne_zahlen)

    # Prompt: Tabellen mit Zahlen
    prompt_datei_tabellen_mit_zahlen = erstelle_dateipfad(
        ordnerpfad=prompts_ordner,
        dateiname=api.prompts_datei_tabellen_mit_zahlen,
        mit_basepath=False,
    )
    prompt_tabellen_mit_zahlen = datei_lesen(prompt_datei_tabellen_mit_zahlen)

    # Prompt: Tabellen ohne Zahlen
    prompt_datei_tabellen_zusammenfassen_ohne_zahlen = erstelle_dateipfad(
        ordnerpfad=prompts_ordner,
        dateiname=api.prompts_datei_tabellen_ohne_zahlen,
        mit_basepath=False,
    )
    prompt_tabellen_ohne_zahlen = datei_lesen(
        prompt_datei_tabellen_zusammenfassen_ohne_zahlen
    )

    referenzdokumente_pdfs_ordner = dateipfad_relativ(
        st.text_input(
            api.text("referenzdokumente_pdfs_ordner_name"),
            help=api.text("referenzdokumente_pdfs_ordner_beschreibung"),
            value=api.pdfs_ordner,
        )
    )

    referenzdokumente_urls_datei = dateipfad_relativ(
        dateipfad=st.text_input(
            api.text("referenzdokumente_urls_datei_name"),
            help=api.text("referenzdokumente_urls_datei_beschreibung"),
            value=api.urls_datei,
        )
    )

    zusammenfassungen_ordner = dateipfad_relativ(
        st.text_input(
            api.text("zusammenfassungen_ordner_name"),
            help=api.text("zusammenfassungen_ordner_beschreibung"),
            value=api.zusammenfassungen_ordner,
        )
    )

# Ergebnisse zeigen
if prozess_fertig:
    # Bisschen Spaß muss sein
    st.balloons()

    # Nachricht anzeigen
    st.success(api.text("erfolgsmeldung"))

    # Reset ohne Rerun
    reset()

tab1, tab2, tab3 = st.tabs(
    [
        api.text("tab_generieren_titel"),
        api.text("tab_anzeigen_titel"),
        api.text("tab_prompts_titel"),
    ]
)

with tab1:

    zeilen: list = []

    referenzdokumente_dateien = ordner_auslesen(referenzdokumente_pdfs_ordner, "*.pdf")
    for datei in referenzdokumente_dateien:
        zeilen.append(
            {
                "art": api.text("tabelle_art_pdf"),
                "name": datei,
                "erstellungsdatum": datetime.fromtimestamp(
                    datei_erstellungsdatum(
                        erstelle_dateipfad(
                            ordnerpfad=referenzdokumente_pdfs_ordner,
                            dateiname=datei,
                            mit_basepath=False,
                        )
                    )
                ),
                "text_verarbeiten": api.text("tabelle_text_verarbeiten_option_1"),
                "tabellen_verarbeiten": api.text(
                    "tabelle_tabellen_verarbeiten_option_1"
                ),
            }
        )

    referenzdokumente_dateien = ordner_auslesen(referenzdokumente_pdfs_ordner, "*.csv")
    for datei in referenzdokumente_dateien:
        zeilen.append(
            {
                "art": "CSV",
                "name": datei,
                "erstellungsdatum": datetime.fromtimestamp(
                    datei_erstellungsdatum(
                        erstelle_dateipfad(
                            ordnerpfad=referenzdokumente_pdfs_ordner,
                            dateiname=datei,
                            mit_basepath=False,
                        )
                    )
                ),
                "text_verarbeiten": api.text("tabelle_text_verarbeiten_option_1"),
                "tabellen_verarbeiten": api.text(
                    "tabelle_tabellen_verarbeiten_option_1"
                ),
            }
        )

    df = pd.read_csv(referenzdokumente_urls_datei, sep=";")  # bei Komma: sep=","
    for url in df["URL"].dropna():
        zeilen.append(
            {
                "art": api.text("tabelle_art_url"),
                "name": url,
                "erstellungsdatum": "N/A",
                "text_verarbeiten": api.text("tabelle_text_verarbeiten_option_1"),
                "tabellen_verarbeiten": api.text(
                    "tabelle_tabellen_verarbeiten_option_1"
                ),
            }
        )

    df = pd.DataFrame(zeilen)

    edited_df = st.data_editor(
        df,
        column_config={
            "art": api.text("tabelle_art_title"),
            "name": api.text("tabelle_name_title"),
            "erstellungsdatum": st.column_config.DatetimeColumn(
                label=api.text("tabelle_erstellungsdatum_title"),
                format=api.text("tabelle_erstellungsdatum_format"),
                step=60,
            ),
            "text_verarbeiten": st.column_config.SelectboxColumn(
                api.text("tabelle_text_verarbeiten_title"),
                width="medium",
                options=[
                    api.text("tabelle_text_verarbeiten_option_1"),
                    api.text("tabelle_text_verarbeiten_option_2"),
                    api.text("tabelle_text_verarbeiten_option_3"),
                ],
                required=True,
            ),
            "tabellen_verarbeiten": st.column_config.SelectboxColumn(
                api.text("tabelle_tabellen_verarbeiten_title"),
                width="medium",
                options=[
                    api.text("tabelle_tabellen_verarbeiten_option_1"),
                    api.text("tabelle_tabellen_verarbeiten_option_2"),
                    api.text("tabelle_tabellen_verarbeiten_option_3"),
                    api.text("tabelle_tabellen_verarbeiten_option_4"),
                ],
                required=True,
            ),
        },
        disabled=["art", "pfad", "erstellungsdatum"],
        hide_index=True,
    )

    referenzdokumente_auswahl: list = []
    for id, row in edited_df.iterrows():

        if row["art"] == api.text("tabelle_art_pdf"):
            pfad = f"{referenzdokumente_pdfs_ordner}/{row["name"]}"
        elif row["art"] == "CSV":
            pfad = f"{referenzdokumente_pdfs_ordner}/{row["name"]}"
        else:
            pfad = row["name"]

        referenzdokument = Referenzdokument(
            id=id,
            art=row["art"],
            name=row["name"],
            pfad=pfad,
            erstellungsdatum=row["erstellungsdatum"],
        )

        text_zusammenfassen = False
        text_zusammenfassen_mit_zahlen = False
        if row["text_verarbeiten"] == api.text("tabelle_text_verarbeiten_option_2"):
            text_zusammenfassen = True
            text_zusammenfassen_mit_zahlen = True
        elif row["text_verarbeiten"] == api.text("tabelle_text_verarbeiten_option_3"):
            text_zusammenfassen = True

        tabellen_extrahieren = False
        tabellen_zusammenfassen = False
        tabellen_zusammenfassen_mit_zahlen = False
        if row["tabellen_verarbeiten"] == api.text(
            "tabelle_tabellen_verarbeiten_option_2"
        ):
            tabellen_extrahieren = True
        if row["tabellen_verarbeiten"] == api.text(
            "tabelle_tabellen_verarbeiten_option_3"
        ):
            tabellen_extrahieren = True
            tabellen_zusammenfassen = True
            tabellen_zusammenfassen_mit_zahlen = True
        if row["tabellen_verarbeiten"] == api.text(
            "tabelle_tabellen_verarbeiten_option_4"
        ):
            tabellen_extrahieren = True
            tabellen_zusammenfassen = True

        zusammenfassung_auswahl = ZusammenfassungAuswahl(
            text_zusammenfassen=text_zusammenfassen,
            text_zusammenfassen_mit_zahlen=text_zusammenfassen_mit_zahlen,
            tabellen_extrahieren=tabellen_extrahieren,
            tabellen_zusammenfassen=tabellen_zusammenfassen,
            tabellen_zusammenfassen_mit_zahlen=tabellen_zusammenfassen_mit_zahlen,
        )

        if zusammenfassung_auswahl.soll_vorbereitet_werden():
            referenzdokumente_auswahl.append(
                ReferenzdokumentAuswahl(
                    referenzdokument=referenzdokument,
                    zusammenfassung_auswahl=zusammenfassung_auswahl,
                )
            )

    col1, col2 = st.columns([3, 1])

    with col2:

        llm_provider: LLMProvider = api.streamlit_llm_provider_auswahl()

        # Startbutton
        st.button(
            api.text("steuerung_start_text"),
            on_click=starten,
            icon=api.text("steuerung_start_icon"),
            disabled=st.session_state[f"{session_key}.gestartet"],
            width="stretch",
        )

        # Abbruchbutton
        st.button(
            api.text("steuerung_abbruch_text"),
            on_click=abbrechen,
            icon=api.text("steuerung_abbruch_icon"),
            disabled=not st.session_state[f"{session_key}.gestartet"],
            width="stretch",
        )

    with col1:
        if prozess_gestartet:

            with st.spinner(api.text("spinner"), show_time=True):
                fortschritt = st.progress(0)

                zusammenfassungsgenerator = Zusammenfassungsgenerator(
                    referenzdokumente_auswahl=referenzdokumente_auswahl,
                    prompt=Prompt(
                        prompts={
                            "text_zusammenfassen_mit_zahlen": prompt_text_mit_zahlen,
                            "text_zusammenfassen_ohne_zahlen": prompt_text_ohne_zahlen,
                            "tabellen_zusammenfassen_mit_zahlen": prompt_tabellen_mit_zahlen,
                            "tabellen_zusammenfassen_ohne_zahlen": prompt_tabellen_ohne_zahlen,
                        },
                        prompt_data={},
                    ),
                    llm_provider=llm_provider,
                )
                zusammenfassungen: list[Zusammenfassung] = (
                    zusammenfassungsgenerator.starten(streamlit_fortschitt=fortschritt)
                )

                zusammenfassungen_dateiname = f"{api.komponenten_name}-{zusammenfassungsgenerator.startzeit_formatiert()}.json"
                zusammenfassungen_dateipfad = erstelle_dateipfad(
                    ordnerpfad=zusammenfassungen_ordner,
                    dateiname=zusammenfassungen_dateiname,
                    mit_basepath=False,
                )

                datei_speichern(
                    dateipfad=zusammenfassungen_dateipfad, items=zusammenfassungen
                )

                fertig(zusammenfassungen_dateipfad)

with tab2:
    zusammenfassungen: list[Zusammenfassung] = api.streamlit_zusammenfassungen_auswahl(
        zusammenfassungen_ordner=zusammenfassungen_ordner,
        vorausgewaehlt=str(st.session_state[f"{session_key}.ergebnis"]),
    )
    api.streamlit_zusammenfassungen_anzeigen(zusammenfassungen=zusammenfassungen)

with tab3:

    prompt_text_mit_zahlen = st.text_area(
        label=f"{api.text("prompt_text_mit_zahlen")} ({prompt_datei_text_mit_zahlen})",
        value=prompt_text_mit_zahlen,
        height="content",
    )
    prompt_text_ohne_zahlen = st.text_area(
        label=f"{api.text("prompt_text_ohne_zahlen")} ({prompt_datei_text_ohne_zahlen})",
        value=prompt_text_ohne_zahlen,
        height="content",
    )
    prompt_tabellen_mit_zahlen = st.text_area(
        label=f"{api.text("prompt_tabellen_mit_zahlen")} ({prompt_datei_tabellen_mit_zahlen})",
        value=prompt_tabellen_mit_zahlen,
        height="content",
    )
    prompt_tabellen_ohne_zahlen = st.text_area(
        label=f"{api.text("prompt_tabellen_ohne_zahlen")} ({prompt_datei_tabellen_zusammenfassen_ohne_zahlen})",
        value=prompt_tabellen_ohne_zahlen,
        height="content",
    )
