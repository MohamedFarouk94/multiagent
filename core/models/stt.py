import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def transcribe_audio(file_path: str, model: str = "gpt-4o-mini-transcribe") -> str:
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=model,
            file=audio_file
        )

    return transcription.text


if __name__ == "__main__":
    # print("KEY:", os.getenv("OPENAI_API_KEY"))

    text = transcribe_audio("samples/input.wav")
    print(text)
