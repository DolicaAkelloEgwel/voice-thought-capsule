"""
Tests for 'Ask by voice'. Gemini, the Mac voice and the permission check are
replaced with pretend versions, so nothing is sent anywhere and no sound plays.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import app  # noqa: E402
from consent import ConsentError  # noqa: E402
from transcriber import TranscriptionError  # noqa: E402


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    asked = []
    monkeypatch.setattr(app, "require_consent", lambda: None)
    monkeypatch.setattr(app, "transcribe", lambda path: "Who did I promise to help?")
    monkeypatch.setattr(app, "load_thoughts", lambda: [])

    def fake_ask(question, thoughts, detail="Brief"):
        asked.append(question)
        return "You promised to help Daniel.", []
    monkeypatch.setattr(app, "ask", fake_ask)
    monkeypatch.setattr(app, "speak_to_file", lambda text: tmp_path / "answer.wav")
    monkeypatch.setattr(app.gr, "Warning", lambda message: None)
    audio = tmp_path / "question.wav"
    audio.write_bytes(b"audio")
    return asked, audio


def test_spoken_question_is_transcribed_answered_and_read_aloud(fakes):
    asked, audio = fakes
    question, answer, notes, spoken = app.ask_by_voice(str(audio), read_aloud=True)
    assert question == "Who did I promise to help?"      # shown in the question box
    assert asked == ["Who did I promise to help?"]       # the transcribed text was asked
    assert answer == "You promised to help Daniel."
    assert spoken.endswith("answer.wav")


def test_spoken_question_is_not_saved_as_a_thought(fakes, monkeypatch):
    _, audio = fakes
    monkeypatch.setattr(app, "add_thought", lambda *a, **k: pytest.fail("question was saved"))
    monkeypatch.setattr(app, "save_recording", lambda *a, **k: pytest.fail("audio was saved"))
    app.ask_by_voice(str(audio), read_aloud=False)


def test_no_permission_means_no_transcription(fakes, monkeypatch):
    _, audio = fakes
    def refuse():
        raise ConsentError("Recording is not allowed yet.")
    monkeypatch.setattr(app, "require_consent", refuse)
    monkeypatch.setattr(app, "transcribe", lambda path: pytest.fail("sent to Gemini without permission"))
    _, answer, _, spoken = app.ask_by_voice(str(audio), read_aloud=True)
    assert "not allowed" in answer and spoken is None


def test_nothing_recorded(fakes):
    assert app.ask_by_voice(None, read_aloud=True) == ("", "", "", None)


def test_silence_is_handled_kindly(fakes, monkeypatch):
    _, audio = fakes
    monkeypatch.setattr(app, "transcribe", lambda path: "")
    _, answer, _, _ = app.ask_by_voice(str(audio), read_aloud=True)
    assert "didn't catch" in answer


def test_transcription_error_is_explained(fakes, monkeypatch):
    _, audio = fakes
    def broken(path):
        raise TranscriptionError("Gemini is busy.")
    monkeypatch.setattr(app, "transcribe", broken)
    _, answer, _, _ = app.ask_by_voice(str(audio), read_aloud=True)
    assert "Gemini is busy" in answer
