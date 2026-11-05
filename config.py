"""
config.py - reads your private settings from the .env file.

The .env file lives only on your computer. Only this Python server code
reads it - the key is never sent to the web page in your browser.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
ENV_FILE = PROJECT_DIR / ".env"

# Load GEMINI_API_KEY (and optionally GEMINI_MODEL) from .env into the environment.
load_dotenv(ENV_FILE)

# Used when .env has no GEMINI_MODEL line.
# Google renames models from time to time - if check_setup.py says this model
# is not found, add a line like  GEMINI_MODEL=<name>  to your .env file.
DEFAULT_MODEL = "gemini-3.5-flash"


class MissingKeyError(Exception):
    """Raised when there is no usable Gemini API key in .env."""


def get_api_key():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "paste-your-key-here":
        raise MissingKeyError(
            "No Gemini API key found. In Terminal, run:  python setup_key.py"
        )
    return key


def get_model():
    return os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
