"""Draws the status page's home-screen icons (H13; run once, the PNGs are kept in this folder).
Same dark tile as the call page's icon, so they sit together, but bars instead of rings.
H56.7: the server's status page (HQ_LABEL set) gets its own set, server-*.png: violet bars and a small server
mark in the corner, so the two status pages are told apart on the home screen (Claude's choice)."""
from pathlib import Path
from PIL import Image, ImageDraw

here = Path(__file__).parent
TEAL, VIOLET, AMBER = (45, 212, 191), (167, 139, 250), (217, 165, 32)


def draw(size, colours, server, name):
    s = size * 4
    img = Image.new("RGB", (s, s), (18, 22, 30))
    d = ImageDraw.Draw(img)
    # three status bars, the last one shorter: a status page at a glance
    for i, (w, col) in enumerate(zip([0.56, 0.44, 0.28], colours)):
        y = s * (0.30 + i * 0.16)
        x0 = s * 0.22
        d.rounded_rectangle([x0, y, x0 + w * s, y + s * 0.09], radius=s * 0.045, fill=col)
    if server:  # two stacked rack units, each with its light on
        for j in range(2):
            y = s * (0.12 + j * 0.075)
            d.rounded_rectangle([s * 0.64, y, s * 0.86, y + s * 0.06], radius=s * 0.012, fill=(60, 66, 84))
            d.ellipse([s * 0.665, y + s * 0.018, s * 0.689, y + s * 0.042], fill=(74, 222, 128))
    img.resize((size, size), Image.LANCZOS).save(here / name)


for size, name, server_name in [(180, "apple-touch-icon.png", "server-180.png"),
                                (192, "icon-192.png", "server-192.png"), (512, "icon-512.png", "server-512.png")]:
    draw(size, [TEAL, TEAL, AMBER], False, name)
    draw(size, [VIOLET, VIOLET, AMBER], True, server_name)
