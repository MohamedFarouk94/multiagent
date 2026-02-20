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


# Example usage
if __name__ == "__main__":
    audio_bytes = synthesize_speech("What is the capital of France?")
    output_file: str = "backend/media/output.mp3"
    with open(output_file, "wb") as f:
        f.write(audio_bytes)  # response is raw binary content
    print("Saved speech to:", output_file)

