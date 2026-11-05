"""
Tests for Step 6 (exhibition). A pretend 'computer voice' makes short beeps,
so these run on any computer, quickly, and without Gemini.
"""

import sys
import wave
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from exhibition import (
    RATE,
    ExhibitionError,
    create_demo,
    demo_seconds,
    list_demos,  # noqa: E402
    load_audio,
    trim_with_fade,
    write_wav,
)
from play_demo import choose_demo  # noqa: E402


def make_wav(path, seconds, rate=48000, channels=2, value=1000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(
            np.full(int(seconds * rate) * channels, value, dtype="<i2").tobytes()
        )
    return path


@pytest.fixture
def fake_tts(tmp_path):
    spoken = []

    def tts(text):
        spoken.append(text)
        return make_wav(tmp_path / f"tts_{len(spoken)}.wav", 1, rate=22050, channels=1)

    return tts, spoken


@pytest.fixture
def thought(tmp_path):
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    make_wav(
        recordings / "thought_1.wav", 3
    )  # 3 s, stereo, 48 kHz - like a browser recording
    return {
        "text": "Book the dentist and message Emma.",
        "audio_file": "thought_1.wav",
    }, recordings


def test_demo_joins_all_parts_in_order(tmp_path, fake_tts, thought):
    tts, spoken = fake_tts
    t, recordings = thought
    wav, txt, script = create_demo(
        t,
        "What do I need to do?",
        "Book the dentist.",
        tts,
        out_dir=tmp_path / "exhibition",
        recordings_dir=recordings,
    )
    assert spoken[0].startswith("This is the Voice Thought Capsule")  # intro first
    assert spoken[-1].startswith("Your thoughts")  # outro last
    assert "What do I need to do?" in spoken and "Book the dentist." in spoken
    order = [line.split(":")[0] for line in script.split("\n\n")]
    assert order == [
        "Intro",
        "Narrator",
        "Thought (recorded voice)",
        "Narrator",
        "Question",
        "Narrator",
        "Answer",
        "Outro",
    ]
    # 7 spoken parts of 1 s + 3 s recording + gaps -> roughly 16-17 s, mono 22050 Hz
    assert 15 < demo_seconds(wav) < 18
    with wave.open(str(wav)) as w:
        assert w.getnchannels() == 1 and w.getframerate() == RATE
    assert "Book the dentist and message Emma." in txt.read_text()


def test_deleted_audio_is_read_by_computer_voice(tmp_path, fake_tts, thought):
    tts, spoken = fake_tts
    t, recordings = thought
    t = {**t, "audio_file": None}  # privacy option was on
    _, _, script = create_demo(
        t, "Q?", "A.", tts, out_dir=tmp_path, recordings_dir=recordings
    )
    assert "Thought (computer voice): Book the dentist" in script
    assert any("deleted for privacy" in s for s in spoken)


def test_without_narration_intro_or_outro(tmp_path, fake_tts, thought):
    tts, spoken = fake_tts
    t, recordings = thought
    _, _, script = create_demo(
        t,
        "Q?",
        "A.",
        tts,
        intro="",
        outro="",
        narration=False,
        out_dir=tmp_path,
        recordings_dir=recordings,
    )
    assert [line.split(":")[0] for line in script.split("\n\n")] == [
        "Thought (recorded voice)",
        "Question",
        "Answer",
    ]


def test_long_recordings_are_shortened_with_a_fade():
    samples = np.ones(RATE * 10, dtype=np.float32)
    out = trim_with_fade(samples, max_seconds=4)
    assert len(out) == RATE * 4 and out[-1] == 0 and out[0] == 1


def test_stereo_48k_is_converted_to_mono_22k(tmp_path):
    samples = load_audio(make_wav(tmp_path / "x.wav", 2, rate=48000, channels=2))
    assert abs(len(samples) - 2 * RATE) <= 1


def test_missing_parts_are_explained(tmp_path, fake_tts, thought):
    tts, _ = fake_tts
    t, _ = thought
    with pytest.raises(ExhibitionError, match="Choose a thought"):
        create_demo(None, "Q?", "A.", tts, out_dir=tmp_path)
    with pytest.raises(ExhibitionError, match="question"):
        create_demo(t, " ", "A.", tts, out_dir=tmp_path)


def test_demos_are_listed_newest_first_and_player_picks_newest(tmp_path):
    for name in ("demo_2026-11-01_10-00-00.wav", "demo_2026-11-02_10-00-00.wav"):
        write_wav(tmp_path / name, np.zeros(100, dtype=np.float32))
    demos = list_demos(tmp_path)
    assert demos[0].name.startswith("demo_2026-11-02")
    assert choose_demo([], demos) == demos[0]
    assert choose_demo(["--loop"], demos) == demos[0]
    assert choose_demo([str(demos[1])], demos) == demos[1]
    assert choose_demo(["missing.wav"], demos) is None
