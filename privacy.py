"""
privacy.py - Extra: delete audio after transcribing.

When "Delete audio after transcribing" is on, each recording is deleted as soon
as it has been turned into text - only the text is kept. If transcription fails,
the audio is KEPT so the thought isn't lost.

The setting is stored in data/settings.json.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
RECORDINGS_DIR = DATA_DIR / "recordings"


def _load(path):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def delete_audio_enabled(path=SETTINGS_FILE):
    return bool(_load(path).get("delete_audio_after_transcribing", False))


def set_delete_audio(enabled, path=SETTINGS_FILE):
    path = Path(path)
    settings = _load(path)
    settings["delete_audio_after_transcribing"] = bool(enabled)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings["delete_audio_after_transcribing"]


def remove_file(path):
    """Delete a file if it exists. Returns True if something was deleted."""
    if not path:
        return False
    path = Path(path)
    if path.is_file():
        path.unlink()
        return True
    return False


def delete_all_audio(thoughts_file, recordings_dir=RECORDINGS_DIR):
    """
    Permanently delete every saved recording but keep all the text.
    Returns how many audio files were deleted.
    """
    # Imported here so this module has no circular imports with storage.
    from storage import load_thoughts, save_thoughts

    thoughts = load_thoughts(thoughts_file)
    deleted = 0
    for thought in thoughts:
        if thought.get("audio_file"):
            if remove_file(Path(recordings_dir) / thought["audio_file"]):
                deleted += 1
            thought["audio_file"] = None
            thought["audio_deleted"] = True
    save_thoughts(thoughts, thoughts_file)

    # Also remove any recordings that were never linked to a thought
    # (e.g. ones where no speech was detected).
    for leftover in Path(recordings_dir).glob("thought_*"):
        if remove_file(leftover):
            deleted += 1
    return deleted
