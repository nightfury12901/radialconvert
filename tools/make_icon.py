"""Generate assets/icon.ico (orange circle with two swap arrows)."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
S = 1024  # draw large, let ICO downscale


def arrow(d: ImageDraw.ImageDraw, y: int, to_right: bool):
    x0, x1 = (260, 700) if to_right else (764, 324)
    d.line([(x0, y), (x1, y)], fill=(30, 30, 30), width=70)
    tip = x1 + (110 if to_right else -110)
    d.polygon([(tip, y), (x1, y - 120), (x1, y + 120)], fill=(30, 30, 30))


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((24, 24, S - 24, S - 24), fill=(255, 140, 0, 255), outline=(255, 255, 255, 255), width=28)
    arrow(d, 400, True)
    arrow(d, 624, False)
    OUT.parent.mkdir(exist_ok=True)
    img.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
