from typing import Any

def normalize(value: Any) -> Any:
    try:
        if hasattr(value, "quantize"):
            return str(value)
        return str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
    except Exception:
        return str(value)


def normalize_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    return {k: normalize(v) for k, v in ctx.items()}
