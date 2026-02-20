from typing import Dict

from models import Message
from .core.chains import text_chain, audio_chain
from history_manager import retrieve_messages_for_llm


# -------------------------------------------------------
# Prepare data for chain invocation
# -------------------------------------------------------

def prepare_data(message: Message) -> Dict:
    """
    Prepares input dictionary for either text_chain or audio_chain.
    """

    chat = message.chat
    agent = chat.agent
    user = agent.user

    data = {
        "agent_name": agent.name,
        "system_prompt": agent.system_prompt,
        "history": retrieve_messages_for_llm(chat),
        "user_text": message.text,
        "is_audio": message.is_audio,
        "user_audio": ""
    }

    # Only attach audio filename if message is audio
    if message.is_audio:
        data["user_audio"] = f"user_{user.username}_{message.id}"

    return data


# -------------------------------------------------------
# Run appropriate chain
# -------------------------------------------------------

def run_chain(data: Dict) -> Dict:
    """
    Routes request to audio_chain or text_chain based on `is_audio`.
    Returns the chain output dictionary.
    """

    if data["is_audio"]:
        return audio_chain.invoke(data)

    return text_chain.invoke(data)
