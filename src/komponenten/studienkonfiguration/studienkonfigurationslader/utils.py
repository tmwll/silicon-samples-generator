# utils.py
import re
from typing import Any, Optional

def stripped_oder_none(string: Optional[str]) -> Optional[str]:
    string = (string or "").strip()
    return string or None

def render_text(text: Optional[str], **ctx: Any) -> str:
    """Ersetzt {{placeholders}} im Text. Fehlende Keys bleiben unverändert."""

    pattern = re.compile(r"\{\{(\w+)\}\}")  # matcht {{thema}}, {{thema_prev}}, ...
    s = text or ""
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))  # unbekannte Keys unverändert lassen
    
    return pattern.sub(repl, s)