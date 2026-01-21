from datetime import datetime
import pprint
from typing import Any
import streamlit as st


import pandas as pd

from src.komponenten.referenzdokumente.referenzdokumente_api import ReferenzdokumenteAPI
from src.komponenten.referenzdokumente.referenzdokumente_models import (
    Zusammenfassung,
)
from src.komponenten.siliconsamplesgenerator.fragesteller.fragesteller import (
    Fragesteller,
)
from src.komponenten.siliconsamplesgenerator.siliconsamplesgenerator_api import (
    SiliconSamplesGeneratorAPI,
)
from src.komponenten.siliconsamplesgenerator.siliconsamplesgenerator_models import (
    SiliconSamples,
)
from src.komponenten.studienkonfiguration.studienkonfiguration_api import (
    StudienkonfigurationAPI,
)
from src.komponenten.studienkonfiguration.studienkonfigurationslader.studienkonfigurationslader import (
    Studienkonfigurationslader,
)
from src.shared.dateien import (
    datei_lesen,
    datei_speichern,
    erstelle_dateipfad,
    dateipfad_relativ,
    ordner_auslesen,
)

from src.shared.generator import Prompt, schicke_update_an_user
from src.shared.llm_integrations.llm_provider import LLMProvider
from src.shared.logger import get_logger
from src.shared.status import Status

log = get_logger(__name__)

api = SiliconSamplesGeneratorAPI()
config = api.config

