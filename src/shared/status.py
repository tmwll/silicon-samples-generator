import streamlit as st


class Status:

    def __init__(self, label, expanded=True):
        self.status = st.status(label=label, expanded=expanded, state="running")

    def update(self, label, change_title=False, expanded=True, state="running"):
        self.status.write(label)
        if change_title:
            self.status.update(label=label, expanded=expanded, state=state)

    def finish(self, label, expanded=True):
        self.update(label=label, change_title=True, expanded=expanded, state="complete")
