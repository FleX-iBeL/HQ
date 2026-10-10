"""Draws the status page's home-screen icons (H13; run once, the PNGs are kept in this folder).
Same dark tile as the call page's icon, so they sit together, but bars instead of rings."""
from pathlib import Path
from PIL import Image, ImageDraw

here = Path(__file__).parent
for size, name in [(180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")]:
    s = size * 4
    img = Image.new("RGB", (s, s), (18, 22, 30))
    d = ImageDraw.Draw(img)
    # three status bars, the last one shorter: a status page at a glance
    for i, (w, col) in enumerate([(0.56, (45, 212, 191)), (0.44, (45, 212, 191)), (0.28, (217, 165, 32))]):
        y = s * (0.30 + i * 0.16)
        x0 = s * 0.22
        d.rounded_rectangle([x0, y, x0 + w * s, y + s * 0.09], radius=s * 0.045, fill=col)
    img.resize((size, size), Image.LANCZOS).save(here / name)
