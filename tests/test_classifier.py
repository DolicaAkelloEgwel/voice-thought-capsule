"""
Tests for Step 4. They use a pretend Gemini client, so they run
without internet and without using your API key.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import errors

sys.path.insert(0, str(Path(__file__).parent.parent))
from classifier import ClassificationError, classify, parse_items  # noqa: E402
from storage import load_thoughts  # noqa: E402
from storage import add_thought, items_table, set_items, unsorted_thoughts


class FakeModels:
    def __init__(self, reply_text=None, error=None):
        self.reply_text, self.error, self.calls = reply_text, error, []

    def generate_content(self, model, contents, config=None):
        self.calls.append((model, contents, config))
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.reply_text)


def fake_client(**kwargs):
    return SimpleNamespace(models=FakeModels(**kwargs))


GOOD_REPLY = json.dumps(
    {
        "items": [
            {"type": "task", "text": "Book a dentist appointment", "when": None},
            {"type": "reminder", "text": "Message Emma about dinner", "when": "Friday"},
            {"type": "idea", "text": "Start a travel journal", "when": ""},
        ]
    }
)


# --- classifier -------------------------------------------------------------


def test_classify_returns_labelled_items():
    client = fake_client(reply_text=GOOD_REPLY)
    items = classify("long note ...", client=client, model="m")
    assert [i["type"] for i in items] == ["task", "reminder", "idea"]
    assert items[1]["when"] == "Friday"
    assert items[2]["when"] is None  # blank time becomes None
    _, contents, config = client.models.calls[0]
    assert contents.endswith("long note ...")  # the note was sent
    assert config.response_mime_type == "application/json"


def test_code_fences_and_odd_labels_are_handled():
    reply = '```json\n{"items": [{"type": "TODO", "text": " Buy bread "}]}\n```'
    assert parse_items(reply) == [{"type": "idea", "text": "Buy bread", "when": None}]


def test_broken_items_are_skipped_not_fatal():
    reply = json.dumps(
        {"items": [{"type": "task", "text": ""}, {"type": "task", "text": "Call mum"}]}
    )
    assert [i["text"] for i in parse_items(reply)] == ["Call mum"]


def test_non_json_reply_gives_clear_error():
    with pytest.raises(ClassificationError, match="expected format"):
        parse_items("Sure! Here are your items: ...")


def test_empty_note_needs_no_api_call():
    client = fake_client(reply_text=GOOD_REPLY)
    assert classify("   ", client=client, model="m") == []
    assert client.models.calls == []


def test_api_error_is_friendly():
    error = errors.ClientError(
        429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}}
    )
    with pytest.raises(ClassificationError, match="Wait a minute"):
        classify("note", client=fake_client(error=error), model="m")


# --- storage of items -------------------------------------------------------


def test_items_get_their_own_ids_and_can_be_filtered(tmp_path):
    db = tmp_path / "thoughts.json"
    add_thought("note", items=parse_items(GOOD_REPLY), path=db)
    saved = load_thoughts(db)[0]["items"]
    assert len({i["id"] for i in saved}) == 3  # every item has a unique ID
    assert len(items_table("All", path=db)) == 3
    reminders = items_table("Reminders", path=db)
    assert (
        len(reminders) == 1
        and reminders[0][0] == "🔔 Reminder"
        and reminders[0][2] == "Friday"
    )


def test_unsorted_thoughts_can_be_sorted_later(tmp_path):
    db = tmp_path / "thoughts.json"
    old = add_thought("saved before step 4", path=db)  # no items yet
    assert [t["id"] for t in unsorted_thoughts(db)] == [old["id"]]
    set_items(old["id"], parse_items(GOOD_REPLY), path=db)
    assert unsorted_thoughts(db) == []
    assert len(items_table(path=db)) == 3
