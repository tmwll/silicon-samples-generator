import tomllib
from pathlib import Path
from typing import Any, Dict

from src.shared.logger import get_logger

log = get_logger(__name__)


class TOMLConfig:
    def __init__(self, config_file: str | Path = "config.toml"):
        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = {}

        # Hauptconfig laden (ohne Namespace → direkt oben in self.config)
        self.load_config(self.config_file)

    def load_config(
        self,
        config_file: str | Path,
        *,
        namespace: str | None = None,
        target: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Lädt eine TOML-Datei und merged sie in 'target' (Standard: self.config).

        - ohne namespace: top-level Keys werden in target.update(...)
        - mit namespace: Inhalt wird unter target[ns1][ns2]...[letzter] = data gehängt
        """
        config_file = Path(config_file)
        try:
            with config_file.open("rb") as f:
                data = tomllib.load(f)
        except FileNotFoundError:
            log.info(f"Konfigurationsdatei '{config_file}' nicht vorhanden")
            data = {}
        except tomllib.TOMLDecodeError as e:
            print(f"Fehler beim Parsen der Konfigurationsdatei '{config_file}': {e}")
            raise

        if target is None:
            target = self.config

        if namespace is None:
            # Direkt oben in target mergen
            target.update(data)
            return target

        # Namespace "a.b.c" → target["a"]["b"]["c"] = data
        parts = namespace.split(".")
        current: Dict[str, Any] = target
        for part in parts[:-1]:
            current = current.setdefault(part, {})

        current[parts[-1]] = data
        self.config = target

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_section(self, section):
        if section not in self.config:
            raise ValueError(f"Section '{section}' not found")
        return self.config[section]
