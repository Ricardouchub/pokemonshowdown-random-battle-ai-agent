import re

def to_id(text: str) -> str:
    """Canonicalize text to Showdown ID format (lowercase, alphanumeric only)."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())
