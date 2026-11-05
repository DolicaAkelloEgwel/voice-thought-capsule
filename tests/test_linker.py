"""
Tests for Step 5. They use a pretend Gemini client and temporary files,
so they run without internet and never touch your real data.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import errors

sys.path.insert(0, str(Path(__file__).parent.parent))
from linker import (
    LinkingError,
    all_items,
    connect_and_summarise,  # noqa: E402
    insights_markdown,
    load_insights,
    parse_insights,
)
from storage import add_thought, load_thoughts  # noqa: E402


class FakeModels:
    def __init__(self, reply_text=None, error=None):
        self.reply_text, self.error, self.calls = reply_text, error, []

    def generate_content(self, model, contents, config=None):
        self.calls.append(contents)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.reply_text)


def fake_client(**kwargs):
    return SimpleNamespace(models=FakeModels(**kwargs))


@pytest.fixture
def thoughts(tmp_path):
    db = tmp_path / "thoughts.json"
    add_thought(
        "a",
        path=db,
        items=[
            {"type": "idea", "text": "Plan a trip to the coast", "when": "next month"},
            {"type": "task", "text": "Book a dentist appointment", "when": None},
        ],
    )
    add_thought(
        "b",
        path=db,
        items=[{"type": "task", "text": "Check accommodation options", "when": None}],
    )
    return load_thoughts(db)


REPLY = json.dumps(
    {
        "overview": "A coastal trip is taking shape; the dentist is still to book.",
        "themes": [
            {
                "title": "Coastal trip",
                "summary": "Plan and book the trip.",
                "items": [1, 3],
            }
        ],
    }
)


def test_items_from_different_recordings_are_linked(thoughts, tmp_path):
    out = tmp_path / "insights.json"
    client = fake_client(reply_text=REPLY)
    result = connect_and_summarise(thoughts, client=client, model="m", path=out)

    trip, dentist, accommodation = all_items(thoughts)
    assert result["themes"][0]["item_ids"] == [trip["id"], accommodation["id"]]
    assert "Coastal trip" in result["themes"][0]["title"]
    assert load_insights(out)["overview"].startswith("A coastal trip")
    assert (
        "1. [idea] Plan a trip to the coast (when: next month)"
        in client.models.calls[0]
    )


def test_bad_numbers_and_one_item_themes_are_dropped(thoughts):
    items = all_items(thoughts)
    reply = json.dumps(
        {
            "overview": "x",
            "themes": [
                {
                    "title": "Real",
                    "summary": "s",
                    "items": [1, 3, 99, "2"],
                },  # 99 and "2" are invalid
                {"title": "Lonely", "summary": "s", "items": [2]},  # only one item
                {
                    "title": "Reused",
                    "summary": "s",
                    "items": [1, 2],
                },  # 1 already used -> only 1 left
            ],
        }
    )
    themes = parse_insights(reply, items)["themes"]
    assert [t["title"] for t in themes] == ["Real"]


def test_needs_at_least_two_items():
    with pytest.raises(LinkingError, match="at least two"):
        connect_and_summarise([], client=fake_client(reply_text=REPLY), model="m")


def test_api_error_is_friendly(thoughts, tmp_path):
    error = errors.ServerError(
        503, {"error": {"message": "busy", "status": "UNAVAILABLE"}}
    )
    with pytest.raises(LinkingError, match="busy or having problems"):
        connect_and_summarise(
            thoughts,
            client=fake_client(error=error),
            model="m",
            path=tmp_path / "i.json",
        )


def test_markdown_shows_themes_and_warns_when_out_of_date(thoughts, tmp_path):
    out = tmp_path / "insights.json"
    insights = connect_and_summarise(
        thoughts, client=fake_client(reply_text=REPLY), model="m", path=out
    )
    text = insights_markdown(insights, thoughts)
    assert "### Coastal trip" in text and "💡 Plan a trip to the coast" in text
    assert "changed since" not in text

    newer = thoughts + [
        {
            "id": "x",
            "created_at": thoughts[0]["created_at"],
            "items": [{"id": "new", "type": "task", "text": "New", "when": None}],
        }
    ]
    assert "changed since" in insights_markdown(insights, newer)


def test_markdown_when_nothing_made_yet():
    assert "Connect and summarise" in insights_markdown(None, [])
