"""
transcriber.py - Step 2: turn a voice recording into text with Gemini.

The audio file is sent from this Python server to Google's Gemini API,
and Gemini sends back the words it heard.
"""

from pathlib import Path

from google import genai
from google.genai import errors, types

import config

TRANSCRIBE_PROMPT = (
    "Transcribe this voice note word for word, in the language it is spoken. "
    "Return only the transcript with normal punctuation - no comments, no headings. "
    "If there is no understandable speech, return exactly: [no speech detected]"
)
NO_SPEECH_MARKER = "[no speech detected]"

AUDIO_TYPES = {".wav": "audio/wav", ".mp3": "audio/mp3", ".m4a": "audio/mp4",
               ".ogg": "audio/ogg", ".flac": "audio/flac", ".webm": "audio/webm"}


class TranscriptionError(Exception):
    """A problem we can explain to the user in plain words."""


def make_client():
    """Create a Gemini client using the key from .env."""
    return genai.Client(api_key=config.get_api_key())


def friendly_error(error):
    """Turn a technical Gemini error into a message a beginner can act on."""
    code = getattr(error, "code", None)
    message = str(getattr(error, "message", "") or error)
    if code == 400 and "api key" in message.lower():
        return "Gemini rejected the API key. Run  python setup_key.py  and paste a fresh key."
    if code in (401, 403):
        return "Gemini refused access with this API key. Run  python setup_key.py  and paste a fresh key."
    if code == 404:
        return (f"Gemini model '{config.get_model()}' was not found. "
                "Run  python check_setup.py  to see which models your key can use.")
    if code == 429:
        return "Gemini's free usage limit was reached. Wait a minute and try again."
    if code is not None and code >= 500:
        return "Gemini is busy or having problems right now. Try again in a moment."
    return f"Gemini error ({code}): {message}"


def transcribe(audio_path, client=None, model=None):
    """
    Return the text spoken in the audio file ("" if no speech was heard).

    `client` and `model` can be passed in by tests; normally leave them out.
    """
    path = Path(audio_path)
    if not path.exists():
        raise TranscriptionError(f"Recording not found: {path.name}")

    mime_type = AUDIO_TYPES.get(path.suffix.lower(), "audio/wav")
    client = client or make_client()
    model = model or config.get_model()

    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                TRANSCRIBE_PROMPT,
                types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type),
            ],
        )
    except errors.APIError as error:
        raise TranscriptionError(friendly_error(error)) from error
    except Exception as error:  # usually: no internet connection
        raise TranscriptionError(
            f"Could not reach Gemini. Check your internet connection. ({type(error).__name__}: {error})"
        ) from error

    text = (response.text or "").strip()
    if text == NO_SPEECH_MARKER:
        return ""
    return text
