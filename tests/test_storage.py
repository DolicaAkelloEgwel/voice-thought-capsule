"""Tests for Step 3. They use a temporary file, never your real thoughts.json."""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from storage import add_thought, load_thoughts, thoughts_table  # noqa: E402


@pytest.fixture
def db(tmp_path):
    return tmp_path / "thoughts.json"


def test_no_file_means_no_thoughts(db):
    assert load_thoughts(db) == []


def test_thought_has_id_timestamp_and_text(db):
    t = add_thought("  Buy oat milk  ", audio_file="/x/thought_1.wav", duration_seconds=3.14, path=db)
    uuid.UUID(t["id"])                                      # a valid unique ID
    assert datetime.fromisoformat(t["created_at"]).tzinfo   # timestamp with time zone
    assert t["text"] == "Buy oat milk"
    assert t["audio_file"] == "thought_1.wav"               # only the name, not the full path
    assert t["duration_seconds"] == 3.1


def test_thoughts_survive_reloading(db):
    a = add_thought("first", path=db)
    b = add_thought("second", path=db)
    saved = load_thoughts(db)
    assert [t["text"] for t in saved] == ["first", "second"]
    assert a["id"] != b["id"]
    assert json.loads(db.read_text())["version"] == 1


def test_empty_thought_is_rejected(db):
    with pytest.raises(ValueError):
        add_thought("   ", path=db)
    assert load_thoughts(db) == []


def test_damaged_file_is_backed_up_not_lost(db):
    db.write_text("{ this is not valid json")
    assert load_thoughts(db) == []
    backups = list(db.parent.glob("thoughts_damaged_*.json"))
    assert len(backups) == 1 and "not valid" in backups[0].read_text()


def test_table_is_newest_first(db):
    add_thought("older", path=db)
    add_thought("newer", path=db)
    rows = thoughts_table(db)
    assert [r[2] for r in rows] == ["newer", "older"]
    assert len(rows[0][1]) == 8  # short ID
