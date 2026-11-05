"""
Tests for Step 7. They use a pretend 'say' program, so they also run on
computers without the macOS voice (and make no sound).
"""

import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from speaker import SpeechError, speak_to_file  # noqa: E402

FAKE_SAY = """#!/bin/sh
# Pretend 'say': copies the text file (after -f) into the output file (after -o)
# and records its arguments.
echo "$@" > "$(dirname "$0")/args.txt"
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift ;;
    -f) txt="$2"; shift ;;
  esac
  shift
done
cp "$txt" "$out"
"""


@pytest.fixture
def fake_say(tmp_path):
    path = tmp_path / "say"
    path.write_text(FAKE_SAY)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_answer_becomes_an_audio_file(tmp_path, fake_say, monkeypatch):
    monkeypatch.delenv("TTS_VOICE", raising=False)
    out = speak_to_file(
        "You promised to help Daniel.",
        out_dir=tmp_path / "answers",
        say_command=str(fake_say),
    )
    assert out.suffix == ".wav" and out.read_text() == "You promised to help Daniel."
    args = (tmp_path / "args.txt").read_text()
    assert "--file-format=WAVE" in args and "-v" not in args.split()
    assert (
        list((tmp_path / "answers").glob("*.txt")) == []
    )  # temporary text file removed


def test_text_starting_with_dash_is_safe(tmp_path, fake_say):
    out = speak_to_file("-o /etc/passwd", out_dir=tmp_path, say_command=str(fake_say))
    assert out.read_text() == "-o /etc/passwd"  # spoken as text, not as an option


def test_voice_can_be_chosen_in_env(tmp_path, fake_say, monkeypatch):
    monkeypatch.setenv("TTS_VOICE", "Daniel")
    speak_to_file("Hello", out_dir=tmp_path, say_command=str(fake_say))
    assert "-v Daniel" in (tmp_path / "args.txt").read_text()


def test_empty_answer_is_not_spoken(tmp_path, fake_say):
    with pytest.raises(SpeechError, match="no answer"):
        speak_to_file("  ", out_dir=tmp_path, say_command=str(fake_say))


def test_failing_voice_gives_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("TTS_VOICE", "NoSuchVoice")
    with pytest.raises(SpeechError, match="TTS_VOICE"):
        speak_to_file("Hello", out_dir=tmp_path, say_command="false")


def test_missing_mac_voice_is_explained(tmp_path, monkeypatch):
    monkeypatch.setattr("speaker.shutil.which", lambda name: None)
    with pytest.raises(SpeechError, match="macOS voice"):
        speak_to_file("Hello", out_dir=tmp_path)
