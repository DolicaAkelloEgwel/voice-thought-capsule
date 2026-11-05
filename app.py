"""
Voice Thought Capsule - all 8 steps: record, transcribe, save, sort, connect, ask,
hear the answers - and edit, delete and undo, with clear recording permission.

Run with:   python app.py
Then open:  http://127.0.0.1:7860  in Chrome.
"""

import gradio as gr

import config
from classifier import ClassificationError, classify
from consent import (CONSENT_TEXT, ConsentError, give_consent, has_consent,
                     require_consent, withdraw_consent)
from editing import EditError, Store
from exhibition import (DEFAULT_INTRO, DEFAULT_OUTRO, EXHIBITION_DIR,
                        ExhibitionError, create_demo, demo_seconds, list_demos)
from linker import (LinkingError, connect_and_summarise, insights_markdown,
                    load_insights)
from privacy import (delete_all_audio, delete_audio_enabled, remove_file,
                     set_delete_audio)
from qa import QuestionError, ask, notes_markdown
from recorder import get_duration_seconds, save_recording
from reminders import (ReminderError, cancel_choices, cancel_reminder,
                       schedule_reminder, schedule_table, start_scheduler)
from speaker import SpeechError, speak_to_file
from storage import (THOUGHTS_FILE, add_thought, items_table, load_thoughts,
                     set_items, thoughts_table, unsorted_thoughts)
from transcriber import TranscriptionError, transcribe

ITEM_HEADERS = ["Type", "Item", "When (as you said it)", "Saved", "From thought"]
THOUGHT_HEADERS = ["Saved", "ID", "Full transcript"]
FILTERS = ["All", "Tasks", "Reminders", "Ideas"]
API_ERRORS = (
    TranscriptionError,
    ClassificationError,
    LinkingError,
    QuestionError,
    config.MissingKeyError,
)
ITEM_TYPES = ["task", "reminder", "idea"]
store = Store()  # edit / delete / undo (Step 8)
EXAMPLE_QUESTIONS = [
    "What do I need to do before Friday?",
    "What are my travel plans?",
    "Which ideas do I have about my health?",
    "Who did I promise to help?",
]


def count_summary(items):
    """e.g. '3 tasks, 1 reminder, 2 ideas'"""
    parts = []
    for kind in ("task", "reminder", "idea"):
        n = sum(1 for item in items if item["type"] == kind)
        if n:
            parts.append(f"{n} {kind}{'s' if n > 1 else ''}")
    return ", ".join(parts) or "no items"


def save_and_transcribe(audio_path, show):
    """
    Called by 'Save and transcribe'.
    Returns (status, transcript, items, transcripts, insights, recorder).
    """
    audio_deleted = False

    def result(message, text=""):
        # Clear the recorder when its audio was deleted (privacy setting).
        recorder = gr.update(value=None) if audio_deleted else gr.update()
        return (
            message,
            text,
            items_table(show),
            thoughts_table(),
            current_insights(),
            recorder,
        )

    def delete_audio_now(saved_path):
        """Privacy setting: remove our copy AND Gradio's temporary copy."""
        nonlocal audio_deleted
        remove_file(saved_path)
        remove_file(audio_path)
        audio_deleted = True

    # Step 8 - recording permission is checked here too, not only on screen.
    try:
        require_consent()
    except ConsentError as error:
        gr.Warning(str(error))
        return result(str(error))

    # Step 1 - keep a copy of the recording.
    try:
        saved_path = save_recording(audio_path)
    except (ValueError, FileNotFoundError) as error:
        gr.Warning(str(error))  # friendly pop-up instead of a crash
        return result("Nothing saved - record something first, then click the button.")

    seconds = get_duration_seconds(saved_path)
    saved_msg = (
        f"Recording saved ({seconds:.1f} s)"
        if seconds is not None
        else "Recording saved"
    )
    privacy_on = delete_audio_enabled()

    # Step 2 - speech to text. If this fails, the recording is ALWAYS kept,
    # even with the privacy setting on, so the thought isn't lost.
    try:
        text = transcribe(saved_path)
    except API_ERRORS as error:
        gr.Warning(str(error))
        kept = " The audio was kept so your thought isn't lost." if privacy_on else ""
        return result(f"{saved_msg}. Transcription failed: {error}{kept}")
    if not text:
        if privacy_on:
            delete_audio_now(saved_path)
            return result(
                "No speech was detected, so nothing was kept (the audio was deleted)."
            )
        return result(f"{saved_msg}. No speech was detected, so no thought was added.")

    if privacy_on:
        delete_audio_now(saved_path)
        saved_msg = "Transcribed, then the audio was deleted (privacy setting)"
    audio_name = None if audio_deleted else saved_path

    # Step 4 - split into labelled items. If this fails, we still keep the thought
    # and it can be sorted later with the 'Sort earlier thoughts' button.
    try:
        items = classify(text)
    except API_ERRORS as error:
        gr.Warning(str(error))
        add_thought(text, audio_file=audio_name, duration_seconds=seconds, items=None)
        return result(
            f"{saved_msg}. Thought saved, but sorting failed: {error} "
            "Use 'Sort earlier thoughts' to try again.",
            text,
        )

    # Step 3 - store everything in data/thoughts.json.
    thought = add_thought(
        text, audio_file=audio_name, duration_seconds=seconds, items=items
    )
    return result(
        f"{saved_msg}. Thought {thought['id'][:8]} saved and sorted into "
        f"{count_summary(items)}.",
        text,
    )


