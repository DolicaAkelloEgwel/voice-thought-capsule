"""
make_hero.py - draws the hero artwork (assets/hero.jpg): soft streaks of light in orange,
peach, lavender and violet on black. Decoration only. You don't need to run this; the
image is already in this folder. To redraw it: python assets/make_hero.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

W, H = 1920, 1080
rng = np.random.default_rng(7)
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
angle = np.deg2rad(13)                                   # streaks fall gently to the right
u = (x * np.cos(angle) + y * np.sin(angle)) / W          # along the streaks
v = (-x * np.sin(angle) + y * np.cos(angle)) / H         # across the streaks

# fine "motion blur" lines: noise that only changes across the streaks
lines = rng.random(4000).astype(np.float32)
lines = np.convolve(lines, np.ones(9) / 9, mode="same")
idx = np.clip(((v + 1) * 1500).astype(int), 0, len(lines) - 1)
texture = 0.78 + 0.44 * (lines[idx] - lines.min()) / (np.ptp(lines) + 1e-6)

img = np.zeros((H, W, 3), np.float32)
# (centre across, width, colour, strength, where along it is brightest, curve)
ribbons = [
    (0.06, 0.060, (255, 122, 47), 1.0, 0.70, 0.04),    # orange
    (0.12, 0.035, (255, 200, 165), 0.95, 0.55, 0.04),  # peach highlight
    (0.20, 0.090, (139, 92, 246), 0.85, 0.35, -0.03),  # violet
    (0.15, 0.016, (255, 255, 255), 0.95, 0.50, 0.04),  # white core
    (-0.04, 0.022, (255, 150, 70), 0.8, 0.95, 0.02),   # thin orange streak at the top
    (0.33, 0.120, (95, 70, 190), 0.55, 0.20, -0.02),   # deep violet haze
    (0.25, 0.040, (205, 185, 255), 0.7, 0.62, 0.03),   # lavender
    (0.10, 0.200, (255, 120, 60), 0.30, 0.85, 0.0),    # wide warm glow
]
for centre, width, colour, strength, peak, curve in ribbons:
    c = centre + curve * np.sin(u * 3.2)
    across = np.exp(-((v - c) / width) ** 2)
    along = np.exp(-((u - peak) / 0.42) ** 2)
    glow = (across * along * strength * texture)[..., None]
    img = 1 - (1 - img) * (1 - glow * np.array(colour, np.float32) / 255)   # "screen" blend

# keep the bottom dark so the title and text are easy to read
fade = np.clip((y / H - 0.52) / 0.40, 0, 1) ** 1.3
img *= (1 - 0.94 * fade)[..., None]
img = np.clip(img ** 0.95, 0, 1)

out = Image.fromarray((img * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
out.save(Path(__file__).parent / "hero.jpg", quality=86, optimize=True, progressive=True)
print("saved hero.jpg")
