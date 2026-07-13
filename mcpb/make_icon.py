"""Generate mcpb/icon.png — a simple flat scanner/document icon (512x512)."""

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
S = SIZE / 256  # scale factor so coordinates are authored at 256 and scaled up

BG = (37, 99, 235)        # blue rounded square
PAGE = (245, 247, 250)
LINE = (150, 160, 175)
SCANBAR = (16, 185, 129)  # green scan line


def sc(*vals):
    return [v * S for v in vals]


img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# rounded background
d.rounded_rectangle(sc(8, 8, 248, 248), radius=48 * S, fill=BG)

# document page
px0, py0, px1, py1 = 74, 52, 182, 204
d.rounded_rectangle(sc(px0, py0, px1, py1), radius=12 * S, fill=PAGE)

# text lines
y = py0 + 26
for i in range(5):
    w = (px1 - px0 - 28) if i % 3 else (px1 - px0 - 60)
    d.rounded_rectangle(sc(px0 + 14, y, px0 + 14 + w, y + 8), radius=4 * S, fill=LINE)
    y += 24

# green scan bar across the page with a soft glow
by = 150
d.rectangle(sc(px0 - 10, by - 3, px1 + 10, by + 3), fill=SCANBAR)
d.rectangle(sc(px0 - 10, by - 7, px1 + 10, by - 5), fill=(16, 185, 129, 120))
d.rectangle(sc(px0 - 10, by + 5, px1 + 10, by + 7), fill=(16, 185, 129, 120))

out = Path(__file__).resolve().parent / "icon.png"
img.save(out)
print("wrote", out, f"({SIZE}x{SIZE})")