def change_privacy(enabled):
    set_delete_audio(enabled)
    return (
        "🔒 From now on, each recording is deleted right after it is transcribed. Only the text is kept."
        if enabled
        else "Recordings will be kept in `data/recordings/`."
    )


# --- Extra: real reminders ----------------------------------------------------------

SCHEDULE_HEADERS = ["Status", "Reminder", "When"]


def reminder_item_choices():
    """All items for the drop-down, with 🔔 reminders listed first."""
    choices = store.item_choices()
    return sorted(choices, key=lambda c: not c[0].startswith("🔔"))


def refresh_reminders():
    return (
        gr.update(choices=reminder_item_choices(), value=None),
        schedule_table(),
        gr.update(choices=cancel_choices(), value=None),
    )


def schedule_clicked(item_id, due, speak):
    try:
        if not item_id:
            raise ReminderError("Choose a reminder first.")
        text = store.get_item(item_id)["text"]
        reminder = schedule_reminder(item_id, text, due, speak=speak)
    except (ReminderError, EditError) as error:
        gr.Warning(str(error))
        # Keep the person's choices so they only need to fix what was wrong.
        return f"⚠️ {error}", gr.update(), schedule_table(), gr.update()
    when = due.strftime("%a %d %b %Y at %H:%M")
    return (
        f"⏰ Scheduled: **{reminder['text']}** on **{when}**. You'll get a Mac notification "
        "then - as long as the app is running.",
        *refresh_reminders(),
    )


def cancel_clicked(reminder_id):
    try:
        if not reminder_id:
            raise ReminderError("Choose a scheduled reminder to cancel.")
        reminder = cancel_reminder(reminder_id)
    except ReminderError as error:
        gr.Warning(str(error))
        return f"⚠️ {error}", gr.update(), schedule_table(), gr.update()
    return (f"✖️ Cancelled: {reminder['text']}", *refresh_reminders())


# --- Faculty Step 6: exhibition version -----------------------------------------------


def exhibition_thought_choices():
    """Recordings for the demo, marked with whose voice will be heard."""
    thoughts = {t["id"]: t for t in load_thoughts()}
    choices = []
    for label, thought_id in store.thought_choices():
        has_audio = bool(thoughts[thought_id].get("audio_file"))
        choices.append(
            (
                f"{label}  {'🎙️ your voice' if has_audio else '🤖 computer voice'}",
                thought_id,
            )
        )
    return choices


def demo_choices():
    return [
        (f"{p.stem.removeprefix('demo_')}  ({demo_seconds(p):.0f} s)", str(p))
        for p in list_demos()
    ]


def refresh_exhibition():
    demos = demo_choices()
    return (
        gr.update(choices=exhibition_thought_choices()),
        gr.update(choices=demos, value=demos[0][1] if demos else None),
    )


