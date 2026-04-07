"""Token counting utilities using tiktoken.

Accurate token counting for OpenAI-compatible models.
Falls back to character-based estimation for unsupported models.
"""

from typing import Optional

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False

# Cache encodings to avoid repeated initialization
_encodings: dict[str, object] = {}


def _get_encoding(model: str = "cl100k_base") -> object:
    """Get tiktoken encoding, with caching."""
    if model not in _encodings:
        try:
            _encodings[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            _encodings[model] = tiktoken.get_encoding("cl100k_base")
    return _encodings[model]


def estimate_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens using tiktoken (accurate for OpenAI models).

    For non-OpenAI models, cl100k_base is a reasonable approximation.
    """
    if not text:
        return 0

    if _HAS_TIKTOKEN:
        try:
            enc = _get_encoding(model)
            return len(enc.encode(text))
        except Exception:
            pass

    # Fallback: rough char-based estimate (~4 chars per token)
    return len(text) // 4


def estimate_messages_tokens(messages: list[dict], model: str = "cl100k_base") -> int:
    """Estimate total tokens for a list of messages.

    Includes message formatting overhead (role markers, separators).
    """
    total = 0
    for msg in messages:
        total += 4  # role + formatting overhead per message

        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content, model)
        elif isinstance(content, list):
            # Multimodal content parts
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        total += estimate_tokens(part.get("text", ""), model)
                    elif part.get("type") == "image_url":
                        total += 300  # Average image token cost

        # Tool calls
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                func = tc.get("function", {})
                total += 10  # Tool call overhead
                total += estimate_tokens(func.get("name", ""), model)
                total += estimate_tokens(func.get("arguments", ""), model)

        # Tool result overhead
        if msg.get("role") == "tool":
            total += 5

    # Message-to-message formatting overhead
    total += len(messages) * 3
    return total


def split_messages_by_tokens(
    messages: list[dict],
    target_tokens: int,
    model: str = "cl100k_base",
) -> tuple[list[dict], list[dict]]:
    """Split messages: keep recent ones within target_tokens budget.

    Returns (older_messages, recent_messages).
    """
    if not messages:
        return [], []

    recent_tokens = 0
    split_idx = len(messages)

    for i in range(len(messages) - 1, -1, -1):
        msg_tokens = estimate_messages_tokens([messages[i]], model)
        if recent_tokens + msg_tokens > target_tokens:
            split_idx = i + 1
            break
        recent_tokens += msg_tokens

    if split_idx >= len(messages):
        return messages, []
    if split_idx <= 0:
        return [], messages

    return messages[:split_idx], messages[split_idx:]
