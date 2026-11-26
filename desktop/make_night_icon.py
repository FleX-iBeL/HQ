"""H84: the server's icon, HQ's house (H48, icon.svg) at night, with the stars and the moon.
Made from icon.svg, so the house stays the same drawing: the day's colours swapped for night ones, the lights on
in the glass (Claude's choice), the sun a crescent moon, stars in the sky. Writes icon-night.svg here, and the
server's phone icons (full squares, like hq-*.png) in status/icons/hq-night-*.png, drawn by headless Chrome.
Run once after changing icon.svg; the PNGs are kept in the repo. Needs Chrome or Chromium."""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

here = Path(__file__).parent
icons = here.parent / "status" / "icons"

NIGHT = {
    "#a9d4f4": "#0f1634", "#8fc6ef": "#1a2852",                     # sky, darker at the top
    "#8fb9a6": "#2c4560", "#6fa58a": "#24443e",                     # hills
    "#2f8fd0": "#123c66", "#2a7fbd": "#0e3054", "#ffffff": "#b9c8e0",  # sea and the wave
    "#dba66b": "#86613f", "#cf965c": "#755434", "#b37a46": "#5a3f26",  # the cliff
    "#5fae45": "#36692d", "#4e9a3a": "#2b5826",                     # grass and bushes
    "#7a5a3a": "#4a3724", "#2f8a3e": "#1c5228", "#3fa34d": "#286634",  # the palms
    "#f6f6f2": "#d5dbe6", "#dfe2df": "#b3bccb",                     # the white house in moonlight
    "#8fd3ec": "#ffd36e", "#3f7f9e": "#f2b54e", "#4f7280": "#3a4757",  # the glass, lights on
    "#40c4e0": "#3ee0ff",                                           # the pool, lit
}

MOON = ('<circle cx="830" cy="190" r="56" fill="#f7f1cf"/>'
        '<circle cx="854" cy="170" r="50" fill="#0f1634"/>')


def star(x, y, r):  # a four-pointed sparkle
    k = r * 0.28
    return (f'<path d="M{x} {y - r} L{x + k} {y - k} L{x + r} {y} L{x + k} {y + k} L{x} {y + r} '
            f'L{x - k} {y + k} L{x - r} {y} L{x - k} {y - k} Z" fill="#fff6d8"/>')


STARS = "".join(star(x, y, r) for x, y, r in [
    (130, 120, 18), (250, 165, 11), (360, 100, 15), (470, 175, 10), (560, 112, 17), (680, 160, 11),
    (735, 95, 13), (930, 290, 10), (160, 260, 10), (420, 255, 12), (900, 120, 9), (590, 230, 9),
]) + "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="#fff6d8"/>' for x, y in [
    (200, 95), (310, 215), (520, 260), (640, 95), (780, 280), (95, 190), (880, 230), (400, 160),
])


def night_svg():
    svg = (here / "icon.svg").read_text()
    svg = re.sub("|".join(re.escape(k) for k in NIGHT), lambda m: NIGHT[m.group(0)], svg)
    sun = '<circle cx="830" cy="190" r="56" fill="#ffe08a"/>'
    assert sun in svg, "the sun moved in icon.svg"
    svg = svg.replace(sun, MOON + STARS)
    svg = svg.replace("<!-- H48: HQ's icon,", "<!-- H84: the server's icon, made by make_night_icon.py from H48: HQ's icon,")
    return svg


def full_square(svg):  # the phone icons are full squares (like hq-*.png): no tile, no margin
    inner = svg.split('<g clip-path="url(#tile)">', 1)[1].rsplit("</g></g>", 1)[0]
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="64 64 896 896" width="1024" height="1024">'
            + inner + "</svg>")


def render(svg, size, out, chrome):
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "icon.html"
        page.write_text('<html><body style="margin:0;background:#000">'
                        f'<div style="width:{size}px;height:{size}px">'
                        + svg.replace('width="1024" height="1024"', f'width="{size}" height="{size}"')
                        + "</div></body></html>")
        subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        f"--window-size={size},{size}", f"--screenshot={out}", page.as_uri()],
                       check=True, capture_output=True, timeout=60)


if __name__ == "__main__":
    chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
    if not chrome:
        sys.exit("Chrome or Chromium is needed to draw the PNGs")
    svg = night_svg()
    (here / "icon-night.svg").write_text(svg)
    for size in (180, 192, 512):
        render(full_square(svg), size, icons / f"hq-night-{size}.png", chrome)
    print("icon-night.svg and status/icons/hq-night-{180,192,512}.png written")
