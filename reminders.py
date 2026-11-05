"""
reminders.py - Extra: real reminders with Mac notifications.

You choose a reminder item and a date/time. The app saves it in
data/schedule.json and a small background checker (the "scheduler") looks
every 15 seconds for reminders that are due. When one is due it shows a
macOS notification (and can also say it aloud).

Honest limits - also shown in the app:
- Notifications only appear while the app is running (Terminal open, Mac awake).
- If the app was closed at the due time, the reminder is marked "missed" and
  delivered as soon as the app starts again - it is never silently lost.
"""

import json
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

SCHEDULE_FILE = Path(__file__).parent / "data" / "schedule.json"
CHECK_EVERY_SECONDS = 15
LATE_AFTER = timedelta(minutes=2)  # delivered later than this counts as "missed"
_lock = threading.Lock()  # the checker and the web page may both write the file


class ReminderError(Exception):
    """A problem we can explain to the user in plain words."""


# --- notifications ---------------------------------------------------------------


def _applescript_text(text):
    """Make text safe to put inside an AppleScript "..." string."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def mac_notify(title, message, speak=False):
    """Show a macOS notification (and optionally say it). Returns True if it worked."""
    osascript = shutil.which("osascript")
    if not osascript:
        return False
    script = (
        f'display notification "{_applescript_text(message)}" '
        f'with title "{_applescript_text(title)}" sound name "Glass"'
    )
    ok = (
        subprocess.run(
            [osascript, "-e", script], capture_output=True, timeout=15
        ).returncode
        == 0
    )
    say = shutil.which("say")
    if speak and say:
        # Text goes in on standard input, so it can't be mistaken for an option.
        subprocess.run(
            [say],
            input=f"Reminder: {message}",
            text=True,
            capture_output=True,
            timeout=60,
        )
    return ok


# --- the schedule file -------------------------------------------------------------


def load_schedule(path=SCHEDULE_FILE):
    path = Path(path)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("reminders", [])
    except json.JSONDecodeError:
        return []


def save_schedule(reminders, path=SCHEDULE_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(
            {"version": 1, "reminders": reminders}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    temp.replace(path)


def _now():
    return datetime.now().astimezone()


def schedule_reminder(item_id, text, due, speak=True, path=SCHEDULE_FILE, now=None):
    """Save a reminder for `due` (a datetime in local time). Returns the saved reminder."""
    now = now or _now()
    if not item_id or not (text or "").strip():
        raise ReminderError("Choose a reminder first.")
    if due is None:
        raise ReminderError("Choose a date and time first.")
    if due.tzinfo is None:
        due = due.astimezone()  # the picker gives local time without a zone
    if due <= now:
        raise ReminderError(
            "That time has already passed. Choose a time in the future."
        )
    reminder = {
        "id": str(uuid.uuid4()),
        "item_id": item_id,
        "text": text.strip(),
        "due_at": due.isoformat(timespec="seconds"),
        "speak": bool(speak),
        "status": "scheduled",
        "created_at": now.isoformat(timespec="seconds"),
    }
    with _lock:
        reminders = load_schedule(path)
        reminders.append(reminder)
        save_schedule(reminders, path)
    return reminder


def cancel_reminder(reminder_id, path=SCHEDULE_FILE):
    with _lock:
        reminders = load_schedule(path)
        for r in reminders:
            if r["id"] == reminder_id:
                if r["status"] != "scheduled":
                    raise ReminderError(
                        "Only reminders that haven't gone off yet can be cancelled."
                    )
                r["status"] = "cancelled"
                save_schedule(reminders, path)
                return r
    raise ReminderError("That reminder no longer exists.")


def deliver_due(notify=mac_notify, path=SCHEDULE_FILE, now=None):
    """Send every reminder that is due. Returns the reminders delivered this time."""
    now = now or _now()
    delivered = []
    with _lock:
        reminders = load_schedule(path)
        for r in reminders:
            if r["status"] != "scheduled":
                continue
            due = datetime.fromisoformat(r["due_at"])
            if due > now:
                continue
            late = now - due > LATE_AFTER
            message = r["text"]
            if late:
                message += (
                    f" (missed at {due:%a %d %b, %H:%M} - the app wasn't running)"
                )
            shown = notify(
                "Voice Thought Capsule", message, speak=r.get("speak", False)
            )
            r["status"] = "missed" if late else "delivered"
            r["delivered_at"] = now.isoformat(timespec="seconds")
            r["notification_shown"] = bool(shown)
            delivered.append(r)
        if delivered:
            save_schedule(reminders, path)
    return delivered


def start_scheduler(notify=mac_notify, path=SCHEDULE_FILE, every=CHECK_EVERY_SECONDS):
    """Start the background checker. It stops automatically when the app stops."""

    def loop():
        while True:
            try:
                deliver_due(notify, path)
            except Exception as error:  # keep checking even if one attempt fails
                print(f"Reminder check failed: {error}")
            time.sleep(every)

    thread = threading.Thread(target=loop, daemon=True, name="reminder-scheduler")
    thread.start()
    return thread


# --- for the page ------------------------------------------------------------------

STATUS_LABELS = {
    "scheduled": "⏰ Scheduled",
    "delivered": "✅ Delivered",
    "missed": "⚠️ Missed (delivered late)",
    "cancelled": "✖️ Cancelled",
}


def schedule_table(path=SCHEDULE_FILE):
    """Rows: [status, reminder, due] - upcoming first, then the rest newest first."""
    reminders = load_schedule(path)
    upcoming = sorted(
        (r for r in reminders if r["status"] == "scheduled"), key=lambda r: r["due_at"]
    )
    others = sorted(
        (r for r in reminders if r["status"] != "scheduled"),
        key=lambda r: r["due_at"],
        reverse=True,
    )
    return [
        [
            STATUS_LABELS.get(r["status"], r["status"]),
            r["text"],
            datetime.fromisoformat(r["due_at"]).strftime("%a %d %b %Y, %H:%M"),
        ]
        for r in upcoming + others
    ]


def cancel_choices(path=SCHEDULE_FILE):
    return [
        (
            f"{datetime.fromisoformat(r['due_at']):%a %d %b, %H:%M} - {r['text'][:60]}",
            r["id"],
        )
        for r in sorted(load_schedule(path), key=lambda r: r["due_at"])
        if r["status"] == "scheduled"
    ]


def scheduled_for_items(path=SCHEDULE_FILE):
    """{item_id: due time} for reminders still waiting - used by Ask (Step 6)."""
    return {
        r["item_id"]: r["due_at"]
        for r in load_schedule(path)
        if r["status"] == "scheduled"
    }
