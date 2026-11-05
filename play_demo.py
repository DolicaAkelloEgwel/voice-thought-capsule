"""
play_demo.py - screen-free exhibition player.

Plays your newest exhibition demo through the Mac's sound output (e.g. headphones)
every time Return is pressed - no browser, no screen and no microphone needed.

A physical button that acts like the Return key (ask CTH) can trigger it later.

Run with:
    python play_demo.py            press Return to play, Control + C to stop
    python play_demo.py --loop     play again and again, with a 10-second pause
    python play_demo.py exhibition/demo_2026-11-01_14-00-00.wav    play a specific demo
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

from exhibition import demo_seconds, list_demos

PAUSE_BETWEEN_LOOPS = 10  # seconds


def choose_demo(args, demos):
    """The file named on the command line, or else the newest demo."""
    files = [a for a in args if not a.startswith("--")]
    if files:
        path = Path(files[0])
        return path if path.exists() else None
    return demos[0] if demos else None


def main(args):
    demo = choose_demo(args, list_demos())
    if not demo:
        print("❌ No demo found. Create one first in the app's 🎧 Exhibition tab.")
        return 1
    player = shutil.which("afplay")  # the Mac's built-in audio player
    if not player:
        print("❌ This player uses the Mac's built-in 'afplay'. Run it on your Mac.")
        return 1

    print(f"🎧 Demo: {demo.name} ({demo_seconds(demo):.0f} seconds)")
    loop = "--loop" in args
    print(
        "Playing on repeat." if loop else "Press Return to play.",
        "Press Control + C to stop.",
    )
    try:
        while True:
            if not loop:
                input()
            print("▶ Playing...")
            subprocess.run([player, str(demo)])
            if loop:
                time.sleep(PAUSE_BETWEEN_LOOPS)
            else:
                print("Press Return to play again.")
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