api_studienkonfiguration = StudienkonfigurationAPI()
api_referenzdokumente = ReferenzdokumenteAPI()


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
    st.session_state[f"{session_key}.ergebnis"] = None


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

    # Prompt: Intro ohne Persona mit Referenzdokumenten
    prompt_datei_intro_ohne_persona_mit_referenzdokumenten = erstelle_dateipfad(
        ordnerpfad=prompts_ordner,
        dateiname=api.prompts_datei_intro_ohne_persona_mit_referenzdokumenten,
        mit_basepath=False,
    )
    prompt_intro_ohne_persona_mit_referenzdokumenten = datei_lesen(
        prompt_datei_intro_ohne_persona_mit_referenzdokumenten
    )

    # Prompt: Intro ohne Persona ohne Referenzdokumente
    prompt_datei_intro_ohne_persona_ohne_referenzdokumente = erstelle_dateipfad(
        ordnerpfad=prompts_ordner,
        dateiname=api.prompts_datei_intro_ohne_persona_ohne_referenzdokumente,
        mit_basepath=False,
    )
    prompt_intro_ohne_persona_ohne_referenzdokumente = datei_lesen(
        prompt_datei_intro_ohne_persona_ohne_referenzdokumente
    )

    # Prompt: Intro mit Persona mit Referenzdokumenten
    prompt_datei_intro_mit_persona_mit_referenzdokumenten = erstelle_dateipfad(
        ordnerpfad=prompts_ordner,
        dateiname=api.prompts_datei_intro_mit_persona_mit_referenzdokumenten,
        mit_basepath=False,
    )
    prompt_intro_mit_persona_mit_referenzdokumenten = datei_lesen(
        prompt_datei_intro_mit_persona_mit_referenzdokumenten
    )

    # Prompt: Intro mit Persona ohne Referenzdokumente
    prompt_datei_intro_mit_persona_ohne_referenzdokumente = erstelle_dateipfad(
        ordnerpfad=prompts_ordner,
        dateiname=api.prompts_datei_intro_mit_persona_ohne_referenzdokumente,
        mit_basepath=False,
    )
    prompt_intro_mit_persona_ohne_referenzdokumente = datei_lesen(
        prompt_datei_intro_mit_persona_ohne_referenzdokumente
    )

    studienkonfiguration_datei = st.text_input(
        api_studienkonfiguration.text("dateiname"),
        help=api_studienkonfiguration.text("dateiname_beschreibung"),
        value=api_studienkonfiguration.dateipfad,
    )

    zusammenfassungen_ordner = dateipfad_relativ(
        dateipfad=st.text_input(
            api_referenzdokumente.text("zusammenfassungen_ordner_name"),
            help=api_referenzdokumente.text("zusammenfassungen_ordner_beschreibung"),
            value=api_referenzdokumente.zusammenfassungen_ordner,
        )
    )

    personas_datei = dateipfad_relativ(
        dateipfad=st.text_input(
            api.text("personas_dateiname"),
            help=api.text("personas_dateiname_beschreibung"),
            value=api.personas_datei,
        )
    )

    siliconsamples_ordner = dateipfad_relativ(
        dateipfad=st.text_input(
            api.text("siliconsamples_ordner_name"),
            help=api.text("siliconsamples_ordner_beschreibung"),
            value=api.siliconsamples_ordner,
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


tab1, tab2, tab3, tab4 = st.tabs(
    [
        api.text("tab_generieren_titel"),
        "Personas anzeigen",
        api.text("tab_anzeigen_titel"),
        api.text("tab_prompts_titel"),
    ]
)

with tab2:
    df = pd.read_csv(personas_datei, sep=";")
    df.index = df.index + 1
    table = st.dataframe(df)
    prompt_data_personas = df.reset_index(names="index").to_dict("records")

with tab3:

    siliconsamples: SiliconSamples = api.streamlit_siliconsamples_auswahl(
        siliconsamples_ordner=siliconsamples_ordner,
        vorausgewaehlt=str(st.session_state[f"{session_key}.ergebnis"]),
    )
    if siliconsamples:
        api.streamlit_siliconsamples_anzeigen(siliconsamples=siliconsamples)

with tab4:

    prompt_intro_ohne_persona_mit_referenzdokumenten = st.text_area(
        label=f"{api.text("prompt_intro_ohne_persona_mit_referenzdokumenten")} ({prompt_datei_intro_ohne_persona_mit_referenzdokumenten})",
        value=prompt_intro_ohne_persona_mit_referenzdokumenten,
        height=350,
    )
    prompt_intro_ohne_persona_ohne_referenzdokumente = st.text_area(
        label=f"{api.text("prompt_intro_ohne_persona_ohne_referenzdokumente")} ({prompt_datei_intro_ohne_persona_ohne_referenzdokumente})",
        value=prompt_intro_ohne_persona_ohne_referenzdokumente,
        height=350,
    )

    prompt_intro_mit_persona_mit_referenzdokumenten = st.text_area(
        label=f"{api.text("prompt_intro_mit_persona_mit_referenzdokumenten")} ({prompt_datei_intro_mit_persona_mit_referenzdokumenten})",
        value=prompt_intro_mit_persona_mit_referenzdokumenten,
        height=350,
    )
    prompt_intro_mit_persona_ohne_referenzdokumente = st.text_area(
        label=f"{api.text("prompt_intro_mit_persona_ohne_referenzdokumente")} ({prompt_datei_intro_mit_persona_ohne_referenzdokumente})",
        value=prompt_intro_mit_persona_ohne_referenzdokumente,
        height=350,
    )

with tab1:

    col1, col2 = st.columns([1, 2])

    with col1:

        zusammenfassungen: list[Zusammenfassung] = (
            api_referenzdokumente.streamlit_zusammenfassungen_auswahl(
                zusammenfassungen_ordner=zusammenfassungen_ordner
            )
        )

        wiederholungen = st.number_input(
            "Wie viele Silicon Samples sollen generiert werden?",
            value=1,
            min_value=1,
            max_value=1000,
            placeholder="Anzahl angeben",
        )

        personas_nutzen = st.toggle("Personas nutzen", value=True)

        llm_provider: LLMProvider = api.streamlit_llm_provider_auswahl()

        buttoncol1, buttoncol2 = st.columns(2)

        with buttoncol1:
            # Startbutton
            st.button(
                api.text("steuerung_start_text"),
                on_click=starten,
                icon=api.text("steuerung_start_icon"),
                disabled=st.session_state[f"{session_key}.gestartet"],
                width="stretch",
            )

        with buttoncol2:
            # Abbruchbutton
            st.button(
                api.text("steuerung_abbruch_text"),
                on_click=abbrechen,
                icon=api.text("steuerung_abbruch_icon"),
                disabled=not st.session_state[f"{session_key}.gestartet"],
                width="stretch",
            )

        if personas_nutzen:
            st.caption(
                f"Es werden :blue-background[{wiederholungen} Silicon Samples mit Persona-Kontext] generiert. Die Personas werden aufsteigend iteriert. Wenn weniger Stichproben als Personas ausgewählt sind, werden nicht mit allen Personas Silicon Samples generiert. Wenn mehr Stichproben als Personas ausgewähl sind, werden die Personas wiederholt."
            )
        else:
            st.caption(
                f"Es werden :blue-background[{wiederholungen} Silicon Samples ohne Persona-Kontext] generiert."
            )

    with col2:
        api_referenzdokumente.streamlit_zusammenfassungen_anzeigen(
            zusammenfassungen=zusammenfassungen, zeige_tokens=False
        )

        if prozess_gestartet:

            with st.spinner(api.text("spinner"), show_time=True):

                fortschritt = st.progress(0)

                startzeit = datetime.now()
                startzeit_formatiert = startzeit.strftime("%Y_%m_%d-%H_%M_%S")

                for aktuelle_wiederholung in range(0, wiederholungen):

                    aktuelle_wiederholung_menschenfreundlich = aktuelle_wiederholung + 1

                    schicke_update_an_user(
                        f"Silicon Sample {aktuelle_wiederholung_menschenfreundlich}/{wiederholungen} gestartet"
                    )

                    fortschritt.progress(
                        (
                            (aktuelle_wiederholung / wiederholungen)
                            if aktuelle_wiederholung > 0
                            else 0
                        ),
                        text=f"Aktuell generiertes Silicon Sample: {aktuelle_wiederholung_menschenfreundlich}",
                    )

                    studienkonfigurationslader = Studienkonfigurationslader(
                        studienkonfiguration_datei
                    )

                    fragesteller = Fragesteller(
                        fragen=studienkonfigurationslader.fragen,
                        zusammenfassungen=zusammenfassungen,
                        prompt=Prompt(
                            prompts={
                                "fragen_intro_ohne_persona_mit_referenzen": prompt_intro_ohne_persona_mit_referenzdokumenten,
                                "fragen_intro_ohne_persona_ohne_referenzen": prompt_intro_ohne_persona_ohne_referenzdokumente,
                                "fragen_intro_mit_persona_mit_referenzen": prompt_intro_mit_persona_mit_referenzdokumenten,
                                "fragen_intro_mit_persona_ohne_referenzen": prompt_intro_mit_persona_ohne_referenzdokumente,
                            },
                            prompt_data={
                                "aktuelle_wiederholung": aktuelle_wiederholung,
                                "personas_nutzen": personas_nutzen,
                                "aktuelle_persona": (
                                    api.hole_persona_fuer_wiederholung(
                                        personas=prompt_data_personas,
                                        wiederholung=aktuelle_wiederholung,
                                    )
                                    if personas_nutzen
                                    else None
                                ),
                                "personas": (
                                    prompt_data_personas if personas_nutzen else None
                                ),
                            },
                        ),
                        llm_provider=llm_provider,
                    )

                    siliconsamples = fragesteller.starten(
                        streamlit_fortschritt=fortschritt
                    )

                    siliconsamples_dateiname = f"{api.komponenten_name}-{fragesteller.startzeit_formatiert()}-{aktuelle_wiederholung}.json"
                    siliconsamples_dateipfad = (
                        erstelle_dateipfad(
                            ordnerpfad=siliconsamples_ordner,
                            dateiname=startzeit_formatiert,
                            mit_basepath=False,
                        )
                        / siliconsamples_dateiname
                    )

                    datei_speichern(
                        dateipfad=siliconsamples_dateipfad, items=siliconsamples
                    )

                    schicke_update_an_user(
                        f"Silicon Sample {aktuelle_wiederholung_menschenfreundlich}/{wiederholungen} generiert"
                    )

                fertig(ergebnis=None)
