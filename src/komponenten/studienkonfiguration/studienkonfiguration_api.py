from src.komponenten.studienkonfiguration.studienkonfigurationslader.studienkonfigurationslader import (
    Studienkonfigurationslader,
)
from src.shared.dateien import erstelle_dateipfad
from src.shared.komponenten import KomponentenAPI

from src.shared.logger import get_logger

log = get_logger(__name__)


class StudienkonfigurationAPI(KomponentenAPI):

    def __init__(self):
        super().__init__("studienkonfiguration")

        self.ordner: str = self.config["speicherort"]["ordner"]
        self.datei: str = self.config["speicherort"]["datei"]
        self.dateipfad = erstelle_dateipfad(self.ordner, self.datei)

    def studienkonfiguration(self, dateipfad):
        studienkonfigurationslader = Studienkonfigurationslader(dateipfad)
        log.info(f"Studienkonfiguraton {dateipfad} geladen")
        return studienkonfigurationslader
