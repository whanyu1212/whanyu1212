"""Frame README screenshots in terminal windows that match the profile header.

Every card comes out at the same size, so they sit side by side in the README
without uneven heights. Re-run after replacing a source screenshot:

    python3 scripts/frame_screenshots.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PICTURES = ROOT / "pictures"

# Palette shared with pictures/terminal-header.svg.
TITLE_BAR = "#121A28"
BORDER = "#2A3548"
TITLE_TEXT = "#8B9BB3"
DOTS = [("#FF3CAC", 1.0), ("#00E5FF", 0.55), ("#CBD5E1", 0.28)]

SCALE = 2  # Draw chrome at 2x, then downsample for smooth edges.
CONTENT_W, CONTENT_H = 800, 600
BAR_H = 32
RADIUS = 10

CARDS = [
    {
        "source": "gem-movement-trail.png",
        "crop": (175, 0, 1845, 1370),  # Map plus team legend; drops the empty margins.
        "title": "~/gem-dota — match-report.html",
        "output": "card-gem-dota.webp",
    },
    {
        "source": "wisp-terminal.jpg",
        "crop": (0, 0, 800, 600),  # Diff, tool output, and the slash-command menu.
        "title": "~/Wisp — wisp",
        "output": "card-wisp.webp",
    },
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc"):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)


def blend(hex_color: str, opacity: float, base: str = TITLE_BAR) -> tuple[int, int, int]:
    fg = Image.new("RGB", (1, 1), hex_color).getpixel((0, 0))
    bg = Image.new("RGB", (1, 1), base).getpixel((0, 0))
    return tuple(round(f * opacity + b * (1 - opacity)) for f, b in zip(fg, bg))


def fit_content(source: Path, crop: tuple[int, int, int, int]) -> Image.Image:
    """Letterbox the cropped screenshot, padding with its own background colour."""
    shot = Image.open(source).convert("RGB").crop(crop)
    shot.thumbnail((CONTENT_W, CONTENT_H), Image.LANCZOS)
    canvas = Image.new("RGB", (CONTENT_W, CONTENT_H), shot.getpixel((2, 2)))
    canvas.paste(shot, ((CONTENT_W - shot.width) // 2, (CONTENT_H - shot.height) // 2))
    return canvas


def draw_window(content: Image.Image, title: str) -> Image.Image:
    w, h = CONTENT_W * SCALE, (CONTENT_H + BAR_H) * SCALE
    bar = BAR_H * SCALE

    window = Image.new("RGB", (w, h), TITLE_BAR)
    window.paste(content.resize((w, h - bar), Image.LANCZOS), (0, bar))

    draw = ImageDraw.Draw(window)
    draw.line([(0, bar), (w, bar)], fill=BORDER, width=SCALE)
    for i, (color, opacity) in enumerate(DOTS):
        cx, cy, r = (20 + i * 15) * SCALE, bar // 2, 4 * SCALE
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=blend(color, opacity))
    font = load_font(12 * SCALE)
    draw.text((w // 2, bar // 2), title, fill=TITLE_TEXT, font=font, anchor="mm")

    # Rounded corners with a hairline border, as in the header SVG.
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], RADIUS * SCALE, fill=255)
    framed = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    framed.paste(window, (0, 0), mask)
    ImageDraw.Draw(framed).rounded_rectangle(
        [0, 0, w - 1, h - 1], RADIUS * SCALE, outline=BORDER, width=SCALE
    )
    return framed.resize((CONTENT_W, CONTENT_H + BAR_H), Image.LANCZOS)


def main() -> None:
    for card in CARDS:
        content = fit_content(PICTURES / card["source"], card["crop"])
        out = PICTURES / card["output"]
        # WebP keeps the transparent corners at a fraction of the PNG size.
        draw_window(content, card["title"]).save(out, quality=88, method=6)
        print(f"{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