def make_demo(thought_id, question, detail, intro, outro, narration, max_seconds):
    """Create one exhibition demo from a real thought, question and Gemini answer."""

    def fail(message):
        gr.Warning(message)
        return f"⚠️ {message}", "", "", None, None, gr.update()

    thoughts = {t["id"]: t for t in load_thoughts()}
    if thought_id not in thoughts:
        return fail("Choose a thought for the demo first.")
    if not (question or "").strip():
        return fail("Type the question to ask in the demo.")
    try:
        answer, _ = ask(
            question, list(thoughts.values()), detail=detail
        )  # the REAL answer
        wav, txt, script = create_demo(
            thoughts[thought_id],
            question,
            answer,
            tts=speak_to_file,
            intro=intro,
            outro=outro,
            narration=narration,
            max_thought_seconds=max_seconds,
        )
    except (*API_ERRORS, ExhibitionError, SpeechError) as error:
        return fail(str(error))
    demos = demo_choices()
    return (
        f"✅ Demo saved: `exhibition/{wav.name}` ({demo_seconds(wav):.0f} seconds) "
        f"and its script `exhibition/{txt.name}`.",
        answer,
        script,
        str(wav),
        [str(wav), str(txt)],
        gr.update(choices=demos, value=str(wav)),
    )


def delete_existing_audio(show, understood):
    if not understood:
        gr.Warning("Tick the box to confirm - deleting audio can't be undone.")
        return "⚠️ Tick the box first.", False, thoughts_table()
    n = delete_all_audio(THOUGHTS_FILE)
    return (
        f"🗑️ Permanently deleted {n} recording{'s' if n != 1 else ''}. All your text was kept.",
        False,
        thoughts_table(),
    )


def current_insights():
    """The last saved connections, as text for the page."""
    return insights_markdown(load_insights(), load_thoughts())


def connect_thoughts():
    """Called by 'Connect and summarise' (Step 5)."""
    try:
        insights = connect_and_summarise(load_thoughts())
    except API_ERRORS as error:
        gr.Warning(str(error))
        return f"❌ {error}\n\n" + current_insights()
    return insights_markdown(insights, load_thoughts())


def ask_question(question, read_aloud, detail="Brief"):
    """Called by 'Ask' (Steps 6-7). Returns (answer, notes used, spoken answer audio)."""
    try:
        answer, found = ask(question, load_thoughts(), detail=detail)
    except API_ERRORS as error:
        gr.Warning(str(error))
        return f"Sorry - {error}", "", None

    audio = None
    if read_aloud:
        try:
            audio = str(speak_to_file(answer))  # Mac's built-in voice, works offline
        except SpeechError as error:
            gr.Warning(str(error))  # the written answer is still shown
    return answer, notes_markdown(found), audio


def ask_by_voice(audio_path, read_aloud, detail="Brief"):
    """
    Extra: ask a question by voice. Returns (question text, answer, notes used, spoken answer).

    The spoken question is only transcribed - it is NOT saved to data/recordings/
    or added to your thoughts.
    """
    try:
        require_consent()  # recording a question needs the same permission
    except ConsentError as error:
        gr.Warning(str(error))
        return "", str(error), "", None
    if not audio_path:
        gr.Warning(
            "No question recorded. Press Record, ask your question, then press Stop."
        )
        return "", "", "", None
    try:
        question_text = transcribe(audio_path)
    except API_ERRORS as error:
        gr.Warning(str(error))
        return "", f"Sorry - {error}", "", None
    finally:
        remove_file(audio_path)  # the spoken question is never kept
    if not question_text:
        return (
            "",
            "Sorry, I didn't catch a question. Please try again, a little closer to the microphone.",
            "",
            None,
        )
    return (question_text, *ask_question(question_text, read_aloud, detail))


def sort_earlier_thoughts(show):
    """Sort thoughts that were saved before Step 4 (or whose sorting failed)."""
    waiting = unsorted_thoughts()
    if not waiting:
        return "All thoughts are already sorted.", items_table(show)
    done = 0
    for thought in waiting:
        try:
            set_items(thought["id"], classify(thought["text"]))
            done += 1
        except API_ERRORS as error:
            gr.Warning(str(error))
            return (
                f"Sorted {done} of {len(waiting)} thoughts, then stopped: {error}",
                items_table(show),
            )
    return f"Sorted {done} earlier thought{'s' if done > 1 else ''}.", items_table(show)


# --- Step 8: permission -------------------------------------------------------


def allow_recording(agreed):
    if not agreed:
        gr.Warning("Please tick the box to confirm you agree first.")
        return gr.update(), gr.update(), gr.update()
    give_consent()
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        "✅ Recording permission given.",
    )


def withdraw_recording():
    withdraw_consent()
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        False,
        "Recording permission withdrawn. Your saved thoughts are kept - delete them in ✏️ Edit.",
    )


