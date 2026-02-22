import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def synthesize_speech(text: str, voice: str = "alloy"):
    """
    Converts text to speech using OpenAI TTS (gpt-4o-mini-tts)
    """
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )

    return response.read()

