from openai import OpenAI
from utils.config import OPENAI_API_KEY


def transcribe_audio(audio_file_path: str) -> str:
    if not OPENAI_API_KEY:
        return "Voice transcription is unavailable because OPENAI_API_KEY is missing."

    if not audio_file_path:
        return "No audio file provided."

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file
            )
        return getattr(transcript, "text", "").strip() or "No transcription text returned."
    except Exception as exc:
        return f"Transcription failed: {exc}"
