"""
Tests for Step 2. They use a pretend Gemini client, so they run
without internet and without using your API key.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import errors

sys.path.insert(0, str(Path(__file__).parent.parent))
import config  # noqa: E402
from transcriber import TranscriptionError, transcribe  # noqa: E402


class FakeModels:
    def __init__(self, reply_text=None, error=None):
        self.reply_text, self.error, self.calls = reply_text, error, []

    def generate_content(self, model, contents):
        self.calls.append((model, contents))
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.reply_text)


def fake_client(**kwargs):
    return SimpleNamespace(models=FakeModels(**kwargs))


@pytest.fixture
def audio_file(tmp_path):
    path = tmp_path / "thought.wav"
    path.write_bytes(b"RIFF fake audio")
    return path


def test_returns_transcript(audio_file):
    client = fake_client(reply_text="  Buy oat milk tomorrow.  \n")
    assert (
        transcribe(audio_file, client=client, model="test-model")
        == "Buy oat milk tomorrow."
    )
    model, contents = client.models.calls[0]
    assert model == "test-model"
    assert contents[1].inline_data.mime_type == "audio/wav"  # audio was attached


def test_no_speech_returns_empty_string(audio_file):
    client = fake_client(reply_text="[no speech detected]")
    assert transcribe(audio_file, client=client, model="m") == ""


def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(TranscriptionError, match="not found"):
        transcribe(tmp_path / "gone.wav", client=fake_client(reply_text="x"), model="m")


def test_unknown_model_gives_helpful_message(audio_file):
    error = errors.ClientError(
        404, {"error": {"message": "model not found", "status": "NOT_FOUND"}}
    )
    with pytest.raises(TranscriptionError, match="check_setup.py"):
        transcribe(audio_file, client=fake_client(error=error), model="m")


def test_rate_limit_gives_helpful_message(audio_file):
    error = errors.ClientError(
        429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}}
    )
    with pytest.raises(TranscriptionError, match="Wait a minute"):
        transcribe(audio_file, client=fake_client(error=error), model="m")


def test_missing_key_is_reported(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "paste-your-key-here")
    with pytest.raises(config.MissingKeyError, match="setup_key.py"):
        config.get_api_key()
