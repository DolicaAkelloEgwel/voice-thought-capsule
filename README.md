# Voice Thought Capsule (UX MA prototype)

You speak a thought, and the app saves it, sorts it and links it to related thoughts. Later you can ask questions about your thoughts and hear the answers.
It is built in small steps, and each step adds one feature you can test before moving on.

| Step | Feature | Status |
|------|---------|--------|
| 1 | Record voice with the microphone | ✅ done |
| 2 | Speech to text (Gemini) | ✅ done |
| 3 | Save thoughts (timestamp + unique ID) to a local JSON file | ✅ done |
| 4 | Split each thought into items, labelled idea / task / reminder | ✅ done |
| 5 | Connect related thoughts + summaries | ✅ done |
| 6 | Ask questions (retrieve relevant notes first) | ✅ done |
| 7 | Speak answers aloud (text-to-speech, built-in Mac voice) | ✅ done |
| 8 | Edit, undo, delete, clear recording permission | ✅ done |
| + | Extra: ask questions by voice | ✅ done |
| + | Extra: privacy option to delete audio after transcribing | ✅ done |
| + | Extra: real reminders with Mac notifications | ✅ done |
| 6* | Faculty Step 6: exhibition version (audio demo + screen-free player) | ✅ done |

> **About reminders:** a 🔔 *reminder* is only a label until you schedule it in the **⏰ Reminders**
> tab. Scheduled reminders show a real Mac notification, **but only while the app is running**.
> If the app was closed at the due time, the reminder is marked *missed* and delivered as soon as the
> app starts again. The app only says "scheduled" when a real schedule has been saved.

> **Privacy:** recordings are stored on your Mac. To turn speech into text, the audio is sent to
> Google's Gemini API. On Gemini's free tier, Google may use what you send to improve its products,
> so use test thoughts rather than very personal ones.

---

## First-time setup (macOS)

Run each command in **Terminal**, one at a time. Press **Return** after each one.

1. Go to the project folder:
   ```bash
   cd ~/Downloads/voice-thought-capsule
   ```
2. Create the project's package space (one time only):
   ```bash
   python3 -m venv .venv
   ```
3. Switch it on. You'll see `(.venv)` at the start of the line:
   ```bash
   source .venv/bin/activate
   ```
4. Install the packages:
   ```bash
   python -m pip install -r requirements.txt
   ```

## Your Gemini API key (Step 2 onwards)

1. Create a key at https://aistudio.google.com/apikey (**Create API key**, then **Create project**).
   Never paste the key into a chat, email, or screenshot.
2. Save it into the private `.env` file:
   ```bash
   python setup_key.py
   ```
   Paste the key and press **Return**. Nothing appears while you paste. That's on purpose, to keep the key hidden.
3. Check that it works:
   ```bash
   python check_setup.py
   ```
   You want to see `✅ Model '...' works`. If the model is not found, the script lists the models
   your key can use and tells you how to choose one.

The key is stored in `.env`, which only the Python server reads. It is never sent to the browser,
and `.gitignore` keeps it out of git.

## Test

```bash
python -m pytest
```
You should see **87 passed**. The tests use a pretend Gemini client, so they need no internet and use none of your quota.

## Run

```bash
python app.py
```
Open **http://127.0.0.1:7860** in Chrome. To stop the app, click Terminal and press **Control + C**.

### Try it by hand
The page has seven tabs: 🎙️ Record, 📋 Sorted items, 🔗 Connections, ❓ Ask, ⏰ Reminders, ✏️ Edit and 🎧 Exhibition.

0. **Permission first.** The Record tab explains what is recorded, where it is stored and what is
   sent to Gemini. Tick the box and click **Allow recording**. The microphone only appears after
   that. You can **Withdraw recording permission** at any time (your saved thoughts are kept).
   Chrome will also ask for microphone access the first time. Both are needed.

1. Click **Record**, and allow the microphone if Chrome asks.
2. Say something, e.g. *"Idea: use softer colours on the capsule screen."* Then click **Stop**.
3. Click **Save and transcribe**.
4. **Status** shows the saved file and the thought's ID, and **What you said** shows the text.
5. Under **Your sorted items**, the thought appears split into ✅ tasks, 🔔 reminders and 💡 ideas.
   Use **Show** to filter. Reload the page and everything is still there.
   Thoughts saved before Step 4 can be sorted with **Sort earlier thoughts**.
   The original wording is under **Full transcripts**.
6. Under **Connections and summary**, click **Connect and summarise**. Related items from all
   your recordings are grouped into themes, each with a short summary, plus an overview.
   If you add thoughts later, a ⚠️ note tells you to run it again.
