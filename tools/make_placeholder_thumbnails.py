"""Draw the launcher thumbnails and the first workshop screenshot for each mod."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PIL import Image, ImageDraw, ImageFont

from tools.resize_workshop_images import MAX_BYTES, SCREENSHOT_SIZE
from tools.targets import repo_root

SIZE = 512
GALLERY_SIZE = SCREENSHOT_SIZE
SUBTITLE = "Trigger an in-game event each time a focus becomes available"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


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


def _palette(phosphor: bool) -> dict[str, tuple[int, int, int]]:
    if phosphor:
        return {
            "background": (8, 16, 10),
            "panel": (12, 28, 16),
            "edge": (120, 220, 110),
            "ink": (210, 255, 196),
            "muted": (150, 196, 140),
            "node": (24, 64, 28),
        }
    return {
        "background": (18, 22, 16),
        "panel": (28, 34, 24),
        "edge": (212, 176, 90),
        "ink": (244, 232, 204),
        "muted": (196, 176, 130),
        "node": (48, 42, 24),
    }


def _save_png_under_limit(image: Image.Image, path: Path) -> Path:
    image.save(path, format="PNG", optimize=True, compress_level=9)
    if path.stat().st_size <= MAX_BYTES:
        return path
    jpeg = path.with_suffix(".jpg")
    rgb = image.convert("RGB")
    for quality in (90, 85, 80, 75, 70):
        rgb.save(jpeg, format="JPEG", quality=quality, optimize=True)
        if jpeg.stat().st_size <= MAX_BYTES:
            path.unlink(missing_ok=True)
            return jpeg
    path.unlink(missing_ok=True)
    return jpeg


def draw_thumbnail(path: Path, footer: str, phosphor: bool) -> None:
    colors = _palette(phosphor)
    background = colors["background"]
    panel = colors["panel"]
    edge = colors["edge"]
    ink = colors["ink"]
    muted = colors["muted"]
    node = colors["node"]
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


def _fitted_font(text: str, max_width: int, start: int, bold: bool) -> ImageFont.ImageFont:
    size = start
    while size > 18:
        font = _font(size, bold=bold)
        if font.getlength(text) <= max_width:
            return font
        size -= 2
    return _font(18, bold=bold)


def draw_gallery_card(path: Path, footer: str, phosphor: bool) -> None:
    colors = _palette(phosphor)
    background = colors["background"]
    panel = colors["panel"]
    edge = colors["edge"]
    ink = colors["ink"]
    muted = colors["muted"]
    node = colors["node"]
    width, height = GALLERY_SIZE
    image = Image.new("RGBA", GALLERY_SIZE, (*background, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((40, 40, width - 41, height - 41), radius=28, outline=edge, width=8)
    draw.rounded_rectangle((64, 64, width - 65, height - 65), radius=18, outline=panel, width=4)
    for index in range(52):
        x = 110 + index * 33
        draw.ellipse((x, 96, x + 12, 108), fill=edge)
        draw.ellipse((x, height - 108, x + 12, height - 96), fill=edge)
    center = (width // 2, 390)
    draw.polygon(_hexagon(center, 118), fill=node, outline=edge, width=6)
    draw.polygon(_hexagon(center, 94), outline=edge, width=4)
    draw.line((center[0], center[1] - 44, center[0], center[1] + 14), fill=ink, width=14)
    draw.ellipse((center[0] - 10, center[1] + 30, center[0] + 10, center[1] + 50), fill=ink)
    draw.text((width / 2, 168), "NOTIFICATIONS", font=_font(42, bold=True), fill=edge, anchor="mm")
    title = _font(92, bold=True)
    draw.text((width / 2, 590), "FOCUS", font=title, fill=ink, anchor="mm")
    draw.text((width / 2, 692), "AVAILABLE", font=title, fill=ink, anchor="mm")
    draw.text((width / 2, 790), footer, font=_font(36, bold=True), fill=muted, anchor="mm")
    subtitle_font = _fitted_font(SUBTITLE, width - 280, 34, bold=False)
    draw.text((width / 2, 868), SUBTITLE, font=subtitle_font, fill=ink, anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    _save_png_under_limit(image, path)


def _contain(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    width, height = GALLERY_SIZE
    margin = 72
    scale = min((width - margin * 2) / image.width, (height - margin * 2) / image.height)
    resized = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    if resized.mode != "RGBA":
        resized = resized.convert("RGBA")
    canvas = Image.new("RGBA", GALLERY_SIZE, (*background, 255))
    canvas.paste(resized, ((width - resized.width) // 2, (height - resized.height) // 2), resized)
    return canvas


def fit_loose_screenshots(root: Path) -> None:
    """Place added crops on a 1920x1080 field and name them screenshot-2 onward."""
    for keyword, phosphor in (("vanilla", False), ("owb", True)):
        folder = root / "screenshots" / keyword
        loose = sorted(
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in IMAGE_SUFFIXES
            and not path.stem.startswith("screenshot-")
        )
        background = _palette(phosphor)["background"]
        for offset, source in enumerate(loose, start=2):
            dest = folder / f"screenshot-{offset}.png"
            with Image.open(source) as opened:
                fitted = _contain(opened.convert("RGBA"), background)
            written = _save_png_under_limit(fitted, dest)
            if source.resolve() != written.resolve():
                source.unlink()
            print(f"Wrote {written} ({written.stat().st_size} bytes) from {source.name}")


def main() -> int:
    root = repo_root()
    cards = (
        ("vanilla", "VANILLA", False),
        ("owb", "OLD WORLD BLUES", True),
    )
    for keyword, footer, phosphor in cards:
        thumbnail = root / "assets" / keyword / "thumbnail.png"
        draw_thumbnail(thumbnail, footer, phosphor=phosphor)
        card = root / "screenshots" / keyword / "screenshot-1.png"
        draw_gallery_card(card, footer, phosphor=phosphor)
        print(f"Wrote {thumbnail} ({thumbnail.stat().st_size} bytes)")
        print(f"Wrote {card} ({card.stat().st_size} bytes)")
    fit_loose_screenshots(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
