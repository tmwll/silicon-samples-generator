import inspect
from typing_extensions import Literal
from langgraph.types import Command
from langgraph.graph import START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import RemoveMessage, REMOVE_ALL_MESSAGES
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.komponenten.referenzdokumente.referenzdokumente_models import (
    ReferenzdokumentState,
    Referenzdokument,
    ReferenzdokumentAuswahl,
    Zusammenfassung,
    ZusammenfassungAuswahl,
)
from src.komponenten.referenzdokumente.zusammenfassungsgenerator.lader_csv import (
    CSVLader,
)
from src.komponenten.referenzdokumente.zusammenfassungsgenerator.lader_url import (
    URLLader,
)
from src.komponenten.referenzdokumente.zusammenfassungsgenerator.lader_pdf import (
    PDFLader,
)
from src.shared.generator import (
    LLM,
    LLMChatverlauf,
    LLMGenerator,
    Prompt,
    hole_llm_instanz_aus_graph,
    hole_prompt_aus_graph,
    hole_tokenverbrauch_aus_graph,
    parse_llm_content,
)
from src.shared.llm_integrations.llm_provider import LLMProvider
from src.shared.logger import get_logger

log = get_logger(__name__)


class Zusammenfassungsgenerator(LLMGenerator):

    def __init__(
        self,
        referenzdokumente_auswahl: list[ReferenzdokumentAuswahl],
        prompt: Prompt,
        llm_provider: LLMProvider,
    ):
        super().__init__(
            prompt=prompt,
            llm_provider=llm_provider,
            state_class=ReferenzdokumentState,
            thread_prefix="Zusammenfassungen",
        )

        self.referenzdokumente_auswahl = referenzdokumente_auswahl

        self.graph_bauen()

    def graph_bauen(self):
        self.graph.add_node(node_kontext)
        self.graph.add_node(node_historie_loeschen)
        self.graph.add_node(pruefe_text_zusammenfassen)
        self.graph.add_node(node_text_zusammenfassen)
        self.graph.add_node(pruefe_tabellen_extrahieren)
        self.graph.add_node(node_tabellen_extrahieren)
        self.graph.add_node(pruefe_tabellen_zusammenfassen)
        self.graph.add_node(node_tabellen_zusammenfassen)

        self.graph.add_edge(START, "node_kontext")
        self.graph.add_edge("node_kontext", "node_historie_loeschen")
        self.graph.add_edge("node_historie_loeschen", "pruefe_text_zusammenfassen")
        self.graph.add_edge("node_text_zusammenfassen", "pruefe_tabellen_extrahieren")
        self.graph.add_edge(
            "node_tabellen_extrahieren", "pruefe_tabellen_zusammenfassen"
        )
        self.graph.add_edge("node_tabellen_zusammenfassen", END)

        self.graph = self.graph.compile(checkpointer=InMemorySaver())

    def starten(self, streamlit_fortschitt) -> list[Zusammenfassung]:

        zusammenfassungen: list[Zusammenfassung] = []

        anzahl_referenzdokumente = len(self.referenzdokumente_auswahl)
        for i, referenzdokumente_auswahl in enumerate(
            self.referenzdokumente_auswahl, 1
        ):

            referenzdokument: Referenzdokument = (
                referenzdokumente_auswahl.referenzdokument
            )
            zusammenfassung_auswahl: ZusammenfassungAuswahl = (
                referenzdokumente_auswahl.zusammenfassung_auswahl
            )

            state = ReferenzdokumentState(
                referenzdokument=referenzdokument,
                zusammenfassung_auswahl=zusammenfassung_auswahl,
                aktuelles_referenzdokument=i,
                anzahl_referenzdokumente=anzahl_referenzdokumente,
                text_extrahiert="",
                text_zusammengefasst="",
                text_zusammengefasst_messages=[],
                tabellen_extrahiert=[],
                tabellen_zusammengefasst=[],
                tabellen_zusammengefasst_messages=[],
            )

            out = self.aufrufen(
                state=state,
                streamlit_fortschritt=streamlit_fortschitt,
                run_name=f"Referenz {referenzdokument.name}",
                reset_tokenverbrauch=True,  # Weil hier die Tokens pro Zusammenfassung gespeichert werden, muss nach jedem Lauf resettet werden
            )

            chatverlaeufe: list[LLMChatverlauf] = []

            chatverlauf_text = out.get("text_zusammengefasst_messages", {})
            if chatverlauf_text:
                chatverlaeufe.append(
                    LLMChatverlauf(
                        name="text_zusammengefasst",
                        chatverlauf=chatverlauf_text,
                    )
                )

            chatverlaeufe_tabellen = out.get("tabellen_zusammengefasst_messages", [])
            for chatverlauf_tabelle in chatverlaeufe_tabellen:
                chatverlaeufe.append(
                    LLMChatverlauf(
                        name="tabellen_zusammengefasst",
                        chatverlauf=chatverlauf_tabelle,
                    )
                )

            zusammenfassungen.append(
                Zusammenfassung(
                    referenzdokument=referenzdokument,
                    zusammenfassung_auswahl=zusammenfassung_auswahl,
                    erstellungsdatum=self.startzeit_formatiert(),
                    text_extrahiert=out.get("text_extrahiert", ""),
                    text_zusammengefasst=out.get("text_zusammengefasst", ""),
                    tabellen_extrahiert=out.get("tabellen_extrahiert", []),
                    tabellen_zusammengefasst=out.get("tabellen_zusammengefasst", []),
                    prompt=self.prompt,
                    llm=LLM(
                        konfiguration=self.llm_config_holen(),
                        tokenverbrauch=self.llm_tokenverbrauch(),
                        chatverlaeufe=chatverlaeufe,
                    ),
                )
            )

        return zusammenfassungen


