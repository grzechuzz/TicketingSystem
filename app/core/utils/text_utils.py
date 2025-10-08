def strip_text(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip()
    return value or None