def consent_screens():
    allowed = has_consent()
    return gr.update(visible=not allowed), gr.update(visible=allowed)


# --- Step 8: edit, delete, undo ------------------------------------------------


def refresh_all(show):
    """Everything that can change after an edit, delete or undo."""
    last = store.last_change()
    bin_n = store.bin_count()
    return (
        items_table(show),
        thoughts_table(),
        current_insights(),
        gr.update(choices=store.item_choices(), value=None),
        gr.update(choices=store.thought_choices(), value=None),
        f"**Last change:** {last}" if last else "*No changes to undo.*",
        (
            f"🗑️ **{bin_n}** deleted recording{'s' if bin_n != 1 else ''} in the bin."
            if bin_n
            else "🗑️ The bin is empty."
        ),
        "",
        None,
        "",
    )  # clear the edit fields


def run_change(action, show, *args):
    """Run an edit/delete/undo and return a status line plus refreshed screens."""
    try:
        message = "✅ " + action(*args)
    except EditError as error:
        message = f"⚠️ {error}"
    return (message, *refresh_all(show))


def pick_item(item_id):
    """Fill the edit fields when an item is chosen."""
    if not item_id:
        return "", None, ""
    try:
        item = store.get_item(item_id)
    except EditError as error:
        gr.Warning(str(error))
        return "", None, ""
    return item["text"], item["type"], item.get("when") or ""


def need_selection(value, what):
    if not value:
        raise EditError(f"Choose {what} first.")
    return value


def save_edit(show, item_id, text, item_type, when):
    return run_change(
        lambda: store.edit_item(
            need_selection(item_id, "an item"), text, item_type, when
        ),
        show,
    )


def delete_item(show, item_id):
    return run_change(
        lambda: store.delete_item(need_selection(item_id, "an item")), show
    )


def delete_recording(show, thought_id):
    return run_change(
        lambda: store.delete_thought(need_selection(thought_id, "a recording")), show
    )


def undo(show):
    return run_change(store.undo_last, show)


def empty_bin(show, understood):
    def action():
        if not understood:
            raise EditError(
                "Tick the box to confirm - emptying the bin can't be undone."
            )
        return store.empty_bin()

    return (*run_change(action, show), False)


