"""Generate docs/demo.gif — an animated terminal demo of scanner-mcp.

Recreates the real workflow from actual command output: discover scanners,
scan a page, then Claude reads the document back (scan-line reveal + transcript).
Run:  python docs/make_demo.py  (needs Pillow; uses the real scan if present).
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 860, 560
TITLEBAR = 34
PAD = 22
LH = 25  # line height
FONT_DIR = r"C:\Windows\Fonts"

BG = (13, 17, 23)
BAR = (22, 27, 34)
BORDER = (48, 54, 61)
PROMPT = (63, 185, 80)
CMD = (230, 237, 243)
GRAY = (139, 148, 158)
CYAN = (86, 182, 194)
GREEN = (86, 211, 100)
YELLOW = (210, 168, 60)
WHITE = (230, 237, 243)

HERE = Path(__file__).resolve().parent
SCAN = Path(os.environ.get("DEMO_SCAN", r"C:\Users\aminh\Scans\scan-20260711-145133.png"))
OUT = HERE / "demo.gif"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "consolab.ttf" if bold else "consola.ttf"
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        return ImageFont.load_default()


F = font(17)
FB = font(17, bold=True)
FT = font(14, bold=True)

frames: list[Image.Image] = []
durations: list[int] = []


def base() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TITLEBAR], fill=BAR)
    d.line([0, TITLEBAR, W, TITLEBAR], fill=BORDER)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([PAD + i * 22, 11, PAD + i * 22 + 12, 23], fill=c)
    d.text((W // 2 - 46, 9), "scanner-mcp", font=FT, fill=GRAY)
    return img


def draw_lines(img: Image.Image, lines, cursor=False):
    d = ImageDraw.Draw(img)
    y = TITLEBAR + PAD
    for segs in lines:
        x = PAD
        for text, color in segs:
            d.text((x, y), text, font=F, fill=color)
            x += d.textlength(text, font=F)
        if cursor and segs is lines[-1]:
            d.rectangle([x + 2, y + 2, x + 11, y + LH - 4], fill=(88, 166, 255))
        y += LH
    return y


def push(lines, cursor=False, dur=90, panel=None):
    img = base()
    draw_lines(img, lines, cursor=cursor)
    if panel is not None:
        img.paste(panel, (0, 0), panel)
    frames.append(img)
    durations.append(dur)


def type_command(lines, prompt_segs, text, hold=700):
    """Animate typing `text` after the prompt on a new line."""
    for i in range(len(text) + 1):
        cur = lines + [prompt_segs + [(text[:i], CMD)]]
        push(cur, cursor=True, dur=45)
    # brief hold with cursor
    push(lines + [prompt_segs + [(text, CMD)]], cursor=True, dur=hold)
    return lines + [prompt_segs + [(text, CMD)]]


# ------------------------------------------------------------------ scene 1
lines: list = []
p = [("$ ", PROMPT)]
lines = type_command(lines, p, "scanner list_scanners")

out1 = [
    [("  backends: eSCL (network), WIA (Windows)", GRAY)],
    [("  ● Canon TS3400 series", WHITE)],
    [("      id ", GRAY), ("wia:SWD\\Escl\\…bc9f", CYAN), ("   [usb]", GRAY)],
]
acc = lines
for ln in out1:
    acc = acc + [ln]
    push(acc, dur=260)
push(acc, dur=900)

# ------------------------------------------------------------------ scene 2
acc = acc + [[("", CMD)]]
acc = type_command(acc, p, "scanner scan_document --dpi 300", hold=500)
for ln, dur in [
    ([("  scanning…", GRAY)], 800),
    ([("  ● Scan OK — 1 page · image/png · 1.5 MB", GREEN)], 300),
    ([("    saved: ~/Scans/scan-2026…-145133.png", GRAY)], 300),
]:
    acc = acc + [ln]
    push(acc, dur=dur)
push(acc, dur=700)

# ------------------------------------------------------------------ scene 3: Claude reads it
# Prepare the scanned image (downscaled) for a scan-line reveal on the left.
doc_w = 250
if SCAN.exists():
    doc = Image.open(SCAN).convert("RGB")
else:  # fallback placeholder
    doc = Image.new("RGB", (500, 700), (245, 244, 236))
ratio = doc_w / doc.width
doc = doc.resize((doc_w, int(doc.height * ratio)))
doc_h = min(doc.height, H - TITLEBAR - 2 * PAD)
doc = doc.crop((0, 0, doc_w, doc_h))
doc_x, doc_y = PAD, TITLEBAR + PAD

bullets = [
    "Upstream → Packloop → Accumulator",
    "2026-06-06  20:03:02 UTC",
    "KPI · Offline processing",
    "Yolo26 + SAM + active",
    "Wedged GPU · 1TB   (userid 1000)",
    "C39 > SMB > logs",
]

tx = doc_x + doc_w + 34
title_y = doc_y
bullets_y = doc_y + 44


def draw_right_title(d):
    d.text((tx, title_y), "Claude reads the page:", font=FB, fill=YELLOW)


# scan-line reveal of the document
reveal_steps = 14
for s in range(1, reveal_steps + 1):
    img = base()
    d = ImageDraw.Draw(img)
    draw_right_title(d)
    h = int(doc_h * s / reveal_steps)
    img.paste(doc.crop((0, 0, doc_w, h)), (doc_x, doc_y))
    d.line([doc_x, doc_y + h, doc_x + doc_w, doc_y + h], fill=(88, 166, 255), width=2)
    frames.append(img)
    durations.append(70)


# transcript bullets type in on the right, one per step
def render_scene3(nb):
    img = base()
    img.paste(doc, (doc_x, doc_y))
    d = ImageDraw.Draw(img)
    draw_right_title(d)
    y = bullets_y
    for i in range(nb):
        d.text((tx, y), "●", font=FB, fill=GREEN)
        d.text((tx + 22, y), bullets[i], font=F, fill=WHITE)
        y += LH + 8
    return img

for nb in range(len(bullets) + 1):
    frames.append(render_scene3(nb))
    durations.append(90 if nb == 0 else 360)
# long hold on the final frame
frames.append(render_scene3(len(bullets)))
durations.append(2600)

# ------------------------------------------------------------------ save
pal_frames = [f.quantize(colors=128, method=Image.FASTOCTREE) for f in frames]
pal_frames[0].save(
    OUT,
    save_all=True,
    append_images=pal_frames[1:],
    duration=durations,
    loop=0,
    optimize=True,
    disposal=2,
)
size_kb = OUT.stat().st_size / 1024
print(f"wrote {OUT}  ({len(frames)} frames, {size_kb:.0f} KB)")
