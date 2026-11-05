"""
exhibition.py - Faculty Step 6: prepare the exhibition version.

Turns one real interaction into a single audio file for headphones:

    intro -> your recorded thought -> the question -> the spoken answer -> outro

with short narration between the parts, so visitors understand it without a
screen. A matching text script is saved next to it (for posters and captions).

Exhibition advice this follows: pre-recorded audio instead of live microphones,
and no visitor voice data is collected. Files are saved in the exhibition/ folder.
"""

import wave
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).parent
EXHIBITION_DIR = PROJECT_DIR / "exhibition"
RECORDINGS_DIR = PROJECT_DIR / "data" / "recordings"
RATE = 22050          # samples per second of the finished demo (good quality for speech)
GAP_SECONDS = 0.8     # silence between parts

DEFAULT_INTRO = ("This is the Voice Thought Capsule. Listen to how a spoken thought is "
                 "captured, organised and remembered.")
DEFAULT_OUTRO = "Your thoughts, kept safe, and ready when you need them."
NARRATION = {
    "thought": "First, a thought is spoken into the capsule.",
    "thought_tts": ("First, a thought is spoken into the capsule. The original audio was deleted "
                    "for privacy, so it is read by the computer voice."),
    "question": "Later, the person asks:",
    "answer": "The capsule finds the relevant notes and answers:",
}


class ExhibitionError(Exception):
    """A problem we can explain to the user in plain words."""


# --- small audio helpers (no extra software needed) --------------------------------

def load_audio(path, rate=RATE):
    """Read a .wav file as mono float samples (-1..1) at `rate` samples per second."""
    try:
        with wave.open(str(path), "rb") as w:
            channels, width, src_rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
            raw = w.readframes(w.getnframes())
    except (wave.Error, EOFError, FileNotFoundError) as error:
        raise ExhibitionError(f"Could not read the audio file {Path(path).name}.") from error

    if width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128
    elif width == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    elif width == 4:
        samples = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648
    else:
        raise ExhibitionError(f"Unsupported audio format in {Path(path).name}.")
    if channels > 1:  # mix stereo down to mono
        samples = samples.reshape(-1, channels).mean(axis=1)
    if src_rate != rate and len(samples):
        duration = len(samples) / src_rate
        new_times = np.linspace(0, duration, int(duration * rate), endpoint=False)
        old_times = np.arange(len(samples)) / src_rate
        samples = np.interp(new_times, old_times, samples).astype(np.float32)
    return samples


def silence(seconds, rate=RATE):
    return np.zeros(int(seconds * rate), dtype=np.float32)


def trim_with_fade(samples, max_seconds, rate=RATE, fade_seconds=0.6):
    """Shorten long recordings for the exhibition, fading out gently instead of cutting."""
    limit = int(max_seconds * rate)
    if len(samples) <= limit:
        return samples
    out = samples[:limit].copy()
    fade = min(int(fade_seconds * rate), limit)
    out[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    return out


def write_wav(path, samples, rate=RATE):
    samples = np.clip(samples, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((samples * 32767).astype("<i2").tobytes())


# --- building the demo -------------------------------------------------------------

def create_demo(thought, question, answer, tts, intro=DEFAULT_INTRO, outro=DEFAULT_OUTRO,
                narration=True, max_thought_seconds=30, out_dir=EXHIBITION_DIR,
                recordings_dir=RECORDINGS_DIR):
    """
    Build one demo audio file plus a text script.
    `tts` turns text into a .wav file path (the Mac voice, from speaker.py).
    Returns (audio_path, script_path, script_text).
    """
    question, answer = (question or "").strip(), (answer or "").strip()
    if not thought:
        raise ExhibitionError("Choose a thought for the demo first.")
    if not question:
        raise ExhibitionError("Type the question to ask in the demo.")
    if not answer:
        raise ExhibitionError("There is no answer to put in the demo.")

    audio_name = thought.get("audio_file")
    audio_path = Path(recordings_dir) / audio_name if audio_name else None
    own_voice = bool(audio_path and audio_path.exists())

    parts, script = [], []

    def say(text, label):
        text = (text or "").strip()
        if text:
            parts.append(load_audio(tts(text)))
            script.append(f"{label}: {text}")

    say(intro, "Intro")
    if narration:
        say(NARRATION["thought"] if own_voice else NARRATION["thought_tts"], "Narrator")
    if own_voice:
        parts.append(trim_with_fade(load_audio(audio_path), max_thought_seconds))
        script.append(f"Thought (recorded voice): {thought['text']}")
    else:
        say(thought["text"], "Thought (computer voice)")
    if narration:
        say(NARRATION["question"], "Narrator")
    say(question, "Question")
    if narration:
        say(NARRATION["answer"], "Narrator")
    say(answer, "Answer")
    say(outro, "Outro")

    joined = [silence(0.5)]
    for part in parts:
        joined += [part, silence(GAP_SECONDS)]
    audio = np.concatenate(joined)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    wav_path, txt_path = out_dir / f"demo_{stamp}.wav", out_dir / f"demo_{stamp}.txt"
    write_wav(wav_path, audio)
    script_text = "\n\n".join(script)
    txt_path.write_text(f"Voice Thought Capsule - exhibition demo ({len(audio) / RATE:.0f} s)\n\n"
                        + script_text + "\n", encoding="utf-8")
    return wav_path, txt_path, script_text


def list_demos(out_dir=EXHIBITION_DIR):
    """Saved demo files, newest first."""
    out_dir = Path(out_dir)
    return sorted(out_dir.glob("demo_*.wav"), reverse=True) if out_dir.exists() else []


def demo_seconds(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()
