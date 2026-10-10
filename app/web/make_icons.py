"""Draws the home-screen icons (run once; the PNGs are kept in this folder)."""
from pathlib import Path
from PIL import Image, ImageDraw

here = Path(__file__).parent
for size, name in [(180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")]:
    s = size * 4
    img = Image.new("RGB", (s, s), (18, 22, 30))
    d = ImageDraw.Draw(img)
    cx = cy = s / 2
    for r, col in [(0.34, (45, 212, 191)), (0.24, (18, 22, 30)), (0.15, (45, 212, 191))]:
        d.ellipse([cx - r * s, cy - r * s, cx + r * s, cy + r * s], fill=col)
    img.resize((size, size), Image.LANCZOS).save(here / name)
