"""Generate docs/demo.gif — a Claude-chat demo of scanner-mcp.

Shows the real way the server is used: you ask Claude, it calls the
`scan_document` tool, then reads the page back. Built from the actual scan.
Run:  python docs/make_demo.py   (needs Pillow; uses the real scan if present).
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 860, 560
TITLEBAR = 34
PAD = 22
LH = 25
FONT_DIR = r"C:\Windows\Fonts"

BG = (13, 17, 23)
BAR = (22, 27, 34)
BORDER = (48, 54, 61)
GRAY = (139, 148, 158)
CYAN = (86, 182, 194)
GREEN = (86, 211, 100)
YELLOW = (210, 168, 60)
WHITE = (230, 237, 243)
USER_BUBBLE = (35, 66, 120)
PILL_BG = (26, 31, 39)

HERE = Path(__file__).resolve().parent
SCAN = Path(os.environ.get("DEMO_SCAN", r"C:\Users\aminh\Scans\scan-20260711-145133.png"))
OUT = HERE / "demo.gif"


def font(size, bold=False, mono=True):
    if mono:
        name = "consolab.ttf" if bold else "consola.ttf"
    else:
        name = "segoeuib.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        return ImageFont.load_default()


F = font(18, mono=False)
FB = font(18, bold=True, mono=False)
FM = font(16)  # mono for tool pill
FT = font(14, bold=True, mono=False)

frames: list[Image.Image] = []
durations: list[int] = []

# --- prepare the scanned page (downscaled) --------------------------------
doc_w = 214
if SCAN.exists():
    doc = Image.open(SCAN).convert("RGB")
else:
    doc = Image.new("RGB", (500, 700), (245, 244, 236))
doc = doc.resize((doc_w, int(doc.height * doc_w / doc.width)))

USER_TEXT = "Scan my document and read it"
bullets = [
    "Upstream → Packloop → Accumulator",
    "2026-06-06  20:03:02 UTC",
    "KPI · Offline processing",
    "Yolo26 + SAM + active",
    "Wedged GPU · 1TB  (userid 1000)",
    "C39 > SMB > logs",
]

# --- layout ---------------------------------------------------------------
ub_y0 = TITLEBAR + PAD
ub_h = 42
asst_y = ub_y0 + ub_h + 26
pill_y = asst_y + 22
msg_y = pill_y + 42
doc_x = PAD
doc_y = msg_y + 34
doc_h = min(doc.height, H - doc_y - PAD)
doc = doc.crop((0, 0, doc_w, doc_h))
tx = doc_x + doc_w + 34
bullets_y = doc_y + 2


def base():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TITLEBAR], fill=BAR)
    d.line([0, TITLEBAR, W, TITLEBAR], fill=BORDER)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([PAD + i * 22, 11, PAD + i * 22 + 12, 23], fill=c)
    d.text((W // 2 - 26, 9), "Claude", font=FT, fill=GRAY)
    return img, d


def user_bubble(d, visible):
    full_w = d.textlength(USER_TEXT, font=F)
    bw = full_w + 28
    x1 = W - PAD
    x0 = x1 - bw
    d.rounded_rectangle([x0, ub_y0, x1, ub_y0 + ub_h], radius=12, fill=USER_BUBBLE)
    d.text((x0 + 14, ub_y0 + 9), visible, font=F, fill=WHITE)


def tool_pill(d, state):
    # state: None | "run" | "done"
    if state is None:
        return
    label = "scanner ▸ scan_document"
    tw = d.textlength(label, font=FM)
    x0, y0 = PAD, pill_y
    x1, y1 = x0 + tw + 58, y0 + 30
    d.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=PILL_BG, outline=BORDER)
    dot = YELLOW if state == "run" else GREEN
    d.ellipse([x0 + 12, y0 + 11, x0 + 20, y0 + 19], fill=dot)
    d.text((x0 + 30, y0 + 6), label, font=FM, fill=GRAY)
    tail = "  running…" if state == "run" else "  done"
    d.text((x1 - 6, y0 + 6), "", font=FM)
    d.text((x0 + 30 + tw + 6, y0 + 6), tail, font=FM, fill=dot)


def push(visible=USER_TEXT, pill=None, msg=False, reveal=0, nb=0, dur=90, blue_line=True):
    img, d = base()
    user_bubble(d, visible)
    tool_pill(d, pill)
    if msg:
        d.text((PAD, msg_y), "Scanned 1 page — here's what's on it:", font=F, fill=WHITE)
    if reveal > 0:
        h = int(doc_h * min(reveal, 1.0))
        img.paste(doc.crop((0, 0, doc_w, h)), (doc_x, doc_y))
        if blue_line and reveal < 1.0:
            ImageDraw.Draw(img).line(
                [doc_x, doc_y + h, doc_x + doc_w, doc_y + h], fill=(88, 166, 255), width=2
            )
    if nb > 0:
        d2 = ImageDraw.Draw(img)
        y = bullets_y
        for i in range(nb):
            d2.text((tx, y), "●", font=FB, fill=GREEN)
            d2.text((tx + 22, y), bullets[i], font=F, fill=WHITE)
            y += LH + 8
    frames.append(img)
    durations.append(dur)


# 1) user types the request
for i in range(len(USER_TEXT) + 1):
    push(visible=USER_TEXT[:i], dur=45)
push(dur=650)

# 2) Claude invokes the tool
push(pill="run", dur=500)
push(pill="run", dur=900)
push(pill="done", dur=600)

# 3) message + scan-line reveal of the page
push(pill="done", msg=True, dur=450)
reveal_steps = 14
for s in range(1, reveal_steps + 1):
    push(pill="done", msg=True, reveal=s / reveal_steps, dur=70)

# 4) Claude's read-back bullets type in
for nb in range(len(bullets) + 1):
    push(pill="done", msg=True, reveal=1.0, nb=nb, dur=90 if nb == 0 else 360)
push(pill="done", msg=True, reveal=1.0, nb=len(bullets), dur=2600)

# --- save -----------------------------------------------------------------
pal = [f.quantize(colors=128, method=Image.FASTOCTREE) for f in frames]
pal[0].save(
    OUT, save_all=True, append_images=pal[1:], duration=durations,
    loop=0, optimize=True, disposal=2,
)
print(f"wrote {OUT}  ({len(frames)} frames, {OUT.stat().st_size/1024:.0f} KB)")
