"""
consent.py - Step 8: clear recording permission.

Nothing can be recorded until the person has agreed, and they can withdraw
their permission at any time. The choice is stored in data/consent.json
together with the date and time.

(This is the app's own permission. The browser will also ask for microphone
access the first time - both are needed.)
"""

import json
from datetime import datetime
from pathlib import Path

CONSENT_FILE = Path(__file__).parent / "data" / "consent.json"

CONSENT_TEXT = """### Before you record
**What happens when you record a thought:**
- Your voice is recorded and saved **on this computer** (`data/recordings/`). In 🔒 Privacy settings
  you can choose to delete each recording right after it is transcribed.
- The recording is sent to **Google's Gemini service** to turn it into text. The text is
  also sent to Gemini to sort it, connect it and answer your questions.
  On Gemini's free tier, Google may use this data to improve its products.
- Answers are read aloud by your Mac's built-in voice. That part stays on your computer.
- You can **edit, delete and undo** in the ✏️ Edit tab, and **withdraw this permission** at any time.

Please don't record other people without their permission, or very sensitive information.
"""


class ConsentError(Exception):
    """Raised when someone tries to record without permission."""


def has_consent(path=CONSENT_FILE):
    path = Path(path)
    if not path.exists():
        return False
    try:
        return bool(json.loads(path.read_text(encoding="utf-8")).get("given"))
    except json.JSONDecodeError:
        return False  # if in doubt, ask again


def _write(given, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"given": given, "at": datetime.now().astimezone().isoformat(timespec="seconds")}
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def give_consent(path=CONSENT_FILE):
    return _write(True, path)


def withdraw_consent(path=CONSENT_FILE):
    return _write(False, path)


def require_consent(path=CONSENT_FILE):
    if not has_consent(path):
        raise ConsentError("Recording is not allowed yet. Give permission in the Record tab first.")
