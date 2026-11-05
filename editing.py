"""
editing.py - Step 8: edit, delete and undo.

- Edit an item's text, type or time words.
- Delete one item, or a whole recording (its transcript, items and audio).
- Deleted audio goes to a bin (data/bin/) so it can be brought back with Undo.
  "Empty bin" deletes it permanently - that cannot be undone.
- Undo reverses the last edit or delete. The last 20 changes are remembered
  in data/undo_history.json. Each undo step stores a copy of only the ONE recording
  that changed, so undoing never removes thoughts you recorded afterwards.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from storage import THOUGHTS_FILE, load_thoughts, save_thoughts

DATA_DIR = THOUGHTS_FILE.parent
UNDO_FILE = DATA_DIR / "undo_history.json"
RECORDINGS_DIR = DATA_DIR / "recordings"
BIN_DIR = DATA_DIR / "bin"
MAX_UNDO = 20
ITEM_TYPES = ("task", "reminder", "idea")
ICONS = {"task": "✅", "reminder": "🔔", "idea": "💡"}


class EditError(Exception):
    """A problem we can explain to the user in plain words."""


class Store:
    """All file locations in one place (tests use temporary folders)."""

    def __init__(
        self,
        thoughts=THOUGHTS_FILE,
        undo=UNDO_FILE,
        recordings=RECORDINGS_DIR,
        bin_dir=BIN_DIR,
    ):
        self.thoughts, self.undo = Path(thoughts), Path(undo)
        self.recordings, self.bin = Path(recordings), Path(bin_dir)

    # --- undo history ------------------------------------------------------
    def _history(self):
        if not self.undo.exists():
            return []
        try:
            return json.loads(self.undo.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _remember(self, description, thought_before, binned_audio=None):
        """Save a copy of the recording BEFORE it changes, so it can be restored."""
        history = self._history()
        history.append(
            {
                "description": description,
                "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "thought": json.loads(json.dumps(thought_before)),  # a true copy
                "binned_audio": binned_audio or [],
            }
        )
        self.undo.parent.mkdir(parents=True, exist_ok=True)
        self.undo.write_text(
            json.dumps(history[-MAX_UNDO:], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def last_change(self):
        history = self._history()
        return history[-1]["description"] if history else None

    def undo_last(self):
        history = self._history()
        if not history:
            raise EditError("There is nothing to undo.")
        step = history.pop()
        missing = []
        for name in step["binned_audio"]:  # bring audio back from the bin
            if (self.bin / name).exists():
                self.recordings.mkdir(parents=True, exist_ok=True)
                shutil.move(str(self.bin / name), str(self.recordings / name))
            else:
                missing.append(name)
        # Put the saved copy back, leaving every other thought exactly as it is now.
        restored = step["thought"]
        thoughts = [
            t for t in load_thoughts(self.thoughts) if t["id"] != restored["id"]
        ]
        thoughts.append(restored)
        thoughts.sort(key=lambda t: t["created_at"])
        save_thoughts(thoughts, self.thoughts)
        self.undo.write_text(
            json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        note = " (the audio had already been permanently deleted)" if missing else ""
        return f"Undone: {step['description']}{note}"

    # --- finding things ----------------------------------------------------
    def _find_item(self, thoughts, item_id):
        for thought in thoughts:
            for item in thought.get("items") or []:
                if item["id"] == item_id:
                    return thought, item
        raise EditError("That item no longer exists. Choose another one.")

    def item_choices(self):
        """(label, id) pairs for a drop-down, newest first."""
        choices = []
        for thought in reversed(load_thoughts(self.thoughts)):
            for item in thought.get("items") or []:
                text = (
                    item["text"]
                    if len(item["text"]) <= 70
                    else item["text"][:67] + "..."
                )
                choices.append((f"{ICONS.get(item['type'], '')} {text}", item["id"]))
        return choices

    def thought_choices(self):
        choices = []
        for thought in reversed(load_thoughts(self.thoughts)):
            saved = datetime.fromisoformat(thought["created_at"]).strftime(
                "%d %b, %H:%M"
            )
            preview = thought["text"][:60] + (
                "..." if len(thought["text"]) > 60 else ""
            )
            choices.append((f'{saved} - "{preview}"', thought["id"]))
        return choices

    def get_item(self, item_id):
        return self._find_item(load_thoughts(self.thoughts), item_id)[1]

    # --- changes -----------------------------------------------------------
    def edit_item(self, item_id, text, item_type, when):
        text, when = (text or "").strip(), (when or "").strip()
        if not text:
            raise EditError(
                "The item text can't be empty. Use 'Delete item' to remove it."
            )
        if item_type not in ITEM_TYPES:
            raise EditError("Choose task, reminder or idea.")
        thoughts = load_thoughts(self.thoughts)
        thought, item = self._find_item(thoughts, item_id)
        if (item["text"], item["type"], item.get("when") or "") == (
            text,
            item_type,
            when,
        ):
            raise EditError("Nothing was changed.")
        self._remember(f"edit of \"{item['text']}\"", thought)
        item.update(
            text=text,
            type=item_type,
            when=when or None,
            edited_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        save_thoughts(thoughts, self.thoughts)
        return f'Saved changes to "{text}".'

    def delete_item(self, item_id):
        thoughts = load_thoughts(self.thoughts)
        thought, item = self._find_item(thoughts, item_id)
        self._remember(f"deletion of \"{item['text']}\"", thought)
        thought["items"] = [i for i in thought["items"] if i["id"] != item_id]
        save_thoughts(thoughts, self.thoughts)
        return f"Deleted \"{item['text']}\". You can undo this."

    def delete_thought(self, thought_id):
        thoughts = load_thoughts(self.thoughts)
        match = [t for t in thoughts if t["id"] == thought_id]
        if not match:
            raise EditError("That recording no longer exists.")
        thought = match[0]
        binned = []
        audio = thought.get("audio_file")
        if audio and (self.recordings / audio).exists():
            self.bin.mkdir(parents=True, exist_ok=True)
            shutil.move(str(self.recordings / audio), str(self.bin / audio))
            binned.append(audio)
        saved = datetime.fromisoformat(thought["created_at"]).strftime("%d %b, %H:%M")
        self._remember(f"deletion of the recording from {saved}", thought, binned)
        save_thoughts([t for t in thoughts if t["id"] != thought_id], self.thoughts)
        n = len(thought.get("items") or [])
        where = (
            "The audio is in the bin - you can undo this."
            if binned
            else "You can undo this."
        )
        return f"Deleted the recording from {saved} and its {n} item{'s' if n != 1 else ''}. {where}"

    def bin_count(self):
        return (
            len([f for f in self.bin.glob("*") if f.is_file()])
            if self.bin.exists()
            else 0
        )

    def empty_bin(self):
        """Permanently delete the audio in the bin. This can't be undone."""
        count = self.bin_count()
        if count == 0:
            raise EditError("The bin is already empty.")
        shutil.rmtree(self.bin)
        return f"Permanently deleted {count} recording{'s' if count != 1 else ''} from the bin."
