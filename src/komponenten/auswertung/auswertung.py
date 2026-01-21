import pandas as pd
import streamlit as st
from src.komponenten.auswertung.auswertung_api import AuswertungAPI
from src.komponenten.siliconsamplesgenerator.siliconsamplesgenerator_api import (
    SiliconSamplesGeneratorAPI,
)
from src.komponenten.siliconsamplesgenerator.siliconsamplesgenerator_models import (
    SiliconSamples,
)
from src.shared.dateien import dateipfad_relativ
from src.shared.komponenten import komponenten_config

api = AuswertungAPI()
config = api.config

api_siliconsamples = SiliconSamplesGeneratorAPI()

st.title(config["page"]["title"])

with st.sidebar:

    siliconsamples_ordner = st.text_input(
        api_siliconsamples.text("siliconsamples_ordner_name"),
        help=api_siliconsamples.text("siliconsamples_ordner_beschreibung"),
        value=dateipfad_relativ(api_siliconsamples.siliconsamples_ordner),
    )

siliconsamples: SiliconSamples = api_siliconsamples.streamlit_siliconsamples_auswahl(
    siliconsamples_ordner=siliconsamples_ordner
)
if siliconsamples:
    api_siliconsamples.streamlit_siliconsamples_anzeigen(siliconsamples=siliconsamples)
