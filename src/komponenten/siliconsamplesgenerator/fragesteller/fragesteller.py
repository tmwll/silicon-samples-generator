import copy
import inspect
from typing_extensions import Literal
from langgraph.types import Command
from langgraph.graph import START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import RemoveMessage, REMOVE_ALL_MESSAGES
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.komponenten.referenzdokumente.referenzdokumente_models import (
    Zusammenfassung,
)
from src.komponenten.siliconsamplesgenerator.fragesteller.fragenmanager import (
    Fragenmanager,
)
from src.komponenten.siliconsamplesgenerator.siliconsamplesgenerator_models import (
    SiliconSampleState,
    StrukturierteFrage,
    SiliconSamples,
)
from src.komponenten.studienkonfiguration.studienkonfigurationslader.models import Frage

from src.shared.generator import (
    LLMGenerator,
    LLM,
    LLMChatverlauf,
    Prompt,
    hole_llm_instanz_aus_graph,
    hole_prompt_aus_graph,
    hole_prompt_data_aus_graph,
    parse_llm_content,
)

from src.shared.llm_integrations.llm_provider import LLMProvider
from src.shared.logger import get_logger

log = get_logger(__name__)


class Fragesteller(LLMGenerator):

    def __init__(
        self,
        fragen: list[Frage],
        zusammenfassungen: list[Zusammenfassung],
        prompt: Prompt,
        llm_provider: LLMProvider,
    ):
        super().__init__(
            prompt=prompt,
            llm_provider=llm_provider,
            state_class=SiliconSampleState,
            thread_prefix="Silicon Samples",
        )

        self.zusammenfassungen = zusammenfassungen

        self.fragen = fragen

        self.graph_bauen()

    def graph_bauen(self):
        self.graph.add_node(node_definiere_aktuellen_kontext)
        self.graph.add_node(node_definiere_kontextwechsel)
        self.graph.add_node(node_historie_loeschen)
        self.graph.add_node(node_fragenintro_generieren)
        self.graph.add_node(node_frage_generieren)
        self.graph.add_node(node_frage_stellen)
        self.graph.add_node(node_antwort_validieren)
        self.graph.add_node(node_aktualisiere_letzten_kontext)

        self.graph.add_edge(START, "node_definiere_aktuellen_kontext")

        self.graph.add_conditional_edges(
            "node_definiere_aktuellen_kontext",
            pruefe_kontextwechsel,
            {True: "node_definiere_kontextwechsel", False: END},
        )

        self.graph.add_edge("node_definiere_kontextwechsel", "node_historie_loeschen")
        self.graph.add_edge("node_historie_loeschen", "node_fragenintro_generieren")
        self.graph.add_edge("node_fragenintro_generieren", "node_frage_generieren")
        self.graph.add_edge("node_frage_generieren", "node_frage_stellen")
        self.graph.add_edge("node_frage_stellen", "node_antwort_validieren")

        self.graph.add_edge("node_aktualisiere_letzten_kontext", END)

        self.graph = self.graph.compile(checkpointer=InMemorySaver())

    def starten(self, streamlit_fortschritt):
        log.info("Starte Befragung, Fragenmanager instanzieren")

        fragenmanager = Fragenmanager(fragen=self.fragen)

        letzter_kontext_key = None

        chatverlaeufe: list[LLMChatverlauf] = []

        while True:

            # Eine Frage/Kontext pro Submit
            strukturierte_frage: StrukturierteFrage = fragenmanager.naechste_frage()

            if strukturierte_frage is None:
                log.info("Keine weitere Frage mehr")
                break

            log.info(f"Nächste Frage: {strukturierte_frage.frage_id}")
            for themenkontext in strukturierte_frage.themenkontexte:

                kontext_key = (
                    f"{strukturierte_frage.frage_id}-{themenkontext.parent_thema_key}"
                )

                log.info(f"Nächster Themenkontext: {kontext_key}")

                if letzter_kontext_key == kontext_key:
                    log.info(f"Themenkontext fertig bearbeitet")
                    continue

                state = SiliconSampleState(
                    frage=strukturierte_frage,
                    kontext=themenkontext,
                    kontextwechsel=False,
                    letzter_kontext_key=letzter_kontext_key,
                    zusammenfassungen=self.zusammenfassungen,
                )

                log.info(f"LLM-Prozess starten")
                out = self.aufrufen(
                    state=state,
                    streamlit_fortschritt=streamlit_fortschritt,
                    run_name=f"Silicon Samples {kontext_key}",
                )
                log.info(f"LLM-Prozess beendet")

                letzter_kontext_key = out.get(
                    "letzter_kontext_key", letzter_kontext_key
                )

                antworten = out.get("antworten", {})
                if antworten:
                    for antwort_thema, antwort_option in antworten.items():
                        fragenmanager.antwort_hinzufuegen(
                            frage_id=strukturierte_frage.frage_id,
                            thema_composite_key=antwort_thema,
                            thema_name=themenkontext.parent_thema_text,
                            option_key=antwort_option,
                        )
                chatverlaeufe.append(
                    LLMChatverlauf(
                        name=f"chatverlauf-{kontext_key}",
                        chatverlauf=out.get("messages", []),
                    ),
                )

        siliconsamples = SiliconSamples(
            zusammenfassungen=self.zusammenfassungen,
            fragen=fragenmanager.fragen,
            antworten=copy.deepcopy(fragenmanager.antworten),
            prompt=self.prompt,
            llm=LLM(
                konfiguration=self.llm_config_holen(),
                tokenverbrauch=self.llm_tokenverbrauch(),
                chatverlaeufe=chatverlaeufe,
            ),
        )

        # Reset für nächsten Stichproben-Lauf
        log.info(f"Antworten im Fragenmanager resetten")
        fragenmanager.reset_antworten()

        return siliconsamples


