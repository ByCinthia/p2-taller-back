import os

from openai import OpenAI


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file using OpenAI Speech-to-Text.

    Model: gpt-4o-mini-transcribe
    Language: Spanish (es)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)

    with open(file_path, "rb") as fh:
        resp = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=fh,
            language="es",
        )
        return resp.text or ""
