"""Text truncation utilities."""


def truncate_head_tail(text: str, max_chars: int, tail_chars: int = 0) -> str:
    """Truncate text preserving both head and tail.

    When tail_chars > 0, ensures the last tail_chars of the original text
    are always visible. Useful for tool results where paths, URLs, and
    final output appear at the end.

    Minimum output structure: head(1) + "..."(3) + tail(1) = 5 chars.
    Falls back to head-only truncation when max_chars < 5.

    Example: truncate_head_tail("abcdefghij", 8, tail_chars=3)
    => "ab...hij"  (head=2 + "..." + tail=3, total=8)
    """
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    if tail_chars <= 0:
        return text[:max_chars] + f"...[truncated, {len(text)} total chars]"
    # Need at least 5 chars for head(1) + "..."(3) + tail(1)
    if max_chars < 5:
        return text[:max_chars] + "..."
    # Clamp tail_chars: must leave room for head(1) + "..."(3)
    tail_chars = min(tail_chars, max_chars - 4)
    head_limit = max_chars - tail_chars - 3  # 3 for "..."
    head = text[:head_limit]
    tail = text[-tail_chars:]
    return f"{head}...{tail}"
