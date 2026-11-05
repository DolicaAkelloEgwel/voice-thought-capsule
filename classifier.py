"""
classifier.py - Step 4: split a thought into items and label each one
as an idea, a task or a reminder (using Gemini).

Important: a "reminder" here is only a LABEL. Nothing is scheduled and
no notification will appear - the app has no scheduler.
"""

import json

from google.genai import errors, types
from pydantic import BaseModel, ValidationError, field_validator

import config
from transcriber import friendly_error, make_client

ITEM_TYPES = ("task", "reminder", "idea")

CLASSIFY_PROMPT = """You help someone organise their spoken notes.

Split the note below into separate, self-contained items and label each one:
- "task": something the speaker needs to do (an action), e.g. "Buy milk and eggs".
- "reminder": something tied to a specific time, date or event that the speaker
  must not forget, e.g. "Message Emma about dinner plans on Friday", appointments, deadlines.
- "idea": a thought, plan, wish or possibility to explore, without a firm commitment,
  e.g. "Start a small travel journal".

Rules:
- Write each item as one short, clear sentence, starting with a verb where natural,
  in the same language as the note.
- Keep the speaker's meaning. Do not invent names, dates or details.
- Leave out filler words and general comments (e.g. "I keep forgetting things").
- "when": copy the time words the speaker used (e.g. "Friday", "next weekend",
  "tomorrow"), or null if no time was mentioned.
- If there is nothing worth keeping, return an empty list.

Reply with JSON only, in exactly this format:
{"items": [{"type": "task", "text": "...", "when": null}]}

The note:
"""


class ClassificationError(Exception):
    """A problem we can explain to the user in plain words."""


class Item(BaseModel):
    type: str
    text: str
    when: str | None = None

    @field_validator("type")
    @classmethod
    def known_type(cls, value):
        value = value.strip().lower()
        return value if value in ITEM_TYPES else "idea"  # unknown labels become ideas

    @field_validator("text")
    @classmethod
    def not_empty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("empty item")
        return value

    @field_validator("when")
    @classmethod
    def blank_is_none(cls, value):
        value = (value or "").strip()
        return None if value.lower() in ("", "null", "none") else value


def parse_items(reply_text):
    """Turn Gemini's JSON reply into a list of clean item dicts."""
    text = (reply_text or "").strip()
    if text.startswith("```"):  # sometimes the JSON is wrapped in a code block
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ClassificationError(
            "Gemini's answer was not in the expected format. Try again."
        ) from error

    raw_items = data.get("items", []) if isinstance(data, dict) else data
    items = []
    for raw in raw_items if isinstance(raw_items, list) else []:
        try:
            items.append(Item.model_validate(raw).model_dump())
        except ValidationError:
            continue  # skip a broken item instead of failing the whole thought
    return items


def classify(text, client=None, model=None):
    """Return a list like [{"type": "task", "text": "Buy milk", "when": "tomorrow"}, ...]."""
    if not (text or "").strip():
        return []
    client = client or make_client()
    model = model or config.get_model()
    try:
        response = client.models.generate_content(
            model=model,
            contents=CLASSIFY_PROMPT + text,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
    except errors.APIError as error:
        raise ClassificationError(friendly_error(error)) from error
    except Exception as error:  # usually: no internet connection
        raise ClassificationError(
            f"Could not reach Gemini. Check your internet connection. ({type(error).__name__}: {error})"
        ) from error
    return parse_items(response.text)
