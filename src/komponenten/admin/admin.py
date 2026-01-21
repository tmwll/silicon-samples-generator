import streamlit as st
from src.shared.komponenten import komponenten_config

config = komponenten_config(__file__)

st.title(config["page"]["title"])

tab1, tab2, tab3 = st.tabs(["Komponenten", "Komponenten-Konfiguration", "Session"])

with tab1:
    st.header("Komponenten")
    st.info(
        "In der TOML-Datei 'ssg.toml' wird definiert, welche Komponenten es gibt bzw. aktiv sind."
    )
    st.json(st.session_state["config"]["komponenten"])

with tab2:
    st.header("Komponenten-Konfiguration")
    st.info(
        "Zu jeder aktiven Komponente gibt es eine eigene TOML-Datei. Die jeweiligen Pfade sind in der TOML-Datei 'ssg.toml' definiert. Die Komponenten-TOMLs werden automatisch geladen."
    )
    st.json(st.session_state["config"]["komponente"])

with tab3:
    st.header("Session")
    st.json(st.session_state)