with gr.Blocks(title="Voice Thought Capsule") as demo:
    gr.Markdown(
        "# Voice Thought Capsule\n"
        "Recordings and thoughts are stored on this computer in the `data/` folder. "
        "To transcribe, sort, connect and answer, the audio and text are sent to Google's Gemini service."
    )

    with gr.Tabs():
        with gr.Tab("🎙️ Record"):
            allowed = has_consent()
            with gr.Group(
                visible=not allowed
            ) as consent_box:  # shown until permission is given
                gr.Markdown(CONSENT_TEXT, padding=True)
                agree = gr.Checkbox(
                    label="I understand and agree to record my voice for this prototype."
                )
                allow_button = gr.Button("Allow recording", variant="primary")
            with gr.Group(
                visible=allowed
            ) as record_box:  # shown once permission is given
                gr.Markdown(
                    "Press **Record**, speak, press **Stop**, then click **Save and transcribe**.",
                    padding=True,
                )
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    format="wav",
                    label="Your thought",
                )
                save_button = gr.Button("Save and transcribe", variant="primary")
                status = gr.Textbox(label="Status", interactive=False)
                transcript = gr.Textbox(
                    label="What you said", lines=4, interactive=False
                )
                with gr.Accordion("🔒 Privacy settings", open=False):
                    delete_audio = gr.Checkbox(
                        value=delete_audio_enabled(),
                        label="Delete audio after transcribing",
                        info="Each recording is deleted as soon as it has been turned into text; only "
                        "the text is kept. If transcription fails, the audio is kept so nothing is lost.",
                    )
                    privacy_status = gr.Markdown()
                    gr.Markdown("**Recordings you already made**", padding=True)
                    understood_audio = gr.Checkbox(
                        label="I understand this permanently deletes all saved audio (the text is kept). "
                        "This can't be undone."
                    )
                    delete_all_button = gr.Button(
                        "Delete all saved audio now", variant="stop", size="sm"
                    )
                withdraw_button = gr.Button(
                    "Withdraw recording permission", size="sm", variant="secondary"
                )
            consent_status = gr.Markdown()

        with gr.Tab("📋 Sorted items"):
            gr.Markdown(
                "🔔 *Reminders are labels only, until you schedule one in the **⏰ Reminders** "
                "tab. Only scheduled reminders give you a Mac notification.*"
            )
            show = gr.Radio(FILTERS, value="All", label="Show", interactive=True)
            items = gr.Dataframe(
                headers=ITEM_HEADERS,
                value=[],
                interactive=False,
                wrap=True,
                column_widths=["13%", "45%", "16%", "13%", "13%"],
            )
            with gr.Row():
                sort_button = gr.Button("Sort earlier thoughts", size="sm")
                sort_status = gr.Markdown()
            with gr.Accordion("Full transcripts", open=False):
                thoughts = gr.Dataframe(
                    headers=THOUGHT_HEADERS,
                    value=[],
                    interactive=False,
                    wrap=True,
                    column_widths=["20%", "12%", "68%"],
                )

        with gr.Tab("🔗 Connections"):
            gr.Markdown(
                "Groups related items from all your recordings into themes, "
                "with a short summary of each."
            )
            connect_button = gr.Button("Connect and summarise")
            insights = gr.Markdown()

        with gr.Tab("❓ Ask"):
            gr.Markdown(
                "Ask a question about your saved thoughts. The app first **finds the "
                "relevant notes**, then answers **only from those notes**, and shows "
                "which ones it used."
            )
            with gr.Row(equal_height=True):
                with gr.Column(scale=3):
                    question = gr.Textbox(
                        label="Type your question",
                        placeholder="e.g. What do I need to do before Friday?",
                    )
                    gr.Examples(
                        EXAMPLE_QUESTIONS, inputs=question, label="Try one of these"
                    )
                with gr.Column(scale=2):
                    voice_question = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        format="wav",
                        label="…or ask by voice: press Record, ask, press Stop",
                    )
                    gr.Markdown(
                        "<small>Your spoken question is answered as soon as you press Stop. "
                        "It is sent to Gemini to be transcribed but is <b>not</b> saved.</small>"
                    )
            detail = gr.Radio(
                ["Brief", "Detailed"],
                value="Brief",
                label="Answer length",
                info="Brief: 1-2 sentences. Detailed: covers every relevant note.",
            )
            read_aloud = gr.Checkbox(
                value=True,
                label="🔊 Read answers aloud",
                info="Uses your Mac's built-in voice (offline). Sound plays "
                "through your Mac's current output, e.g. headphones.",
            )
            ask_button = gr.Button("Ask", variant="primary")
            answer = gr.Textbox(label="Answer", lines=3, interactive=False)
            spoken = gr.Audio(
                label="Spoken answer (press ▶ to hear it again)",
                type="filepath",
                autoplay=True,
                interactive=False,
            )
            notes_used = gr.Markdown()

        with gr.Tab("⏰ Reminders") as reminders_tab:
            gr.Markdown(
                "Choose an item and a time to get a **real Mac notification** (and, if you like, hear "
                "it spoken).\n\n"
                "⚠️ **Notifications only appear while the app is running** (Terminal open, Mac awake). "
                "If the app was closed at that time, the reminder is shown as *missed* and delivered "
                "as soon as you start the app again."
            )
            reminder_pick = gr.Dropdown(label="Remind me about", choices=[], value=None)
            with gr.Row():
                due_picker = gr.DateTime(
                    label="When (your Mac's local time)",
                    include_time=True,
                    type="datetime",
                )
                speak_reminder = gr.Checkbox(value=True, label="🔊 Also say it aloud")
            schedule_button = gr.Button("Schedule reminder", variant="primary")
            reminder_status = gr.Markdown()
            schedule_list = gr.Dataframe(
                headers=SCHEDULE_HEADERS,
                value=[],
                interactive=False,
                wrap=True,
                column_widths=["22%", "50%", "28%"],
            )
            with gr.Row():
                cancel_pick = gr.Dropdown(
                    label="Cancel a scheduled reminder", choices=[], value=None, scale=3
                )
                cancel_button = gr.Button("Cancel reminder", variant="stop", scale=1)
            reminder_timer = gr.Timer(20)  # refresh the list so new deliveries show up

        with gr.Tab("✏️ Edit") as edit_tab:
            edit_status = gr.Markdown()
            with gr.Row():
                undo_info = gr.Markdown()
                undo_button = gr.Button("↩️ Undo last change", size="sm")

            gr.Markdown("### Edit or delete an item")
            item_pick = gr.Dropdown(label="Choose an item", choices=[], value=None)
            edit_text = gr.Textbox(label="Item text")
            with gr.Row():
                edit_type = gr.Radio(ITEM_TYPES, label="Type")
                edit_when = gr.Textbox(label="When (optional, e.g. Friday)")
            with gr.Row():
                save_edit_button = gr.Button("Save changes", variant="primary")
                delete_item_button = gr.Button("Delete item", variant="stop")

            gr.Markdown(
                "### Delete a whole recording\n"
                "Removes its transcript and all its items. The audio goes to the bin."
            )
            thought_pick = gr.Dropdown(
                label="Choose a recording", choices=[], value=None
            )
            delete_thought_button = gr.Button("Delete recording", variant="stop")

            gr.Markdown("### Bin")
            bin_info = gr.Markdown()
            understood = gr.Checkbox(
                label="I understand that emptying the bin deletes the audio "
                "permanently. This can't be undone."
            )
            empty_bin_button = gr.Button(
                "Empty bin permanently", variant="stop", size="sm"
            )

        with gr.Tab("🎧 Exhibition") as exhibition_tab:
            gr.Markdown(
                "Turn one real interaction into a **single audio file for headphones**: intro → your "
                "thought → the question → the spoken answer → outro, with short narration so visitors "
                "understand it **without a screen**. No microphone is used and **no visitor voice data** "
                "is collected. Files are saved in the `exhibition/` folder."
            )
            gr.Markdown("### 1. Create a demo")
            demo_thought = gr.Dropdown(
                label="Thought to play",
                choices=[],
                value=None,
                info="🎙️ = your recorded voice is played. 🤖 = the audio was "
                "deleted, so the computer voice reads the text.",
            )
            gr.Markdown(
                "⚠️ *The demo contains **your own recorded voice** and the text of that thought. "
                "Only choose thoughts you are happy for visitors to hear.*"
            )
            with gr.Row():
                demo_question = gr.Textbox(
                    label="Question to ask",
                    value="What do I need to do this week?",
                    scale=3,
                )
                demo_detail = gr.Radio(
                    ["Brief", "Detailed"], value="Brief", label="Answer length", scale=1
                )
            with gr.Accordion("Intro, outro and timing", open=False):
                demo_intro = gr.Textbox(
                    label="Intro (spoken first; leave empty for none)",
                    value=DEFAULT_INTRO,
                    lines=2,
                )
                demo_outro = gr.Textbox(
                    label="Outro (spoken last; leave empty for none)",
                    value=DEFAULT_OUTRO,
                    lines=2,
                )
                demo_narration = gr.Checkbox(
                    value=True, label="Add short narration between the parts"
                )
                demo_max = gr.Slider(
                    10,
                    90,
                    value=30,
                    step=5,
                    label="Longest part of the thought to play (seconds)",
                    info="Long recordings fade out gently at this point.",
                )
            demo_button = gr.Button("Create demo audio", variant="primary")
            demo_status = gr.Markdown()
            demo_answer = gr.Textbox(
                label="The answer Gemini gave (from your real notes)",
                lines=3,
                interactive=False,
            )
            demo_preview = gr.Audio(
                label="Listen to the demo", type="filepath", interactive=False
            )
            with gr.Accordion(
                "Script of the demo (for posters and captions)", open=False
            ):
                demo_script = gr.Markdown()
            demo_files = gr.File(
                label="Download the demo (.wav) and its script (.txt)",
                file_count="multiple",
                interactive=False,
            )

            gr.Markdown(
                "### 2. Exhibition player\n"
                "Plays saved demos - no microphone. For a **screen-free** set-up, run "
                "`python play_demo.py` in Terminal instead: it plays the newest demo through "
                "your headphones each time **Return** is pressed."
            )
            player_pick = gr.Dropdown(label="Saved demos", choices=[], value=None)
            player = gr.Audio(
                label="Exhibition player", type="filepath", interactive=False
            )

    # --- what each button does ---
    save_button.click(
        fn=save_and_transcribe,
        inputs=[audio_input, show],
        outputs=[status, transcript, items, thoughts, insights, audio_input],
    )
    delete_audio.change(fn=change_privacy, inputs=delete_audio, outputs=privacy_status)
    delete_all_button.click(
        fn=delete_existing_audio,
        inputs=[show, understood_audio],
        outputs=[privacy_status, understood_audio, thoughts],
    )
    show.change(fn=items_table, inputs=show, outputs=items)
    sort_button.click(
        fn=sort_earlier_thoughts, inputs=show, outputs=[sort_status, items]
    )
    connect_button.click(fn=connect_thoughts, outputs=insights)
    ask_button.click(
        fn=ask_question,
        inputs=[question, read_aloud, detail],
        outputs=[answer, notes_used, spoken],
    )
    question.submit(
        fn=ask_question,
        inputs=[question, read_aloud, detail],  # Return key
        outputs=[answer, notes_used, spoken],
    )
    # Ask by voice: answer automatically as soon as the person presses Stop.
    voice_question.stop_recording(
        fn=ask_by_voice,
        inputs=[voice_question, read_aloud, detail],
        outputs=[question, answer, notes_used, spoken],
    )

    allow_button.click(
        fn=allow_recording,
        inputs=agree,
        outputs=[consent_box, record_box, consent_status],
    )
    withdraw_button.click(
        fn=withdraw_recording, outputs=[consent_box, record_box, agree, consent_status]
    )

    refreshed = [
        items,
        thoughts,
        insights,
        item_pick,
        thought_pick,
        undo_info,
        bin_info,
        edit_text,
        edit_type,
        edit_when,
    ]
    item_pick.change(
        fn=pick_item, inputs=item_pick, outputs=[edit_text, edit_type, edit_when]
    )
    save_edit_button.click(
        fn=save_edit,
        inputs=[show, item_pick, edit_text, edit_type, edit_when],
        outputs=[edit_status, *refreshed],
    )
    delete_item_button.click(
        fn=delete_item, inputs=[show, item_pick], outputs=[edit_status, *refreshed]
    )
    delete_thought_button.click(
        fn=delete_recording,
        inputs=[show, thought_pick],
        outputs=[edit_status, *refreshed],
    )
    undo_button.click(fn=undo, inputs=show, outputs=[edit_status, *refreshed])
    empty_bin_button.click(
        fn=empty_bin,
        inputs=[show, understood],
        outputs=[edit_status, *refreshed, understood],
    )
    edit_tab.select(
        fn=refresh_all, inputs=show, outputs=refreshed
    )  # fresh lists on opening the tab

    reminder_lists = [reminder_pick, schedule_list, cancel_pick]
    reminders_tab.select(fn=refresh_reminders, outputs=reminder_lists)
    schedule_button.click(
        fn=schedule_clicked,
        inputs=[reminder_pick, due_picker, speak_reminder],
        outputs=[reminder_status, *reminder_lists],
    )
    cancel_button.click(
        fn=cancel_clicked,
        inputs=cancel_pick,
        outputs=[reminder_status, *reminder_lists],
    )
    reminder_timer.tick(fn=schedule_table, outputs=schedule_list)

    exhibition_tab.select(fn=refresh_exhibition, outputs=[demo_thought, player_pick])
    demo_button.click(
        fn=make_demo,
        inputs=[
            demo_thought,
            demo_question,
            demo_detail,
            demo_intro,
            demo_outro,
            demo_narration,
            demo_max,
        ],
        outputs=[
            demo_status,
            demo_answer,
            demo_script,
            demo_preview,
            demo_files,
            player_pick,
        ],
    )
    player_pick.change(fn=lambda path: path, inputs=player_pick, outputs=player)

    # Fill everything from the data/ folder whenever the page is opened or reloaded.
    demo.load(
        fn=lambda: (items_table("All"), thoughts_table(), current_insights()),
        outputs=[items, thoughts, insights],
    )
    demo.load(fn=consent_screens, outputs=[consent_box, record_box])
    demo.load(
        fn=delete_audio_enabled, outputs=delete_audio
    )  # show the saved privacy setting


if __name__ == "__main__":
    # Background checker for scheduled reminders. It delivers any that were missed
    # while the app was closed, then checks every 15 seconds.
    start_scheduler()
    # 127.0.0.1 = only reachable from your own computer (safer for private notes).
    # allowed_paths lets the page play and download the demos in exhibition/.
    demo.launch(server_name="127.0.0.1", allowed_paths=[str(EXHIBITION_DIR)])
