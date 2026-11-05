"""
Tests for Step 6. They use a pretend Gemini client and temporary files,
so they run without internet and never touch your real data.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import errors

sys.path.insert(0, str(Path(__file__).parent.parent))
from qa import QuestionError, ask, notes_markdown, parse_numbers  # noqa: E402
from storage import add_thought, load_thoughts  # noqa: E402


class FakeModels:
    """Replies with the next answer from a list, and remembers every prompt."""
    def __init__(self, replies=None, error=None):
        self.replies, self.error, self.prompts = list(replies or []), error, []

    def generate_content(self, model, contents, config=None):
        self.prompts.append(contents)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.replies.pop(0))


def fake_client(**kwargs):
    return SimpleNamespace(models=FakeModels(**kwargs))


@pytest.fixture
def thoughts(tmp_path):
    db = tmp_path / "thoughts.json"
    add_thought("a", path=db, items=[
        {"type": "reminder", "text": "Message Emma about dinner plans", "when": "Friday"},
        {"type": "task", "text": "Book a dentist appointment", "when": None},
        {"type": "idea", "text": "Try the new Italian restaurant", "when": None}])
    return load_thoughts(db)


def test_retrieves_first_then_answers_only_from_those_notes(thoughts):
    client = fake_client(replies=['{"items": [1, 3]}',
                                  "You planned to message Emma about Friday's dinner."])
    answer, used = ask("What are my dinner plans?", thoughts, client=client, model="m",
                       today="Saturday 31 October 2026")

    assert answer.startswith("You planned")
    assert [i["text"] for i in used] == ["Message Emma about dinner plans",
                                         "Try the new Italian restaurant"]
    retrieve_prompt, answer_prompt = client.models.prompts
    assert "Book a dentist appointment" in retrieve_prompt      # stage 1 sees everything
    assert "Book a dentist appointment" not in answer_prompt    # stage 2 sees only retrieved notes
    assert "Message Emma" in answer_prompt and "31 October 2026" in answer_prompt


def test_nothing_relevant_means_no_made_up_answer(thoughts):
    client = fake_client(replies=['{"items": []}'])
    answer, used = ask("What is my bank PIN?", thoughts, client=client, model="m")
    assert "couldn't find" in answer and used == []
    assert len(client.models.prompts) == 1                      # stage 2 was skipped


def test_invalid_numbers_are_ignored():
    assert parse_numbers('{"items": [2, 2, 0, 9, "1", 1]}', count=3) == [2, 1]


def test_empty_question_is_rejected(thoughts):
    with pytest.raises(QuestionError, match="Type a question"):
        ask("   ", thoughts, client=fake_client(), model="m")


def test_no_notes_yet():
    answer, used = ask("Anything?", [], client=fake_client(), model="m")
    assert "don't have any sorted notes" in answer and used == []


def test_api_error_is_friendly(thoughts):
    error = errors.ClientError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    with pytest.raises(QuestionError, match="Wait a minute"):
        ask("Dinner?", thoughts, client=fake_client(error=error), model="m")


def test_notes_used_are_listed(thoughts):
    client = fake_client(replies=['{"items": [1]}', "Message Emma."])
    _, used = ask("Friday?", thoughts, client=client, model="m")
    text = notes_markdown(used)
    assert "Notes used for this answer (1)" in text and "🔔 Message Emma" in text and "Friday" in text


def test_answer_only_mentions_real_schedules():
    from qa import numbered_notes
    items = [{"id": "a", "type": "reminder", "text": "Call Sarah", "when": None,
              "saved": "2026-11-01T09:00:00+00:00"},
             {"id": "b", "type": "reminder", "text": "Message Emma", "when": "Friday",
              "saved": "2026-11-01T09:00:00+00:00"}]
    text = numbered_notes(items, {"a": "2026-11-02T10:00:00+00:00"})
    assert "Call Sarah - recorded Sun 01 Nov 2026 - notification scheduled for Mon 02 Nov 2026, 10:00" in text
    assert text.splitlines()[1].endswith("recorded Sun 01 Nov 2026")  # unscheduled: no schedule claimed


def test_note_finder_knows_today_for_yesterday_questions(thoughts):
    client = fake_client(replies=['{"items": [3]}', "Yesterday you had the idea to try the Italian restaurant."])
    ask("What were my ideas from yesterday?", thoughts, client=client, model="m",
        today="Sunday 01 November 2026")
    retrieve_prompt = client.models.prompts[0]
    assert "Today is Sunday 01 November 2026" in retrieve_prompt   # stage 1 can work out "yesterday"
    assert "- recorded " in retrieve_prompt                         # ...from each note's recording date


@pytest.mark.parametrize("detail, expected", [("Brief", "1 or 2 short"), ("Detailed", "up to 8")])
def test_brief_or_detailed_answers(thoughts, detail, expected):
    client = fake_client(replies=['{"items": [1]}', "An answer."])
    ask("Dinner?", thoughts, client=client, model="m", detail=detail)
    assert expected in client.models.prompts[1]


def test_unknown_length_falls_back_to_brief(thoughts):
    client = fake_client(replies=['{"items": [1]}', "An answer."])
    ask("Dinner?", thoughts, client=client, model="m", detail="Banana")
    assert "1 or 2 short" in client.models.prompts[1]
