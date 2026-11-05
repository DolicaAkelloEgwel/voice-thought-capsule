"""
storage.py - Step 3: save thoughts in a local JSON file.

Every thought gets:
  id           - a unique ID (UUID), so we can find, edit or delete it later
  created_at   - date and time it was saved (your computer's local time zone)
  text         - what you said
  audio_file   - name of the recording in data/recordings/
  duration_seconds - length of the recording
  items        - (Step 4) the thought split into labelled items, each with its own ID:
                 {"id", "type": "idea" | "task" | "reminder", "text", "when"}
                 None means "not sorted yet".

The file is data/thoughts.json. It stays on your computer.
You can open it in TextEdit to see exactly what is stored.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

THOUGHTS_FILE = Path(__file__).parent / "data" / "thoughts.json"


def load_thoughts(path=THOUGHTS_FILE):
    """Return the list of saved thoughts (oldest first). Empty list if none yet."""
    path = Path(path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # The file was damaged (e.g. edited by hand). Keep a copy so nothing is lost,
        # then start a fresh list instead of crashing.
        backup = path.with_name(f"thoughts_damaged_{datetime.now():%Y%m%d_%H%M%S}.json")
        path.rename(backup)
        print(
            f"Warning: {path.name} could not be read. A copy was saved as {backup.name}."
        )
        return []
    return data.get("thoughts", [])


def save_thoughts(thoughts, path=THOUGHTS_FILE):
    """Write all thoughts to the JSON file safely."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temporary file first, then swap it in. If the app is closed
    # mid-save, the old file stays intact instead of being half-written.
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps({"version": 1, "thoughts": thoughts}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temp, path)


def _with_ids(items):
    """Give every item its own unique ID (so it can be edited or deleted later)."""
    return [{"id": str(uuid.uuid4()), **item} for item in items]


def add_thought(
    text, audio_file=None, duration_seconds=None, items=None, path=THOUGHTS_FILE
):
    """Create a new thought, save it, and return it."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Cannot save an empty thought.")

    thought = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "text": text,
        "audio_file": Path(audio_file).name if audio_file else None,
        "duration_seconds": round(duration_seconds, 1) if duration_seconds else None,
        "items": _with_ids(items) if items is not None else None,
    }
    thoughts = load_thoughts(path)
    thoughts.append(thought)
    save_thoughts(thoughts, path)
    return thought


def thoughts_table(path=THOUGHTS_FILE):
    """Rows for the on-screen table, newest first: [date, short ID, text]."""
    rows = []
    for t in reversed(load_thoughts(path)):
        when = datetime.fromisoformat(t["created_at"]).strftime("%d %b %Y, %H:%M")
        rows.append([when, t["id"][:8], t["text"]])
    return rows


def set_items(thought_id, items, path=THOUGHTS_FILE):
    """Store the sorted items for an existing thought."""
    thoughts = load_thoughts(path)
    for thought in thoughts:
        if thought["id"] == thought_id:
            thought["items"] = _with_ids(items)
            save_thoughts(thoughts, path)
            return thought
    raise KeyError(f"No thought with ID {thought_id}")


def unsorted_thoughts(path=THOUGHTS_FILE):
    """Thoughts saved before Step 4, or whose sorting failed."""
    return [t for t in load_thoughts(path) if t.get("items") is None]


TYPE_LABELS = {"task": "✅ Task", "reminder": "🔔 Reminder", "idea": "💡 Idea"}


def items_table(show="All", path=THOUGHTS_FILE):
    """
    Rows for the sorted-items table, newest first: [type, item, when, saved, from thought].
    `show` is "All", "Tasks", "Reminders" or "Ideas".
    """
    wanted = {"Tasks": "task", "Reminders": "reminder", "Ideas": "idea"}.get(show)
    rows = []
    for thought in reversed(load_thoughts(path)):
        when_saved = datetime.fromisoformat(thought["created_at"]).strftime(
            "%d %b, %H:%M"
        )
        for item in thought.get("items") or []:
            if wanted and item["type"] != wanted:
                continue
            rows.append(
                [
                    TYPE_LABELS.get(item["type"], item["type"]),
                    item["text"],
                    item.get("when") or "",
                    when_saved,
                    thought["id"][:8],
                ]
            )
    return rows