def node_definiere_aktuellen_kontext(state):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")
    # Aktuellen Kontext-Key von aktueller Frage definieren
    frage = state["frage"]
    kontext = state["kontext"]
    result = {"aktueller_kontext_key": f"{frage.frage_id}-{kontext.parent_thema_key}"}
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result


def pruefe_kontextwechsel(state):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")
    # Kontexte vergleichen
    aktueller_kontext_key = state["aktueller_kontext_key"]
    letzter_kontext_key = state["letzter_kontext_key"]
    result = letzter_kontext_key != aktueller_kontext_key
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result


def node_definiere_kontextwechsel(state):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")
    result = {"kontextwechsel": True, "antworten": {}}
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result


def node_historie_loeschen(state):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")
    result = {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result


def node_fragenintro_generieren(state, config=None):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")
    zusammenfassungen: list[Zusammenfassung] = state.get("zusammenfassungen", [])

    fragenintro_teile: list[str] = []

    personas_nutzen: bool = hole_prompt_data_aus_graph("personas_nutzen", config)

    if personas_nutzen:
        aktuelle_persona: dict[str, str] = hole_prompt_data_aus_graph(
            "aktuelle_persona", config
        )
        # {'index': 0, 'Geschlecht': 'weiblich/männlich', 'Altersgruppe': '15-24', 'Region': 'Nielsen 1', 'Urban': 'Ja/Nein'}

        if not zusammenfassungen:
            prompt_intro = hole_prompt_aus_graph(
                prompt_name="fragen_intro_mit_persona_ohne_referenzen",
                config=config,
                prompt_data=aktuelle_persona,
            )
        else:
            prompt_intro = hole_prompt_aus_graph(
                "fragen_intro_mit_persona_mit_referenzen",
                config=config,
                prompt_data=aktuelle_persona,
            )
    else:
        if not zusammenfassungen:
            prompt_intro = hole_prompt_aus_graph(
                prompt_name="fragen_intro_ohne_persona_ohne_referenzen",
                config=config,
            )
        else:
            prompt_intro = hole_prompt_aus_graph(
                "fragen_intro_ohne_persona_mit_referenzen",
                config=config,
            )

    fragenintro_teile.append(prompt_intro)

    texte = [z.text_zusammengefasst for z in zusammenfassungen]

    tabellen = []
    for zusammenfassung in zusammenfassungen:
        if not zusammenfassung.tabellen_zusammengefasst:
            if not zusammenfassung.tabellen_extrahiert:
                continue
            else:
                for tabelle_extrahiert in zusammenfassung.tabellen_extrahiert:
                    tabellen.append(tabelle_extrahiert)

        else:
            for tabelle_zusammengefasst in zusammenfassung.tabellen_zusammengefasst:
                tabellen.append(tabelle_zusammengefasst)

    if texte:
        fragenintro_teile.append("\nTexte:")
        for wert in texte:
            fragenintro_teile.append(f"\n{wert}")

    if tabellen:
        fragenintro_teile.append("\nTabellen:")
        for wert in tabellen:
            fragenintro_teile.append(f"\n{wert}")

    fragenintro: SystemMessage = SystemMessage(content="\n".join(fragenintro_teile))

    result = {"messages": fragenintro}
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result


def node_frage_generieren(state):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")

    # Aktuelle Frage aus State holen
    frage = state["frage"]

    # Aktuellen Kontext aus State
    kontext = state["kontext"]

    # Gerenderten Text pro Kontext ausgeben
    frage_teile = []
    frage_teile.append(f"Frage: {kontext.text_gerendert}")

    # Themen hinzufügen
    if frage.themenkontexte:
        frage_teile.append("\nAussagen:")
        for k in frage.themenkontexte:
            if k.text_gerendert != kontext.text_gerendert:
                continue
            frage_teile.append(f"{k.composite_key}: {k.child_thema_text}")

    # Optionen (identisch für alle Kontexte)
    if frage.antwortoptionen:
        frage_teile.append("\nAntwortoptionen:")
        for opt in frage.antwortoptionen:
            frage_teile.append(f"{opt.id} ({opt.text})")

    frage: HumanMessage = HumanMessage(content="\n".join(frage_teile))
    result = {"messages": frage}
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result


def node_frage_stellen(state, config):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")
    # Historie aus State holen
    messages = state["messages"]
    response: AIMessage = hole_llm_instanz_aus_graph(config).invoke(messages)
    result = {"messages": [response]}
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result


def node_antwort_validieren(
    state, config
) -> Command[Literal["node_frage_stellen", "node_aktualisiere_letzten_kontext"]]:
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")

    def llm_antwort_parsen(llm_antwort: str) -> dict[str, str]:
        pairs: dict[str, str] = {}
        for raw in llm_antwort.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"Ungültige Zeile (kein ':'): {raw}")

            left, right = line.rsplit(":", 1)  # <<< letzter Doppelpunkt
            k, v = left.strip(), right.strip()
            if not k or not v:
                raise ValueError(f"Ungültige Zeile (leer nach Trim): {raw}")

            # Falls du keine Spaces im Value erlauben willst:
            # if re.search(r"\s", v):
            #     raise ValueError(f"Antwort-Key enthält Whitespace: {v!r}")

            pairs[k] = v
        return pairs

    # Aktuelle Frage aus State holen
    frage = state["frage"]

    # Aktuellen Kontext aus State
    kontext = state["kontext"]

    # Aktuelle Antwort aus State holen
    llm_ai_message: AIMessage = state["messages"][-1]
    llm_antwort: AIMessage = parse_llm_content(llm_ai_message, config)

    log.info(llm_antwort)

    antworten: dict[str, str] = state.get("antworten", {})

    try:
        notwendige_keys = {
            k.composite_key
            for k in frage.themenkontexte
            if k.text_gerendert == kontext.text_gerendert
        }

        # erlaubte Values als Set
        erlaubte_values = {opt.id for opt in frage.antwortoptionen}

        # Stand vor dem Update merken (für "neu dazugekommen")
        vorhandene_keys_vorher = [k for k in antworten.keys()]

        antworten_neu = llm_antwort_parsen(llm_antwort)
        antworten_neu_keys = set(antworten_neu.keys())

        # ungültige Keys (aus der neuen LLM-Antwort)
        ungueltige_keys = antworten_neu_keys - notwendige_keys

        # ungültige Values (nur für gültige Keys prüfen)
        ungueltige_values_keys = {
            k
            for k, v in antworten_neu.items()
            if k in notwendige_keys and v not in erlaubte_values
        }

        # gültige Keys (aus der neuen LLM-Antwort)
        gueltige_keys = antworten_neu_keys & notwendige_keys

        # nur gültige Einträge übernehmen: Key gültig UND Value erlaubt
        antworten_neu_gueltig = {
            k: v
            for k, v in antworten_neu.items()
            if k in notwendige_keys and v in erlaubte_values
        }
        antworten.update(antworten_neu_gueltig)

        # Stand nach dem Update: welche notwendigen Keys sind insgesamt schon beantwortet?
        vorhandene_gueltige_keys_gesamt = set(antworten.keys()) & notwendige_keys

        # fehlende Keys (bezogen auf alle Antworten bisher)
        fehlende_keys = notwendige_keys - vorhandene_gueltige_keys_gesamt

        if ungueltige_keys or fehlende_keys or ungueltige_values_keys:
            fehlernachricht = []
            fehlernachricht.append(
                "Deine Antwort ist nicht gültig. Bitte nochmal antworten. Beachte die Regeln.\n\n"
            )
            fehlernachricht.append(
                f"Vor deiner Antwort waren folgende Nummern gespeichert: {", ".join((v for v in vorhandene_keys_vorher))}"
            )
            fehlernachricht.append(
                f"Deine Antwort beinhaltete folgende gültige Nummern: {", ".join((v for v in gueltige_keys))}"
            )
            fehlernachricht.append(
                f"Deine Antwort beinhaltete folgende ungültige Nummern: {", ".join((v for v in ungueltige_keys))}"
            )
            fehlernachricht.append(
                f"Deine Antwort beinhaltete ungültige Antworten zu folgenden Nummern: {", ".join((v for v in ungueltige_values_keys))}"
            )
            fehlernachricht.append(
                f"Nach deiner Antwort waren folgende Nummern gespeichert: {", ".join((v for v in vorhandene_gueltige_keys_gesamt))}"
            )
            fehlernachricht.append(
                f"Folgende Nummern der Fragen/Aussagen fehlen insgesamt noch: {", ".join((v for v in fehlende_keys))}"
            )
            raise ValueError("\n".join(fehlernachricht))

        log.info(
            f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(antworten)}"
        )

        return Command(
            update={"antworten": antworten}, goto="node_aktualisiere_letzten_kontext"
        )

    except ValueError as e:

        log.debug(f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(e)}")
        return Command(
            update={"messages": [HumanMessage(content=str(e))]},
            goto="node_frage_stellen",
        )


def node_aktualisiere_letzten_kontext(state):
    log.info(f"LangGraph Node {inspect.stack()[0][3]} gestartet")
    # Letzten Kontext-Key mit aktuellen Kontext-Key definieren
    aktueller_kontext_key = state["aktueller_kontext_key"]
    result = {"letzter_kontext_key": aktueller_kontext_key}
    log.debug(
        f"LangGraph Node {inspect.stack()[0][3]} beendet, Ergebnis: {str(result)}"
    )
    return result
