"""
recorder.py - Step 1: keep a copy of a voice recording.

This file has NO user-interface code, so it is easy to test on its own.
app.py (the Gradio interface) calls these functions.
"""

import shutil
import wave
from datetime import datetime
from pathlib import Path

# Folder where recordings are kept (created automatically if missing).
RECORDINGS_DIR = Path(__file__).parent / "data" / "recordings"


def get_duration_seconds(audio_path):
    """Return the length of a .wav file in seconds, or None if we can't tell."""
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            return wav_file.getnframes() / wav_file.getframerate()
    except (wave.Error, EOFError, OSError, ZeroDivisionError):
        return None  # not a readable .wav file - that's OK, we just skip the length


def save_recording(temp_audio_path, recordings_dir=RECORDINGS_DIR):
    """
    Copy the temporary file Gradio gives us into our own recordings folder.

    Gradio stores microphone audio in a temporary folder that can be wiped,
    so we keep our own copy with a timestamped filename,
    e.g. data/recordings/thought_2026-10-31_14-05-09.wav

    Returns the path of the saved copy.
    """
    if not temp_audio_path:
        raise ValueError("No recording found. Press the microphone button and speak first.")

    source = Path(temp_audio_path)
    if not source.exists():
        raise FileNotFoundError(f"The recording file is missing: {source}")

    recordings_dir = Path(recordings_dir)
    recordings_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destination = recordings_dir / f"thought_{timestamp}{source.suffix or '.wav'}"

    # If two recordings are saved in the same second, add a number: _2, _3 ...
    counter = 2
    while destination.exists():
        destination = recordings_dir / f"thought_{timestamp}_{counter}{source.suffix or '.wav'}"
        counter += 1

    shutil.copy(source, destination)
    return destination
