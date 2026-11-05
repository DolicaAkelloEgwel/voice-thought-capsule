"""Tests for Step 8: permission, edit, delete, undo and the bin. Uses temporary folders only."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from consent import ConsentError, give_consent, has_consent, require_consent, withdraw_consent  # noqa: E402
from editing import EditError, Store  # noqa: E402
from storage import add_thought, load_thoughts  # noqa: E402


@pytest.fixture
def store(tmp_path):
    s = Store(thoughts=tmp_path / "thoughts.json", undo=tmp_path / "undo.json",
              recordings=tmp_path / "recordings", bin_dir=tmp_path / "bin")
    s.recordings.mkdir()
    (s.recordings / "thought_1.wav").write_bytes(b"audio")
    add_thought("I need to book the dentist and maybe paint", audio_file="thought_1.wav",
                path=s.thoughts, items=[
                    {"type": "task", "text": "Book the dentist", "when": None},
                    {"type": "idea", "text": "Start painting", "when": None}])
    return s


def items(store):
    return [(i["type"], i["text"], i.get("when")) for t in load_thoughts(store.thoughts)
            for i in t.get("items") or []]


def item_id(store, text):
    return next(i for label, i in store.item_choices() if text in label)


# --- permission -------------------------------------------------------------

def test_no_recording_without_permission(tmp_path):
    path = tmp_path / "consent.json"
    assert not has_consent(path)
    with pytest.raises(ConsentError):
        require_consent(path)
    give_consent(path)
    require_consent(path)                       # no error now
    withdraw_consent(path)
    assert not has_consent(path)


# --- edit -------------------------------------------------------------------

def test_edit_changes_text_type_and_time(store):
    store.edit_item(item_id(store, "dentist"), "Book the dentist for a check-up", "reminder", "Monday")
    assert ("reminder", "Book the dentist for a check-up", "Monday") in items(store)


def test_edit_rejects_empty_text_and_no_change(store):
    dentist = item_id(store, "dentist")
    with pytest.raises(EditError, match="can't be empty"):
        store.edit_item(dentist, "  ", "task", "")
    with pytest.raises(EditError, match="Nothing was changed"):
        store.edit_item(dentist, "Book the dentist", "task", "")


# --- delete + undo ----------------------------------------------------------

def test_delete_item_then_undo(store):
    store.delete_item(item_id(store, "painting"))
    assert [t for _, t, _ in items(store)] == ["Book the dentist"]
    assert "Start painting" in store.last_change()
    store.undo_last()
    assert [t for _, t, _ in items(store)] == ["Book the dentist", "Start painting"]


def test_undo_edit_restores_old_text(store):
    store.edit_item(item_id(store, "dentist"), "Changed", "task", "")
    store.undo_last()
    assert ("task", "Book the dentist", None) in items(store)


def test_delete_recording_moves_audio_to_bin_and_undo_brings_it_back(store):
    thought_id = store.thought_choices()[0][1]
    store.delete_thought(thought_id)
    assert load_thoughts(store.thoughts) == []
    assert not (store.recordings / "thought_1.wav").exists()
    assert store.bin_count() == 1

    store.undo_last()
    assert len(load_thoughts(store.thoughts)) == 1
    assert (store.recordings / "thought_1.wav").read_bytes() == b"audio"
    assert store.bin_count() == 0


def test_undo_never_removes_thoughts_recorded_later(store):
    store.delete_item(item_id(store, "painting"))
    add_thought("A newer thought", path=store.thoughts, items=[{"type": "idea", "text": "Newer", "when": None}])
    store.undo_last()
    texts = [t for _, t, _ in items(store)]
    assert "Start painting" in texts and "Newer" in texts


def test_empty_bin_is_permanent(store):
    store.delete_thought(store.thought_choices()[0][1])
    assert "Permanently deleted 1" in store.empty_bin()
    assert store.bin_count() == 0
    message = store.undo_last()                 # the transcript comes back, the audio can't
    assert "permanently deleted" in message
    with pytest.raises(EditError, match="already empty"):
        store.empty_bin()


def test_nothing_to_undo(store):
    assert store.last_change() is None
    with pytest.raises(EditError, match="nothing to undo"):
        store.undo_last()


def test_undo_history_is_limited(store):
    dentist = item_id(store, "dentist")
    for n in range(25):
        store.edit_item(dentist, f"Version {n}", "task", "")
    assert len(store._history()) == 20