def fortschritt(prozessschritt: int, text: str, state, config):
    referenz: Referenzdokument = state["referenzdokument"]
    aktuelle_referenz: int = state["aktuelles_referenzdokument"]
    anzahl_referenzen: int = state["anzahl_referenzdokumente"]

    prozent_referenz = aktuelle_referenz / anzahl_referenzen
    prozent_prozessschritt = prozent_referenz / 7 * prozessschritt

    tokenverbrauch = hole_tokenverbrauch_aus_graph(config)
    fortschritt = (
        (config or {}).get("configurable", {}).get("streamlit_fortschritt", None)
    )
    fortschritt.progress(
        prozent_prozessschritt,
        text=f"{referenz.name}: {text} - {tokenverbrauch} Token verbraucht!",
    )


def node_kontext(state, config=None):
    fortschritt(1, "Vearbeitung vorbereiten", state, config)
    return {}


def node_historie_loeschen(state):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")
    result = {
        "text_zusammengefasst_messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
        "tabellen_zusammengefasst_messages": [],
    }
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result


def pruefe_text_zusammenfassen(
    state, config=None
) -> Command[Literal["node_text_zusammenfassen", "pruefe_tabellen_extrahieren"]]:
    fortschritt(
        2, "Überprüfen, ob Zusammenfassung aus Text erstellt werden soll", state, config
    )
    zusammenfassung_auswahl: ZusammenfassungAuswahl = state["zusammenfassung_auswahl"]
    if zusammenfassung_auswahl.text_zusammenfassen:
        return Command(goto="node_text_zusammenfassen")
    return Command(goto="pruefe_tabellen_extrahieren")


def node_text_zusammenfassen(state, config=None):
    fortschritt(3, "Text auslesen", state, config)
    referenzdokument: Referenzdokument = state["referenzdokument"]
    zusammenfassung_auswahl: ZusammenfassungAuswahl = state["zusammenfassung_auswahl"]

    text_extrahiert: str = ""
    zusammengefasst: str = ""
    messages = []

    if referenzdokument.art == "URL":
        lader = URLLader()
    elif referenzdokument.art == "CSV":
        lader = CSVLader()
    else:
        lader = PDFLader()

    text_extrahiert = lader.extrahiere_text(referenzdokument.pfad)

    if text_extrahiert != "":

        ##### LLM zusammenfassen lassen

        if zusammenfassung_auswahl.text_zusammenfassen_mit_zahlen:
            fortschritt(
                3, "Text von KI zusammenfassen lassen (mit Zahlen)", state, config
            )
            prompt_zusammenfassung = hole_prompt_aus_graph(
                "text_zusammenfassen_mit_zahlen", config
            )
        else:
            fortschritt(
                3, "Text von KI zusammenfassen lassen (ohne Zahlen)", state, config
            )
            prompt_zusammenfassung = hole_prompt_aus_graph(
                "text_zusammenfassen_ohne_zahlen", config
            )

        messages.append(SystemMessage(content=prompt_zusammenfassung))
        messages.append(HumanMessage(content=text_extrahiert))

        antwort_message: AIMessage = hole_llm_instanz_aus_graph(config).invoke(messages)
        messages.append(antwort_message)

        zusammengefasst = parse_llm_content(antwort_message, config)

    return {
        "text_extrahiert": text_extrahiert,
        "text_zusammengefasst": zusammengefasst,
        "text_zusammengefasst_messages": messages,
    }


