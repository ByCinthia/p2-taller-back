import os

import openai


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file using OpenAI Speech-to-Text.

    Model: gpt-4o-mini-transcribe
    Language: Spanish (es)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    openai.api_key = api_key

    try:
        with open(file_path, "rb") as fh:
            # The OpenAI python client exposes an Audio.transcribe helper in recent versions
            resp = openai.Audio.transcribe("gpt-4o-mini-transcribe", fh, language="es")
    except Exception as exc:
        raise

    # Try common response keys
    text = None
    if isinstance(resp, dict):
        text = resp.get("text") or resp.get("transcript")
    if not text:
        try:
            text = str(resp)
        except Exception:
            text = ""

    return text or ""
