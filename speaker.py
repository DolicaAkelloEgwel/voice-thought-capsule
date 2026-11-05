"""
speaker.py - Step 7: turn an answer into speech.

Uses macOS's built-in voice (the `say` command), so:
  - it is free and works offline,
  - the text is NOT sent to any online service to be spoken.

The sound is saved as a .wav file and played by the browser, so it comes out of
whatever your Mac is set to use for sound - e.g. your headphones.

Optional: choose a different voice by adding a line to .env, e.g.  TTS_VOICE=Daniel
(see the list of voices with:  say -v '?'  in Terminal)
"""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

# Kept in the system temp folder: the browser is allowed to play files from there,
# and old answers don't pile up in your project.
ANSWERS_DIR = Path(tempfile.gettempdir()) / "voice_thought_capsule_answers"
SPEAKING_RATE = "180"  # words per minute (macOS default is about 175-200)


class SpeechError(Exception):
    """A problem we can explain to the user in plain words."""


def speak_to_file(text, out_dir=ANSWERS_DIR, say_command=None):
    """Turn text into a .wav file and return its path."""
    text = (text or "").strip()
    if not text:
        raise SpeechError("There is no answer to read aloud yet.")

    say = say_command or shutil.which("say")
    if not say:
        raise SpeechError(
            "Reading aloud uses the built-in macOS voice, "
            "which was not found on this computer."
        )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    text_file = out_dir / f"answer_{stamp}.txt"
    audio_file = out_dir / f"answer_{stamp}.wav"
    # The text goes in via a file (-f), so nothing in the answer can be mistaken
    # for a command option.
    text_file.write_text(text, encoding="utf-8")

    command = [
        say,
        "-r",
        SPEAKING_RATE,
        "-o",
        str(audio_file),
        "--file-format=WAVE",
        "--data-format=LEI16@22050",
        "-f",
        str(text_file),
    ]
    voice = os.getenv("TTS_VOICE", "").strip()
    if voice:
        command[1:1] = ["-v", voice]

    try:
        subprocess.run(command, check=True, capture_output=True, timeout=60)
    except subprocess.CalledProcessError as error:
        hint = " Check the TTS_VOICE name in .env." if voice else ""
        raise SpeechError(f"The Mac voice could not create the audio.{hint}") from error
    except subprocess.TimeoutExpired as error:
        raise SpeechError(
            "Reading aloud took too long. Try a shorter answer."
        ) from error
    finally:
        text_file.unlink(missing_ok=True)

    if not audio_file.exists() or audio_file.stat().st_size == 0:
        raise SpeechError("The Mac voice did not produce any audio.")
    return audio_file
