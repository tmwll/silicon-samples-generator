from src.shared.komponenten import KomponentenAPI

from src.shared.logger import get_logger

log = get_logger(__name__)


class StartseiteAPI(KomponentenAPI):

    def __init__(self):
        super().__init__("startseite")
