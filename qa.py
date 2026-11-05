"""
qa.py - Step 6: ask questions about your saved thoughts.

It works in two stages, so answers are based on YOUR notes only:

  1. RETRIEVE - Gemini looks at the numbered list of your items and picks the
     ones relevant to the question. (This understands meaning, so a question
     about "food" can find "Try the new Italian restaurant".)
  2. ANSWER   - Gemini answers using ONLY the retrieved notes, and says so
     plainly if they don't contain the answer.

If nothing relevant is found, we say so and skip stage 2 - so the app
can't make up an answer.
"""

import json
from datetime import datetime

from google.genai import errors, types

import config
from linker import all_items
from reminders import scheduled_for_items
from storage import load_thoughts
from transcriber import friendly_error, make_client

MAX_ITEMS = 300  # newest items to search; plenty for a prototype
MAX_RETRIEVED = 10

RETRIEVE_PROMPT = """Below is a question and a numbered list of someone's saved notes
(tasks, reminders and ideas). Today is {today}. Each note shows the date it was
recorded, so questions like "yesterday", "this week" or "last Monday" can be matched
to the right notes.

Pick the notes that help answer the question. Include notes that are related in
meaning, not only ones with the same words. Pick at most {max} notes, most relevant
first. If no note is relevant, return an empty list.

Reply with JSON only, in exactly this format: {{"items": [3, 7]}}

Question: {question}

Notes:
{notes}
"""

ANSWER_PROMPT = """You answer questions about someone's own saved notes.
Today is {today}.

Rules:
- Use ONLY the notes below. Do not add facts, names, dates or advice that are not in them.
- If the notes don't answer the question, say so plainly.
- Each note shows the date it was recorded. Time words like "Friday" or "next weekend"
  are relative to the recording date, not today - mention this if it matters.
- Only say a notification is scheduled if the note itself says "notification scheduled
  for ...". Otherwise never claim a reminder or alarm has been set.
- {length_rule}
- Use plain text (no lists, no markdown) and speak to the person as "you".
  The answer may be read aloud.

Question: {question}

Notes:
{notes}
"""


# Faculty Step 5: "Test brief versus detailed answers".
ANSWER_LENGTHS = {
    "Brief": "Answer in 1 or 2 short, friendly sentences - just the key point.",
    "Detailed": (
        "Answer in up to 8 friendly sentences. Mention every relevant note, "
        "group related ones together, and say when they were recorded."
    ),
}


class QuestionError(Exception):
    """A problem we can explain to the user in plain words."""


def numbered_notes(items, scheduled=None):
    scheduled = scheduled or {}
    lines = []
    for n, item in enumerate(items, start=1):
        when = f" (when: {item['when']})" if item.get("when") else ""
        saved = datetime.fromisoformat(item["saved"]).strftime("%a %d %b %Y")
        alarm = ""
        if item.get("id") in scheduled:  # a real, saved schedule (reminders.py)
            due = datetime.fromisoformat(scheduled[item["id"]]).strftime(
                "%a %d %b %Y, %H:%M"
            )
            alarm = f" - notification scheduled for {due}"
        lines.append(
            f"{n}. [{item['type']}] {item['text']}{when} - recorded {saved}{alarm}"
        )
    return "\n".join(lines)


def _ask_gemini(client, model, prompt, json_reply):
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=(
                types.GenerateContentConfig(response_mime_type="application/json")
                if json_reply
                else None
            ),
        )
    except errors.APIError as error:
        raise QuestionError(friendly_error(error)) from error
    except Exception as error:  # usually: no internet connection
        raise QuestionError(
            f"Could not reach Gemini. Check your internet connection. ({type(error).__name__}: {error})"
        ) from error
    return (response.text or "").strip()


def parse_numbers(reply_text, count):
    """Read {"items": [..]} and keep only valid, unique item numbers."""
    text = reply_text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise QuestionError(
            "Gemini's answer was not in the expected format. Try again."
        ) from error
    numbers = data.get("items", []) if isinstance(data, dict) else data
    picked = []
    for n in numbers if isinstance(numbers, list) else []:
        if isinstance(n, int) and 1 <= n <= count and n not in picked:
            picked.append(n)
    return picked[:MAX_RETRIEVED]


def retrieve(question, items, client, model, today):
    """Stage 1: return the items relevant to the question (most relevant first)."""
    reply = _ask_gemini(
        client,
        model,
        RETRIEVE_PROMPT.format(
            max=MAX_RETRIEVED,
            today=today,
            question=question,
            notes=numbered_notes(items),
        ),
        json_reply=True,
    )
    return [items[n - 1] for n in parse_numbers(reply, len(items))]


def ask(question, thoughts=None, client=None, model=None, today=None, detail="Brief"):
    """
    Answer a question about the saved thoughts.
    `detail` is "Brief" or "Detailed".
    Returns (answer_text, notes_used) - notes_used is the list of retrieved items.
    """
    question = (question or "").strip()
    if not question:
        raise QuestionError("Type a question first.")
    items = all_items(thoughts if thoughts is not None else load_thoughts())[
        -MAX_ITEMS:
    ]
    if not items:
        return "You don't have any sorted notes yet, so there is nothing to search.", []

    client = client or make_client()
    model = model or config.get_model()

    today = today or datetime.now().strftime("%A %d %B %Y")
    found = retrieve(question, items, client, model, today)
    if not found:
        return "I couldn't find anything about that in your saved notes.", []

    length_rule = ANSWER_LENGTHS.get(detail, ANSWER_LENGTHS["Brief"])
    answer = _ask_gemini(
        client,
        model,
        ANSWER_PROMPT.format(
            today=today,
            length_rule=length_rule,
            question=question,
            notes=numbered_notes(found, scheduled_for_items()),
        ),
        json_reply=False,
    )
    return answer or "Sorry, no answer came back. Please try again.", found


ICONS = {"task": "✅", "reminder": "🔔", "idea": "💡"}


def notes_markdown(found):
    """List of retrieved notes, so the person can check where the answer came from."""
    if not found:
        return "*No notes were used.*"
    lines = [f"**Notes used for this answer ({len(found)}):**"]
    for item in found:
        when = f" — *{item['when']}*" if item.get("when") else ""
        saved = datetime.fromisoformat(item["saved"]).strftime("%d %b, %H:%M")
        lines.append(
            f"- {ICONS.get(item['type'], '')} {item['text']}{when} "
            f"<small>(recording {saved})</small>"
        )
    return "\n".join(lines)
