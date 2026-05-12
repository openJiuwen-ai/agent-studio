from typing import Optional

SSE_FIELD_PREFIXES = ("data:", "event:", "id:", "retry:", ":")


def normalize_relay_stream_line(line: str, search_mode: Optional[str]) -> str:
    """Normalize relayed DeepSearch stream lines for frontend SSE consumption."""
    if search_mode != "search":
        return line

    stripped = line.strip()
    if not stripped:
        return ""

    if stripped.startswith(SSE_FIELD_PREFIXES):
        return stripped

    return f"data: {stripped}"
