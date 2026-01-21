def natural_sort_key(col):
    try:
        return (0, int(col))
    except (ValueError, TypeError):
        return (1, str(col))


def split_last_dcolon(s: str) -> tuple[str, str]:
    return tuple(s.rsplit("::", 1)) if "::" in s else (s, "")