7. In the **Ask** tab, type a question (or click an example) and press **Ask**.
   The app first finds the relevant notes, then answers only from them, and lists the
   notes it used so you can check. If nothing relevant is found, it says so instead of guessing.
   **Answer length:** choose **Brief** (1-2 sentences) or **Detailed** (covers every relevant note).
   Questions about dates such as *"What were my ideas from yesterday?"* work too, because the
   app knows today's date and when each note was recorded.
   **Or ask by voice:** press Record on the microphone next to the question box, ask, then
   press Stop. The question is transcribed and answered straight away. The spoken question
   is sent to Gemini to be transcribed but is not saved, and it needs recording permission.
   With **🔊 Read answers aloud** ticked, the answer is spoken automatically. Press ▶ to hear it again.
   To hear it in your **headphones**, connect them and choose them as the Mac's sound output
   (Control Centre → Sound). The voice is the Mac's built-in one, so it works offline and
   the answer is not sent anywhere to be spoken. To change the voice, add `TTS_VOICE=Daniel`
   (or another name from `say -v '?'`) to `.env` and restart the app.
8. **🔒 Privacy settings** (Record tab): tick **Delete audio after transcribing** to delete each
   recording as soon as it is turned into text, keeping only the text. If transcription fails,
   the audio is kept so nothing is lost. The setting is remembered (`data/settings.json`).
   **Delete all saved audio now** removes existing recordings but keeps all text
   (tick the confirmation box first, because it can't be undone).
9. In the **⏰ Reminders** tab, choose an item (🔔 reminders are listed first), type a date and time
   (`YYYY-MM-DD HH:MM:SS`) or use the calendar button, and click **Schedule reminder**. At that time
   you get a Mac notification (and hear it spoken, if ticked). The list shows ⏰ Scheduled,
   ✅ Delivered, ⚠️ Missed or ✖️ Cancelled. If no notification appears, allow notifications for
   **Script Editor** in System Settings → Notifications, and check Focus / Do Not Disturb.
10. In the **🎧 Exhibition** tab (faculty Step 6), pick a thought, type a question and click
    **Create demo audio**. The app gets the real answer from your notes and joins intro → your
    thought → question → spoken answer → outro into one `.wav` file, plus a `.txt` script, in the
    `exhibition/` folder. Only use thoughts you're happy for visitors to hear (it contains your voice).
    **Screen-free exhibition player:** `python play_demo.py` plays the newest demo through the
    headphones each time Return is pressed (`--loop` plays it on repeat). A physical button that
    acts like the Return key could trigger it later. No microphone and no visitor data.
11. In the **✏️ Edit** tab:
   - choose an item to **edit** its text, type or time, or to **delete** it
   - **delete a whole recording** (transcript, items and audio). The audio goes to the **bin**
   - **↩️ Undo last change** reverses the last edit or delete (up to 20 steps), including
     bringing a deleted recording's audio back from the bin
   - **Empty bin permanently** really deletes the audio. You must tick a box first, because
     this can't be undone
12. Open `data/thoughts.json` in TextEdit to see exactly what is stored.
13. Try a recording of silence. It should say *No speech was detected*.

### Starting again another day
```bash
cd ~/Downloads/voice-thought-capsule
```
```bash
source .venv/bin/activate
```
```bash
python app.py
```

## Troubleshooting
| Message | What to do |
|---|---|
| `No Gemini API key found` | Run `python setup_key.py` |
| `Gemini refused access` / `rejected the API key` | Make a new key in AI Studio, then run `python setup_key.py` |
| `model ... was not found` | Run `python check_setup.py` and follow its suggestion |
| `free usage limit was reached` | Wait a minute and try again |
| Microphone not detected | Apple menu → System Settings → Privacy & Security → Microphone → turn on Chrome |
| `ModuleNotFoundError` | Run `source .venv/bin/activate`, then `python -m pip install -r requirements.txt` |

## Project files

```
app.py            the Gradio interface (what you see in the browser)
recorder.py       Step 1: saves a copy of each recording
transcriber.py    Step 2: speech to text with Gemini
storage.py        Step 3: saves thoughts to data/thoughts.json
classifier.py     Step 4: splits thoughts into labelled items (Gemini)
linker.py         Step 5: connects related items and writes summaries (Gemini)
qa.py             Step 6: finds relevant notes, then answers questions from them (Gemini)
speaker.py        Step 7: reads answers aloud with the built-in Mac voice (offline)
consent.py        Step 8: recording permission (data/consent.json)
editing.py        Step 8: edit, delete, undo and the bin (data/undo_history.json, data/bin/)
privacy.py        Extra: delete audio after transcribing (data/settings.json)
reminders.py      Extra: real reminders with Mac notifications (data/schedule.json)
exhibition.py     Step 6: builds exhibition audio demos (exhibition/)
play_demo.py      Step 6: screen-free player for the exhibition (press Return to play)
config.py         reads your key and model name from .env
setup_key.py      stores your key safely in .env
check_setup.py    tests your key and model
tests/            automatic tests
data/recordings/  your saved audio (private, not committed to git)
data/thoughts.json  your saved thoughts (private, not committed to git)
data/insights.json  the latest connections and summary
```
