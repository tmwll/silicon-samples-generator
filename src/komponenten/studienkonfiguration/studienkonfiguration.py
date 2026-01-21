import streamlit as st
from src.komponenten.studienkonfiguration.studienkonfiguration_api import (
    StudienkonfigurationAPI,
)
from src.shared.dateien import dateipfad_relativ

from src.shared.logger import get_logger

log = get_logger(__name__)

api = StudienkonfigurationAPI()
config = api.config

# Anwendungstitel
st.title(config["page"]["title"])

with st.sidebar:

    datei = st.text_input(
        api.text("dateiname"),
        help=api.text("dateiname_beschreibung"),
        value=api.dateipfad,
    )

    studienkonfiguration = api.studienkonfiguration(datei)

    # tab_xml, tab_objekte = st.tabs(
    #     [
    #         api.text("tab_xml_titel"),
    #         api.text("tab_objekte_titel"),
    #     ]
    # )

    # with tab_xml:
# st.header(api.text("tab_xml_titel"))
# st.info(api.text("tab_xml_info"))
st.code(studienkonfiguration.xml_datei())

# with tab_objekte:
#     st.header(api.text("tab_objekte_titel"))
#     st.info(api.text("tab_objekte_info"))
#     for frage in studienkonfiguration.fragen:
#         with st.expander(f"Frage: {frage.id}: {frage.text}"):
#             st.write(frage)