def pruefe_tabellen_extrahieren(state, config=None) -> Command[Literal["node_tabellen_extrahieren", END]]:  # type: ignore
    fortschritt(4, "Überprüfen, ob Tabellen extrahiert werden sollen", state, config)
    zusammenfassung_auswahl: ZusammenfassungAuswahl = state["zusammenfassung_auswahl"]
    if zusammenfassung_auswahl.tabellen_extrahieren:
        return Command(goto="node_tabellen_extrahieren")
    return Command(goto=END)


def node_tabellen_extrahieren(state, config=None):
    fortschritt(5, "Tabellen extrahieren", state, config)
    referenzdokument: Referenzdokument = state["referenzdokument"]

    tabellen_extrahiert: list[str] = []
    if referenzdokument.art == "URL":
        lader = URLLader()
    elif referenzdokument.art == "CSV":
        lader = CSVLader()
    else:
        lader = PDFLader()

    tabellen_extrahiert = lader.extrahiere_tabellen(referenzdokument.pfad, zeilen=20)

    return {"tabellen_extrahiert": tabellen_extrahiert}


def pruefe_tabellen_zusammenfassen(state, config=None) -> Command[Literal["node_tabellen_zusammenfassen", END]]:  # type: ignore
    fortschritt(
        6,
        "Überprüfen, ob Zusammenfassungen aus Tabellen erstellt werden sollen",
        state,
        config,
    )
    zusammenfassung_auswahl: ZusammenfassungAuswahl = state["zusammenfassung_auswahl"]
    if zusammenfassung_auswahl.tabellen_zusammenfassen:
        return Command(goto="node_tabellen_zusammenfassen")
    return Command(goto=END)


def node_tabellen_zusammenfassen(state, config=None):
    fortschritt(7, "Tabellen zusammenfassen", state, config)
    zusammenfassung_auswahl: ZusammenfassungAuswahl = state["zusammenfassung_auswahl"]

    tabellen: list[str] = state.get("tabellen_extrahiert", [])
    tabellen_zusammengefasst: list[str] = []
    messages_liste: list[str] = []

    anzahl_tabellen = len(tabellen)

    for i, tabelle in enumerate(tabellen, 1):

        ##### LLM zusammenfassen lassen

        messages = []

        if zusammenfassung_auswahl.tabellen_zusammenfassen_mit_zahlen:
            fortschritt(
                7,
                f"Tabelle {i}/{anzahl_tabellen} von KI zusammenfassen lassen (mit Zahlen)",
                state,
                config,
            )
            prompt_zusammenfassung = hole_prompt_aus_graph(
                "tabellen_zusammenfassen_mit_zahlen", config
            )
        else:
            fortschritt(
                7,
                f"Tabelle {i}/{anzahl_tabellen} von KI zusammenfassen lassen (ohne Zahlen)",
                state,
                config,
            )
            prompt_zusammenfassung = hole_prompt_aus_graph(
                "tabellen_zusammenfassen_ohne_zahlen", config
            )

        messages.append(SystemMessage(content=prompt_zusammenfassung))
        messages.append(HumanMessage(content=tabelle))

        antwort_message: AIMessage = hole_llm_instanz_aus_graph(config).invoke(messages)
        messages.append(antwort_message)

        zusammengefasst = parse_llm_content(antwort_message, config)

        messages_liste.append(messages)
        tabellen_zusammengefasst.append(zusammengefasst)

    return {
        "tabellen_zusammengefasst": tabellen_zusammengefasst,
        "tabellen_zusammengefasst_messages": messages_liste,
    }
