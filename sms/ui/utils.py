"""Small parsing helpers for form input. They raise ValueError with a friendly message."""


def to_int(text: str, label: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"{label} must be a whole number.") from None


def to_float(text: str, label: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{label} must be a number.") from None


def fmt(value: float) -> str:
    """12.0 -> '12', 7.5 -> '7.5'."""
    return f"{value:g}"
