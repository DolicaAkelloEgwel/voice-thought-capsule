"""
check_setup.py - check that your Gemini key and model work before using the app.

Run with:  python check_setup.py
"""

from google.genai import errors

import config
from transcriber import friendly_error, make_client


def main():
    # 1. Is there a key?
    try:
        key = config.get_api_key()
    except config.MissingKeyError as error:
        print(f"❌ {error}")
        return
    print(f"✅ Found an API key in .env (ends with ...{key[-4:]})")

    client = make_client()
    model = config.get_model()

    # 2. Does the chosen model answer?
    try:
        reply = client.models.generate_content(
            model=model, contents="Reply with just the word OK."
        )
        print(f"✅ Model '{model}' works. It replied: {(reply.text or '').strip()}")
        print("\nAll good! Start the app with:  python app.py")
        return
    except errors.APIError as error:
        print(f"❌ {friendly_error(error)}")
    except Exception as error:
        print(
            f"❌ Could not reach Gemini. Check your internet connection. ({type(error).__name__}: {error})"
        )
        return

    # 3. If the model failed, list the 'flash' models this key can use.
    try:
        names = [
            m.name.removeprefix("models/")
            for m in client.models.list()
            if "flash" in (m.name or "")
            and "generateContent" in (m.supported_actions or [])
        ]
    except errors.APIError:
        return  # the key itself is the problem - the message above explains it
    if names:
        print(
            "\nModels your key can use (pick a plain 'flash' one, without 'preview' or 'tts'):"
        )
        for name in sorted(names):
            print(f"   {name}")
        print("\nTo choose one, open .env in TextEdit and add a line like:")
        print(f"   GEMINI_MODEL={sorted(names)[-1]}")
        print("Then run  python check_setup.py  again.")


if __name__ == "__main__":
    main()
