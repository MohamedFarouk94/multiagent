import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def synthesize_speech(text: str, voice: str = "alloy", output_file: str = "backend/media/output.mp3"):
    """
    Converts text to speech using OpenAI TTS (gpt-4o-mini-tts)
    """
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )

    # Save the audio directly from response
    audio_bytes = response.read()
    with open(output_file, "wb") as f:
        f.write(audio_bytes)  # response is raw binary content

    return output_file


# Example usage
if __name__ == "__main__":
    file_path = synthesize_speech("What is the capital of France?")
    print("Saved speech to:", file_path)
