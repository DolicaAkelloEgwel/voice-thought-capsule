"""
setup_key.py - safely store your Gemini API key in the private .env file.

Run with:  python setup_key.py
Your typing is hidden, and the key is never printed or shown in the browser.
"""

import os
from getpass import getpass

from config import ENV_FILE


def main():
    print("Paste your Gemini API key and press Return.")
    print(
        "(Nothing will appear while you paste - that is normal, it keeps the key hidden.)"
    )
    key = getpass("API key: ").strip()

    if len(key) < 20 or " " in key:
        print(
            "\n❌ That doesn't look like a complete API key. Copy it again and re-run:  python setup_key.py"
        )
        return

    # Keep any other settings already in .env (e.g. GEMINI_MODEL), replace only the key.
    other_lines = []
    if ENV_FILE.exists():
        other_lines = [
            line
            for line in ENV_FILE.read_text().splitlines()
            if line.strip() and not line.startswith("GEMINI_API_KEY")
        ]

    ENV_FILE.write_text("\n".join([f"GEMINI_API_KEY={key}", *other_lines]) + "\n")
    os.chmod(ENV_FILE, 0o600)  # only your user account can read the file

    print(f"\n✅ Key saved in {ENV_FILE.name} (ends with ...{key[-4:]}).")
    print("Next, test it with:  python check_setup.py")


if __name__ == "__main__":
    main()
