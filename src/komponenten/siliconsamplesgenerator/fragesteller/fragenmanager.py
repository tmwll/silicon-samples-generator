import random
from typing import Optional
from src.komponenten.siliconsamplesgenerator.fragesteller.fragestellerfehler import (
    FragestellerFehler,
)
from src.komponenten.siliconsamplesgenerator.siliconsamplesgenerator_models import (
    Antwort,
    AntwortThemaOption,
    StrukturierteFrage,
    ThemenKontext,
)
from src.komponenten.studienkonfiguration.studienkonfigurationslader.models import (
    Frage,
    Option,
)
from src.komponenten.studienkonfiguration.studienkonfigurationslader.utils import (
    render_text,
)

from src.shared.logger import get_logger

log = get_logger(__name__)


class Fragenmanager:

    fragen: dict[str, Frage] = {}
    antworten: dict[str, Antwort] = {}

    def __init__(self, fragen: list[Frage]):
        self.fragen = {f.id: f for f in fragen}
        self._parent_themen_cache: dict[tuple, list[str]] = {}

    def reset_antworten(self):
        self.antworten.clear()
        self._parent_themen_cache.clear()

    def naechste_frage(self) -> Optional[StrukturierteFrage]:
        """Ermittelt die *nächste* offene Frage/Teilfrage.

        Gibt None zurück, wenn alles vollständig beantwortet ist.
        """
        for f_id, frage in self.fragen.items():

            # Falls Abhängigkeit nicht erfüllt → Frage überspringen
            if not self._frage_darf_gestellt_werden(frage.id):
                log.info(f"Frage darf noch nicht gestellt werden: {frage.id}")
                continue

            # Wenn bereits vollständig → weiter
            if self._frage_ist_komplett_beantwortet(frage.id):
                log.info(f"Frage ist bereits beantwortet: {frage.id}")
                continue

            # Es gibt noch offene Teilfragen → bestimme die *nächste* Einheit
            return self._baue_strukturierte_frage(frage)

        return None

    def antwort_hinzufuegen(
        self,
        frage_id: str,
        thema_composite_key: Optional[str],
        thema_name: Optional[str],
        option_key: str,
    ):
        """Bequeme Möglichkeit, eine Auswahl hinzuzufügen/zu aktualisieren.

        - Aggregiert Antworten pro Frage.
        - Ersetzt vorhandene Auswahl für denselben themen_composite_key.
        """
        log.info(
            f"Antwort für Frage {frage_id} hinzufügen, Thema: {thema_composite_key}, Option: {option_key}"
        )

        antwort = self.antworten.get(frage_id)
        neue_antwort = AntwortThemaOption(
            thema_key=thema_composite_key, thema_name=thema_name, option_key=option_key
        )
        if not antwort:
            self.antworten[frage_id] = Antwort(
                frage_id=frage_id, auswahl=(neue_antwort,)
            )
        else:
            rest = [a for a in antwort.auswahl if a.thema_key != thema_composite_key]
            rest.append(neue_antwort)
            self.antworten[frage_id] = Antwort(frage_id=frage_id, auswahl=tuple(rest))

    # ---- Interne Hilfen -------------------------------------------------

    def _frage_darf_gestellt_werden(self, frage_id) -> bool:
        log.info(f"Prüfung ob {frage_id} gestellt werden darf")

        frage = self.fragen.get(frage_id)

        if not frage:
            raise FragestellerFehler(f"Frage nicht vorhanden: {frage_id}")

        # Hat keine übergeordnete Frage, dann darf immer gefragt werden
        if not frage.hat_uebergeordnete_frage:
            log.info(f"Frage hat keine übergeordnete Frage, darf gestellt werden")
            return True

        # Hat übergeorndete Frage...
        else:
            log.info(f"Frage hat übergeordnete Frage...")

            # und keine übergeordnete Antwortoption, dann darf gefragt werden
            if not frage.hat_uebergeordnete_antwortoption:
                log.info(
                    f"... und keine übergeordnete Antwortoption, darf gestellt werden"
                )
                return True

            # und die Antwort ist schon vorhanden...
            uebergeordnete_frage_antwort = self.antworten.get(
                frage.uebergeordnete_frage_id
            )
            if uebergeordnete_frage_antwort:
                # prüfen ob zu irgendeinem Thema die übergeordnete Antwortoption gegeben wurde
                result = any(
                    a.option_key == frage.uebergeordnete_antwortoption_id
                    for a in uebergeordnete_frage_antwort.auswahl
                )
                log.info(
                    f"... und Antwort vorhanden. Prüfung ob notwendige Antwortoption in übergeordneter Frage beantwortet wurde. Ergebnis: {result}"
                )
                return result
            # Antwort nicht vorhanden
            else:
                log.info(f"... und Antwort nicht vorhanden. Ergebnis: False")
                return False

    def _frage_ist_komplett_beantwortet(self, frage_id) -> bool:
        log.info(f"Prüfung ob Frage {frage_id} komplett beantwortet wurde")

        frage = self.fragen.get(frage_id)

        if not frage:
            raise FragestellerFehler(f"Frage nicht vorhanden: {frage_id}")

        aktuelle_antworten = self.antworten.get(frage_id)
        if not aktuelle_antworten:
            return False

        gewaehlte_keys = {a.thema_key for a in aktuelle_antworten.auswahl}

        uebergeordnete_frage = self.fragen.get(frage.uebergeordnete_frage_id)
        uebergeordnete_antwortoption = frage.uebergeordnete_antwortoption_id

        # Fall A: Parent mit Themen → Wiederholung pro relevantem Eltern-Thema
        if uebergeordnete_frage and uebergeordnete_frage.themen:
            uebergeordnete_frage_antwort = self.antworten.get(uebergeordnete_frage.id)
            if not uebergeordnete_frage_antwort:
                return False

            relevante_parent_themen = self._parent_themen_fuer_folgefrage(
                frage, uebergeordnete_frage, uebergeordnete_frage_antwort
            )

            if not relevante_parent_themen:
                return True  # nichts zu tun

            if frage.themen:
                # Jede Kombi parent_thema x child_thema muss vorhanden sein
                erwartete = {
                    self._compose_key(uebergeordnete_frage.id, ptk, ct.id)
                    for ptk in relevante_parent_themen
                    for ct in frage.themen
                }
            else:
                erwartete = {
                    self._compose_key(uebergeordnete_frage.id, ptk, None)
                    for ptk in relevante_parent_themen
                }
            return erwartete.issubset(gewaehlte_keys)

        # Fall B: Kein Parent-Thema-Loop
        if frage.themen:
            erwartete = {t.id for t in frage.themen}
            return erwartete.issubset(gewaehlte_keys)
        else:
            # genau eine Auswahl erforderlich
            return len(gewaehlte_keys) >= 1

    def _baue_strukturierte_frage(self, frage: Frage) -> StrukturierteFrage:
        parent_id = frage.uebergeordnete_frage_id
        required_opt = frage.uebergeordnete_antwortoption_id
        parent = self.fragen.get(parent_id) if parent_id else None

        bereits = self.antworten.get(frage.id)
        bereits_keys = {a.thema_key for a in (bereits.auswahl if bereits else ())}

        kontexte: list[ThemenKontext] = []

        # A) Parent mit Themen → alle fehlenden Kombinationen sammeln
        if parent and parent.themen:
            parent_ans = self.antworten.get(parent.id)
            relevante_parent_themen = self._parent_themen_fuer_folgefrage(
                frage, parent, parent_ans
            )

            for ptk in relevante_parent_themen:
                parent_text = parent.thema_text(ptk) or ptk
                if frage.themen:
                    for ct in frage.themen:
                        comp = self._compose_key(parent.id, ptk, ct.id)
                        if comp not in bereits_keys:
                            kontexte.append(
                                ThemenKontext(
                                    composite_key=comp,
                                    parent_frage_id=parent.id,
                                    parent_thema_key=ptk,
                                    parent_thema_text=parent_text,
                                    child_thema_key=ct.id,
                                    child_thema_text=ct.text,
                                    text_gerendert=render_text(
                                        frage.text,
                                        thema_prev=parent_text,
                                        thema=ct.text,
                                    ),
                                )
                            )
                else:
                    comp = self._compose_key(parent.id, ptk, None)
                    if comp not in bereits_keys:
                        kontexte.append(
                            ThemenKontext(
                                composite_key=comp,
                                parent_frage_id=parent.id,
                                parent_thema_key=ptk,
                                parent_thema_text=parent_text,
                                child_thema_key=None,
                                child_thema_text=None,
                                text_gerendert=render_text(
                                    frage.text, thema_prev=parent_text
                                ),
                            )
                        )

        # B) Kein Parent-Thema-Loop → alle fehlenden Child-Themen sammeln
        elif frage.themen:
            for t in frage.themen:
                if t.id not in bereits_keys:
                    kontexte.append(
                        ThemenKontext(
                            composite_key=t.id,
                            parent_frage_id=None,
                            parent_thema_key=None,
                            parent_thema_text=None,
                            child_thema_key=t.id,
                            child_thema_text=t.text,
                            text_gerendert=render_text(frage.text, thema=t.text),
                        )
                    )

        # C) Frage ohne Themen → ein „leer“-Kontext, falls noch unbeantwortet
        else:
            if not bereits_keys:
                kontexte.append(
                    ThemenKontext(
                        composite_key=None,  # kein Thema → kein Child-Key
                        parent_frage_id=None,
                        parent_thema_key=None,
                        parent_thema_text=None,
                        child_thema_key=None,
                        child_thema_text=None,
                        text_gerendert=render_text(frage.text),
                    )
                )

        # Optionen sind identisch für alle Kontexte
        # Nutze die Basisoptionen ohne spezielles Thema:
        optionen: tuple[Option, ...] = tuple(frage.optionen_fuer(None))

        return StrukturierteFrage(
            frage_id=frage.id,
            themenkontexte=tuple(kontexte),
            antwortoptionen=optionen,
            rohe_frage=frage,
        )

    def _compose_key(
        self,
        parent_frage_id: str,
        parent_thema_key: str,
        child_thema_key: Optional[str],
    ) -> str:
        DELIM = "::"
        if child_thema_key:
            return f"{parent_frage_id}{DELIM}{parent_thema_key}{DELIM}{child_thema_key}"
        return f"{parent_frage_id}{DELIM}{parent_thema_key}"

    def _parent_themen_fuer_folgefrage(
        self, frage: Frage, parent: Frage, parent_ans: Optional[Antwort]
    ) -> list[str]:
        required_opt = frage.uebergeordnete_antwortoption_id
        relevante = self._relevante_parent_themen(parent, parent_ans, required_opt)
        if not relevante:
            return []

        limit = getattr(frage, "uebergeordnete_themen_limit", None)
        zufaellig = bool(getattr(frage, "uebergeordnete_themen_zufaellig", False))

        # Wenn kein Limit oder nicht zufällig, dann sind alle relevant
        if limit is None and not zufaellig:
            return relevante

        # Cache speichert zufällige Themen, damit bei "nächster Frage" nicht wieder zufällig neue Werte generiert werden
        cache_key = (frage.id, parent.id, required_opt or "", limit, zufaellig)
        cached = self._parent_themen_cache.get(cache_key)
        if cached is not None:
            return cached

        # Kein Cache dann weiter

        # Shuffle “beibehalten”: sample(k=len) gibt eine zufällige Permutation
        permutation = (
            random.Random().sample(relevante, k=len(relevante))
            if zufaellig
            else list(relevante)
        )
        if limit is not None:
            permutation = permutation[:limit]

        self._parent_themen_cache[cache_key] = permutation
        return permutation

    def _relevante_parent_themen(
        self, parent: Frage, parent_ans: Optional[Antwort], required_opt: Optional[str]
    ) -> list[str]:
        if not parent_ans:
            return []
        if not parent.themen:
            # Eltern hat keine Themen → keine Wiederholung, bleibt leer
            return []

        # 1) Welche parent-thema-keys sind überhaupt "relevant" (gefiltert nach required_opt)?
        if required_opt is None:
            # Wenn keine geforderte Option → alle Themen, die beantwortet wurden
            relevante_keys = {
                a.thema_key for a in parent_ans.auswahl if a.thema_key is not None
            }
        else:
            # Filtere Eltern-Themen nach der geforderten Option
            relevante_keys = {
                a.thema_key
                for a in parent_ans.auswahl
                if a.option_key == required_opt and a.thema_key is not None
            }
        # 2) NICHT sortieren: Reihenfolge wie parent.themen (XML-Reihenfolge)
        return [t.id for t in parent.themen if t.id in relevante_keys]
