"""H194: the Mac app's Dock icon, drawn once and kept in the repo (desktop/HQ.icns), so a friend's fresh install
has HQ's house in the Dock without having to draw it on their Mac (svg2png or Quick Look could fail there, and then
the app got the plain icon). Made from icon.svg with its tile and margin, the corners transparent, by headless
Chrome; the .icns (16 to 1024, with the @2x sizes) is written with Pillow. Run once after changing icon.svg.
Needs Chrome or Chromium."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

here = Path(__file__).parent


def render(svg, size, out, chrome):
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "icon.html"
        page.write_text('<html><body style="margin:0;background:transparent">'
                        f'<div style="width:{size}px;height:{size}px">'
                        + svg.replace('viewBox="0 0 1024 1024"', f'viewBox="0 0 1024 1024" width="{size}" height="{size}"', 1)
                        + "</div></body></html>")
        subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        "--default-background-color=00000000", f"--window-size={size},{size}",
                        f"--screenshot={out}", page.as_uri()], check=True, capture_output=True, timeout=60)


if __name__ == "__main__":
    chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
    if not chrome:
        sys.exit("Chrome or Chromium is needed to draw the icon")
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "icon-1024.png"
        render((here / "icon.svg").read_text(), 1024, png, chrome)
        img = Image.open(png).convert("RGBA")
        assert img.getpixel((0, 0))[3] == 0 and img.getpixel((512, 512))[3] == 255, "the corners aren't transparent"
        img.save(here / "HQ.icns")
    print("desktop/HQ.icns written")
