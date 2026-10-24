"""Draw the 512x512 launcher thumbnails used until a replacement image is added."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PIL import Image, ImageDraw, ImageFont

from tools.targets import repo_root

SIZE = 512


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    windows = Path(r"C:\Windows\Fonts")
    for name in names:
        path = windows / name
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _hexagon(center: tuple[int, int], radius: int) -> list[tuple[float, float]]:
    import math

    cx, cy = center
    points: list[tuple[float, float]] = []
    for step in range(6):
        angle = math.radians(-90 + step * 60)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def draw_thumbnail(path: Path, footer: str, phosphor: bool) -> None:
    if phosphor:
        background = (8, 16, 10)
        panel = (12, 28, 16)
        edge = (120, 220, 110)
        ink = (210, 255, 196)
        muted = (150, 196, 140)
        node = (24, 64, 28)
    else:
        background = (18, 22, 16)
        panel = (28, 34, 24)
        edge = (212, 176, 90)
        ink = (244, 232, 204)
        muted = (196, 176, 130)
        node = (48, 42, 24)
    image = Image.new("RGBA", (SIZE, SIZE), (*background, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, SIZE - 19, SIZE - 19), radius=18, outline=edge, width=4)
    draw.rounded_rectangle((34, 34, SIZE - 35, SIZE - 35), radius=12, outline=panel, width=2)
    for index in range(28):
        x = 46 + index * 15
        draw.ellipse((x, 48, x + 6, 54), fill=edge)
        draw.ellipse((x, SIZE - 54, x + 6, SIZE - 48), fill=edge)
    center = (SIZE // 2, 188)
    draw.polygon(_hexagon(center, 78), fill=node, outline=edge)
    draw.polygon(_hexagon(center, 62), outline=edge)
    draw.line((center[0], center[1] - 28, center[0], center[1] + 8), fill=ink, width=8)
    draw.ellipse((center[0] - 6, center[1] + 20, center[0] + 6, center[1] + 32), fill=ink)
    title = _font(52, bold=True)
    subtitle = _font(28, bold=True)
    footer_font = _font(22, bold=True)
    draw.text((SIZE / 2, 300), "FOCUS", font=title, fill=ink, anchor="mm")
    draw.text((SIZE / 2, 358), "AVAILABLE", font=title, fill=ink, anchor="mm")
    draw.text((SIZE / 2, 430), footer, font=footer_font, fill=muted, anchor="mm")
    draw.text((SIZE / 2, 78), "NOTIFICATIONS", font=subtitle, fill=edge, anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def main() -> int:
    root = repo_root()
    draw_thumbnail(root / "assets" / "vanilla" / "thumbnail.png", "VANILLA", phosphor=False)
    draw_thumbnail(root / "assets" / "owb" / "thumbnail.png", "OLD WORLD BLUES", phosphor=True)
    for keyword in ("vanilla", "owb"):
        path = root / "assets" / keyword / "thumbnail.png"
        print(f"Wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
