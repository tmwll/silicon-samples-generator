from src.komponenten.startseite.startseite_api import StartseiteAPI
import streamlit as st

from src.shared.logger import get_logger

log = get_logger(__name__)

api = StartseiteAPI()
config = api.config

# Anwendungstitel
st.title(config["page"]["title"])

st.header(api.text("subtitle"))

st.markdown(
    """
    Der **Silicon-Samples-Generator** ist ein LLM-System, das **kontextsensitive Silicon Samples** erzeugt.
    
    Ein **Large Language Model (LLM)** wird in die Rolle von Befragten versetzt (z. B. über demografische Merkmale) 
    und beantwortet die Items eines Fragebogens.

    👈 Wähle eine Komponente um zu starten.
"""
)
