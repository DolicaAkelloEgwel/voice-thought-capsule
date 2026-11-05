"""
Tests for the privacy option 'Delete audio after transcribing'.
Gemini and the permission check are replaced with pretend versions, and
everything happens in temporary folders.
"""

import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import app  # noqa: E402
import privacy  # noqa: E402
from storage import add_thought, load_thoughts  # noqa: E402
from transcriber import TranscriptionError  # noqa: E402


def make_wav(path):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000)
    return path


@pytest.fixture
def setup(tmp_path, monkeypatch):
    """A pretend app: temporary data folder, pretend Gemini, permission given."""
    recordings = tmp_path / "recordings"
    thoughts_file = tmp_path / "thoughts.json"
    settings = tmp_path / "settings.json"

    import recorder, storage

    monkeypatch.setattr(recorder, "RECORDINGS_DIR", recordings)
    monkeypatch.setattr(
        app, "save_recording", lambda p: recorder.save_recording(p, recordings)
    )
    monkeypatch.setattr(
        app,
        "add_thought",
        lambda *a, **k: storage.add_thought(*a, path=thoughts_file, **k),
    )
    for name in ("items_table", "thoughts_table", "current_insights"):
        monkeypatch.setattr(app, name, lambda *a, **k: None)
    monkeypatch.setattr(
        app, "delete_audio_enabled", lambda: privacy.delete_audio_enabled(settings)
    )
    monkeypatch.setattr(app, "require_consent", lambda: None)
    monkeypatch.setattr(app, "transcribe", lambda p: "Buy milk tomorrow.")
    monkeypatch.setattr(
        app,
        "classify",
        lambda t: [{"type": "task", "text": "Buy milk", "when": "tomorrow"}],
    )
    monkeypatch.setattr(app.gr, "Warning", lambda m: None)

    browser_copy = make_wav(tmp_path / "gradio_temp.wav")  # the file Gradio gives us
    return {
        "recordings": recordings,
        "thoughts": thoughts_file,
        "settings": settings,
        "browser_copy": browser_copy,
    }


def test_setting_is_off_by_default_and_remembered(tmp_path):
    path = tmp_path / "settings.json"
    assert privacy.delete_audio_enabled(path) is False
    privacy.set_delete_audio(True, path)
    assert privacy.delete_audio_enabled(path) is True


def test_audio_is_kept_when_setting_is_off(setup):
    app.save_and_transcribe(str(setup["browser_copy"]), "All")
    thought = load_thoughts(setup["thoughts"])[0]
    assert (
        thought["audio_file"] and (setup["recordings"] / thought["audio_file"]).exists()
    )


def test_audio_is_deleted_after_transcribing_when_setting_is_on(setup):
    privacy.set_delete_audio(True, setup["settings"])
    status, text, *_ = app.save_and_transcribe(str(setup["browser_copy"]), "All")

    thought = load_thoughts(setup["thoughts"])[0]
    assert thought["text"] == "Buy milk tomorrow."  # the text is kept
    assert thought["audio_file"] is None  # ...but no audio
    assert list(setup["recordings"].glob("thought_*")) == []  # our copy is gone
    assert not setup["browser_copy"].exists()  # Gradio's temporary copy too
    assert "audio was deleted" in status


def test_audio_is_kept_if_transcription_fails_even_with_setting_on(setup, monkeypatch):
    privacy.set_delete_audio(True, setup["settings"])

    def broken(p):
        raise TranscriptionError("Gemini is busy.")

    monkeypatch.setattr(app, "transcribe", broken)
    status, *_ = app.save_and_transcribe(str(setup["browser_copy"]), "All")
    assert len(list(setup["recordings"].glob("thought_*"))) == 1  # nothing lost
    assert "kept" in status


def test_silence_with_setting_on_leaves_nothing_behind(setup, monkeypatch):
    privacy.set_delete_audio(True, setup["settings"])
    monkeypatch.setattr(app, "transcribe", lambda p: "")
    app.save_and_transcribe(str(setup["browser_copy"]), "All")
    assert list(setup["recordings"].glob("thought_*")) == []
    assert not setup["thoughts"].exists() or load_thoughts(setup["thoughts"]) == []


def test_delete_all_existing_audio_keeps_text(tmp_path):
    recordings, thoughts_file = tmp_path / "recordings", tmp_path / "thoughts.json"
    recordings.mkdir()
    (recordings / "thought_1.wav").write_bytes(b"a")
    (recordings / "thought_2.wav").write_bytes(b"b")  # not linked to any thought
    add_thought("Keep this text", audio_file="thought_1.wav", path=thoughts_file)

    assert privacy.delete_all_audio(thoughts_file, recordings) == 2
    thought = load_thoughts(thoughts_file)[0]
    assert thought["text"] == "Keep this text" and thought["audio_file"] is None
    assert list(recordings.glob("thought_*")) == []


def test_spoken_question_audio_is_always_removed(tmp_path, monkeypatch):
    question_audio = make_wav(tmp_path / "question.wav")
    monkeypatch.setattr(app, "require_consent", lambda: None)
    monkeypatch.setattr(app, "transcribe", lambda p: "Anything for Friday?")
    monkeypatch.setattr(
        app, "ask_question", lambda q, r, d="Brief": ("Nothing.", "", None)
    )
    app.ask_by_voice(str(question_audio), read_aloud=False)
    assert not question_audio.exists()
