"""
linker.py - Step 5: connect related items across all your thoughts and
write clear summaries (using Gemini).

The result is saved in data/insights.json so it can be shown again later
(and used by Step 6 when you ask questions).
"""

import json
from datetime import datetime
from pathlib import Path

from google.genai import errors, types

import config
from storage import load_thoughts
from transcriber import friendly_error, make_client

INSIGHTS_FILE = Path(__file__).parent / "data" / "insights.json"

LINK_PROMPT = """You help someone see connections between their saved notes.

Below is a numbered list of items. Each one is a task, reminder or idea.

1. Group items that belong together into themes. A theme should join items that
   share a goal, topic, person, place or plan - also when they come from
   different recordings. Every theme needs at least 2 items. An item can be in
   at most one theme. Leave items out if they don't clearly connect to others.
2. For each theme write:
   - "title": 2 to 5 words
   - "summary": 1 or 2 plain sentences about what the items have in common and
     what the next step could be. Use only facts from the items - do not invent
     names, dates or details.
   - "items": the item numbers
3. Write an "overview": 2 or 3 sentences summarising everything, mentioning the
   most time-sensitive reminders and tasks first.

Reply with JSON only, in exactly this format:
{"overview": "...", "themes": [{"title": "...", "summary": "...", "items": [1, 4]}]}

The items:
"""


class LinkingError(Exception):
    """A problem we can explain to the user in plain words."""


def all_items(thoughts=None):
    """Every sorted item, oldest first, with info about the recording it came from."""
    rows = []
    for thought in thoughts if thoughts is not None else load_thoughts():
        for item in thought.get("items") or []:
            rows.append(
                {**item, "thought_id": thought["id"], "saved": thought["created_at"]}
            )
    return rows


def numbered_list(items):
    lines = []
    for n, item in enumerate(items, start=1):
        when = f" (when: {item['when']})" if item.get("when") else ""
        saved = datetime.fromisoformat(item["saved"]).strftime("%d %b")
        lines.append(f"{n}. [{item['type']}] {item['text']}{when} - recorded {saved}")
    return "\n".join(lines)


def parse_insights(reply_text, items):
    """Check Gemini's JSON and swap item numbers for real item IDs."""
    text = (reply_text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise LinkingError(
            "Gemini's answer was not in the expected format. Try again."
        ) from error
    if not isinstance(data, dict):
        raise LinkingError("Gemini's answer was not in the expected format. Try again.")

    used, themes = set(), []
    for raw in data.get("themes") or []:
        if not isinstance(raw, dict):
            continue
        ids = []
        for n in raw.get("items") or []:
            # keep only real item numbers, each item in one theme at most
            if isinstance(n, int) and 1 <= n <= len(items) and n not in used:
                used.add(n)
                ids.append(items[n - 1]["id"])
        title = str(raw.get("title") or "").strip()
        if len(ids) >= 2 and title:
            themes.append(
                {
                    "title": title,
                    "summary": str(raw.get("summary") or "").strip(),
                    "item_ids": ids,
                }
            )
    return {"overview": str(data.get("overview") or "").strip(), "themes": themes}


def save_insights(insights, item_ids, path=INSIGHTS_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "based_on_item_ids": sorted(
            item_ids
        ),  # lets us notice when new thoughts arrive
        **insights,
    }
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record


def load_insights(path=INSIGHTS_FILE):
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def connect_and_summarise(thoughts=None, client=None, model=None, path=INSIGHTS_FILE):
    """Ask Gemini to group related items, then save and return the result."""
    items = all_items(thoughts)
    if len(items) < 2:
        raise LinkingError(
            "Save and sort at least two items first - then there is something to connect."
        )
    client = client or make_client()
    model = model or config.get_model()
    try:
        response = client.models.generate_content(
            model=model,
            contents=LINK_PROMPT + numbered_list(items),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
    except errors.APIError as error:
        raise LinkingError(friendly_error(error)) from error
    except Exception as error:  # usually: no internet connection
        raise LinkingError(
            f"Could not reach Gemini. Check your internet connection. ({type(error).__name__}: {error})"
        ) from error
    insights = parse_insights(response.text, items)
    return save_insights(insights, [i["id"] for i in items], path)


ICONS = {"task": "✅", "reminder": "🔔", "idea": "💡"}


def insights_markdown(insights, thoughts=None):
    """Turn saved insights into readable text for the page."""
    if not insights:
        return "*No connections yet. Click **Connect and summarise**.*"

    items = {i["id"]: i for i in all_items(thoughts)}
    made = datetime.fromisoformat(insights["generated_at"]).strftime("%d %b %Y, %H:%M")
    parts = [f"*Made on {made}.*"]
    if set(items) != set(insights.get("based_on_item_ids", [])):
        parts.append(
            "⚠️ *Your thoughts have changed since then. Click "
            "**Connect and summarise** again to update.*"
        )
    if insights.get("overview"):
        parts.append(f"### Overview\n{insights['overview']}")
    if not insights.get("themes"):
        parts.append("*No clear connections were found between your items yet.*")
    for theme in insights.get("themes", []):
        lines = [f"### {theme['title']}", theme.get("summary", "")]
        for item_id in theme["item_ids"]:
            item = items.get(item_id)
            if item:  # skip items that were deleted later
                saved = datetime.fromisoformat(item["saved"]).strftime("%d %b, %H:%M")
                lines.append(
                    f"- {ICONS.get(item['type'], '')} {item['text']} "
                    f"<small>(recording {saved})</small>"
                )
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
