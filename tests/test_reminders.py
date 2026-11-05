"""
Tests for real reminders. A pretend clock and a pretend notifier are used, so
the tests run instantly, on any computer, and show no real notifications.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from reminders import (
    ReminderError,
    _applescript_text,
    cancel_choices,
    cancel_reminder,  # noqa: E402
    deliver_due,
    load_schedule,
    schedule_reminder,
    schedule_table,
    scheduled_for_items,
)

NOW = datetime(2026, 11, 1, 9, 0).astimezone()


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def __call__(self, title, message, speak=False):
        self.sent.append((message, speak))
        return True


@pytest.fixture
def path(tmp_path):
    return tmp_path / "schedule.json"


def test_schedule_then_deliver_on_time(path):
    schedule_reminder(
        "item-1",
        "Message Emma about dinner",
        NOW + timedelta(minutes=30),
        speak=True,
        path=path,
        now=NOW,
    )
    notifier = FakeNotifier()

    assert deliver_due(notifier, path, now=NOW + timedelta(minutes=29)) == []  # not yet
    delivered = deliver_due(notifier, path, now=NOW + timedelta(minutes=30, seconds=10))
    assert [r["status"] for r in delivered] == ["delivered"]
    assert notifier.sent == [("Message Emma about dinner", True)]

    deliver_due(notifier, path, now=NOW + timedelta(hours=1))  # never twice
    assert len(notifier.sent) == 1


def test_reminder_missed_while_app_was_closed_is_delivered_late_not_lost(path):
    schedule_reminder(
        "item-1", "Call Sarah", NOW + timedelta(minutes=5), path=path, now=NOW
    )
    notifier = FakeNotifier()
    delivered = deliver_due(
        notifier, path, now=NOW + timedelta(hours=3)
    )  # app started later
    assert delivered[0]["status"] == "missed"
    assert "missed at" in notifier.sent[0][0]


def test_past_times_and_missing_choices_are_refused(path):
    with pytest.raises(ReminderError, match="already passed"):
        schedule_reminder("item-1", "x", NOW - timedelta(minutes=1), path=path, now=NOW)
    with pytest.raises(ReminderError, match="date and time"):
        schedule_reminder("item-1", "x", None, path=path, now=NOW)
    with pytest.raises(ReminderError, match="Choose a reminder"):
        schedule_reminder(None, "", NOW + timedelta(hours=1), path=path, now=NOW)
    assert load_schedule(path) == []


def test_picker_time_without_zone_is_treated_as_local_time(path):
    naive = (NOW + timedelta(hours=1)).replace(tzinfo=None)
    r = schedule_reminder("item-1", "x", naive, path=path, now=NOW)
    assert datetime.fromisoformat(r["due_at"]).tzinfo is not None


def test_cancel_stops_delivery(path):
    r = schedule_reminder(
        "item-1", "Book dentist", NOW + timedelta(minutes=10), path=path, now=NOW
    )
    assert len(cancel_choices(path)) == 1
    cancel_reminder(r["id"], path)
    notifier = FakeNotifier()
    deliver_due(notifier, path, now=NOW + timedelta(hours=1))
    assert notifier.sent == [] and cancel_choices(path) == []
    with pytest.raises(ReminderError, match="haven't gone off"):
        cancel_reminder(r["id"], path)


def test_table_and_lookup_for_ask(path):
    schedule_reminder("item-2", "Later", NOW + timedelta(days=2), path=path, now=NOW)
    schedule_reminder("item-1", "Sooner", NOW + timedelta(hours=1), path=path, now=NOW)
    rows = schedule_table(path)
    assert [row[1] for row in rows] == ["Sooner", "Later"]  # upcoming first
    assert rows[0][0] == "⏰ Scheduled"
    assert set(scheduled_for_items(path)) == {"item-1", "item-2"}


def test_failed_notification_is_recorded_honestly(path):
    schedule_reminder("item-1", "x", NOW + timedelta(minutes=1), path=path, now=NOW)
    delivered = deliver_due(
        lambda t, m, speak=False: False, path, now=NOW + timedelta(minutes=1)
    )
    assert delivered[0]["notification_shown"] is False


def test_quotes_in_text_cannot_break_the_notification_script():
    assert _applescript_text('Say "hi" \\ bye') == 'Say \\"hi\\" \\\\ bye'
