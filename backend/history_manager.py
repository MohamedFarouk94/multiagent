from typing import List, Dict
from .models import Chat


# -------------------------------------------------------
# Retrieve messages formatted for LLM
# -------------------------------------------------------

def retrieve_messages_for_llm(chat: Chat, n: int = 10) -> List[dict]:
    """
    Returns the last n messages formatted for LLM consumption.
    Output format:
    [
        {"role": "user" | "assistant", "content": "..."},
        ...
    ]
    """

    # Sort messages by time (ascending)
    messages = sorted(chat.messages, key=lambda m: m.sent_at)

    # Take last n
    last_messages = messages[-n:]

    llm_history = [
        {
            "role": "assistant" if msg.is_agent else "user",
            "content": msg.text
        }
        for msg in last_messages
    ]

    return llm_history


# -------------------------------------------------------
# Retrieve messages formatted for user (pagination-like)
# -------------------------------------------------------

def retrieve_messages_for_user(
    chat: Chat,
    start_index: int = -1,
    n: int = 10
) -> List[Dict]:
    """
    Retrieves n messages starting from a negative index and going backwards.

    Example:
        start_index = -1  -> last message
        start_index = -5  -> 5th message from the end

    Returns list of dicts:
    {
        "id": int,
        "sent_at": datetime,
        "sender": "user" | "agent",
        "is_audio": bool,
        "text": str (empty if audio)
    }
    """

    messages = sorted(chat.messages, key=lambda m: m.sent_at)

    if not messages:
        return []

    # Resolve negative index safely
    start = len(messages) + start_index if start_index < 0 else start_index

    if start < 0:
        return []
    if start >= len(messages):
        return []

    # Slice backwards
    end = max(start - n + 1, 0)
    selected = messages[end:start + 1]

    # Keep chronological order
    selected = sorted(selected, key=lambda m: m.sent_at)

    return [
        {
            "id": msg.id,
            "sent_at": msg.sent_at,
            "sender": "agent" if msg.is_agent else "user",
            "is_audio": msg.is_audio,
            "text": "" if msg.is_audio else msg.text
        }
        for msg in selected
    ]
