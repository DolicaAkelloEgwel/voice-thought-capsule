"""Tests for Step 1. Run with:  python -m pytest"""

import sys
import wave
from pathlib import Path

import pytest

# Let the tests import recorder.py from the project folder.
sys.path.insert(0, str(Path(__file__).parent.parent))
from recorder import get_duration_seconds, save_recording  # noqa: E402


def make_silent_wav(path, seconds=1.0, rate=16000):
    """Create a short silent .wav file so tests don't need a real microphone."""
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(b"\x00\x00" * int(rate * seconds))
    return path


def test_save_recording_copies_file(tmp_path):
    source = make_silent_wav(tmp_path / "temp.wav", seconds=2)
    saved = save_recording(source, recordings_dir=tmp_path / "recordings")

    assert saved.exists()
    assert saved.name.startswith("thought_")
    assert saved.suffix == ".wav"
    assert source.exists()  # the original is untouched


def test_two_saves_in_same_second_do_not_overwrite(tmp_path):
    source = make_silent_wav(tmp_path / "temp.wav")
    first = save_recording(source, recordings_dir=tmp_path / "rec")
    second = save_recording(source, recordings_dir=tmp_path / "rec")
    assert first != second
    assert first.exists() and second.exists()


def test_duration_is_measured(tmp_path):
    source = make_silent_wav(tmp_path / "temp.wav", seconds=1.5)
    assert get_duration_seconds(source) == pytest.approx(1.5)


def test_duration_of_non_wav_is_none(tmp_path):
    not_audio = tmp_path / "note.wav"
    not_audio.write_text("hello")
    assert get_duration_seconds(not_audio) is None


def test_missing_recording_gives_clear_error():
    with pytest.raises(ValueError, match="No recording"):
        save_recording(None)
